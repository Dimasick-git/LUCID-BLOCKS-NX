/* Shared-memory producer adapted from the local ULTRAKILL NX bridge.
 * Protocol: masagrator/SaltyNX 2.1.1. No injected hooks or display writes. */
#include <switch.h>
#include <string.h>
#include <stdio.h>
#include "nx_salty.h"
static SharedMemory memory;
static volatile NxSaltyBlock *block;
static volatile uint8_t *shared_base;
static uint64_t previous, window, retry_at;
static unsigned frames, sample_index, attempts, overlay_limit;
static bool enabled, foreign_producer, limit_checked;
int nx_salty_fps_limit(void) { return (int)__atomic_load_n(&overlay_limit, __ATOMIC_RELAXED); }
static bool nx_salty_session_room(void) {
  u64 raw=0; s64 limit=-1,current=-1;
  Result rc=svcGetInfo(&raw,InfoType_ResourceLimit,INVALID_HANDLE,0);
  if (R_FAILED(rc) || !raw) {
    printf("[saltynx] session resource handle rc=0x%x\n",rc);return false;
  }
  Handle resource=(Handle)raw;
  Result lr=svcGetResourceLimitLimitValue(&limit,resource,LimitableResource_Sessions);
  Result cr=svcGetResourceLimitCurrentValue(&current,resource,LimitableResource_Sessions);
  bool changed=false;
  printf("[saltynx] process sessions current=%lld limit=%lld query=0x%x/0x%x\n",
              (long long)current,(long long)limit,lr,cr);
  /* Only repair an actually exhausted small process budget; do not alter
   * memory/thread budgets or guess that every 0x10801 is a session limit. */
  if (R_SUCCEEDED(lr) && R_SUCCEEDED(cr) && current>=limit && limit>=0 && limit<=128) {
    rc=svcSetResourceLimitLimitValue(resource,LimitableResource_Sessions,current+8);
    changed=R_SUCCEEDED(rc);
    printf("[saltynx] session budget request %lld -> %lld rc=0x%x\n",
                (long long)limit,(long long)(current+8),rc);
  }
  svcCloseHandle(resource);
  return changed;
}

void nx_salty_init(void) {
    enabled = true;
    if (block || attempts >= 30) return;
    ++attempts;
    retry_at = armGetSystemTick() + 19200000;
    Handle handle = 0, remote = 0;
    Result rc = svcConnectToNamedPort(&handle, "SaltySD");
    if (rc == 0x10801 && !limit_checked) {
        limit_checked = true;
        if (nx_salty_session_room()) rc = svcConnectToNamedPort(&handle, "SaltySD");
    }
    if (R_FAILED(rc)) {
        if (attempts == 1 || attempts == 30) printf("[saltynx] connect attempt=%u rc=%08x\n", attempts, rc);
        return;
    }
    Service service;
    serviceCreate(&service, handle);
    rc = serviceDispatch(&service, 7, .in_send_pid=true, .out_handle_attrs={SfOutHandleAttr_HipcCopy}, .out_handles=&remote);
    if (R_SUCCEEDED(rc)) {
        shmemLoadRemote(&memory, remote, 0x1000, Perm_Rw);
        rc = shmemMap(&memory);
        if (R_SUCCEEDED(rc)) {
            shared_base = shmemGetAddr(&memory);
            uint64_t offset = 0;
            bool found = false;
            for (unsigned i = 4; i + sizeof(NxSaltyBlock) + 2 <= 0x1000; i += 4) {
                uint32_t magic;
                memcpy(&magic, (const void *)(shared_base+i), 4);
                if (magic == 0x465053) {
                    offset = i; found = true;
                    bool ours = shared_base[i+310]=='N' && shared_base[i+311]=='X';
                    foreign_producer = shared_base[i+9] && !ours;
                    break;
                }
            }
            if (!found) {
                uint64_t size = 316; /* Reserve four header bytes plus ABI and owner tag. */
                rc = serviceDispatchInOut(&service, 6, size, offset, .in_send_pid=true);
                if (R_SUCCEEDED(rc)) offset += 4;
            }
            if (R_SUCCEEDED(rc) && offset >= 4 && offset <= 0x1000-312 && !(offset & 3)) {
                block = (volatile NxSaltyBlock *)(shared_base+offset);
                if (!foreign_producer) {
                    memset((void *)block, 0, 312);
                    block->fps=255; block->average=255; block->api=2;
                    block->expected_buffers=-1;
                    shared_base[offset+310]='N'; shared_base[offset+311]='X';
                    __atomic_thread_fence(__ATOMIC_RELEASE);
                    block->magic=0x465053; block->active=1;
                }
                uint64_t hz=0;
                Result rr=serviceDispatchOut(&service, 10, hz, .in_send_pid=true);
                if (!foreign_producer && R_SUCCEEDED(rr) && hz>=30 && hz<=240) block->refresh=hz;
                printf("[saltynx] connected offset=%llu ABI=310 mode=%s display_hz=%llu result=%08x\n",
                       (unsigned long long)offset, foreign_producer?"external":"direct EGL", (unsigned long long)hz, rr);
            } else {
                if (R_SUCCEEDED(rc)) rc=MAKERESULT(Module_Libnx, 2);
                shmemClose(&memory); shared_base=NULL;
            }
        } else shmemClose(&memory);
    }
    serviceDispatch(&service, 0);
    serviceClose(&service);
    if (!block) printf("[saltynx] shared-memory init rc=%08x\n", rc);
}
void nx_salty_present(uint64_t tick) {
    if (!block) {
        if (enabled && attempts<30 && tick>=retry_at) nx_salty_init();
        return;
    }
    if (foreign_producer) return;
    block->magic=0x465053; block->active=1; block->api=2;
    const unsigned hz=shared_base[1];
    if (hz>=30 && hz<=240) block->refresh=hz;
    if (previous && tick>previous) {
        uint64_t delta=tick-previous;
        block->ticks[sample_index++%10]=(uint32_t)(delta>UINT32_MAX?UINT32_MAX:delta);
    }
    previous=tick;
    if (!window) { window=tick; frames=0; } else ++frames;
    ++block->frame;
    if (tick-window>=19200000) {
        float fps=(float)((double)frames*19200000.0/(tick-window));
        block->average=fps; block->fps=(uint8_t)(fps>254?254:fps+0.5f);
        frames=0; window=tick;
    }
    unsigned target=appletGetOperationMode()==AppletOperationMode_Console?block->locked_docked:block->locked;
    __atomic_store_n(&overlay_limit,target>=15 && target<=240?target:0,__ATOMIC_RELAXED);
}
void nx_salty_shutdown(void) {
    enabled=false;
    if (block && !foreign_producer) { block->active=0; __atomic_thread_fence(__ATOMIC_RELEASE); }
    /* Mapping survives renderer teardown; no dangling render-thread pointer. */
}
