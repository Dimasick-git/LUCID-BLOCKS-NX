#include <switch.h>
#include <stdio.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include "nx_loading.h"
static bool active;
static u64 deadline;
int nx_loading_set(int enabled) {
    if (!!enabled == active) return 0;
    Result rc = appletSetCpuBoostMode(enabled ? ApmCpuBoostMode_FastLoad : ApmCpuBoostMode_Normal);
    printf("[nx-loading] CPU fast-load request=%d result=%08x\n", !!enabled, rc);
    if (R_SUCCEEDED(rc)) {
        active = !!enabled;
        deadline = armGetSystemTick() + armNsToTicks(60000000000ULL);
    }
    return (int)rc;
}
void nx_loading_tick(void) {
    if (active && (armGetSystemTick() >= deadline || appletGetFocusState() != AppletFocusState_InFocus)) {
        nx_loading_set(0);
    }
}
const char *nx_lan_address(void) {
    static char address[INET_ADDRSTRLEN];
    struct in_addr value = { .s_addr = gethostid() };
    if (!inet_ntop(AF_INET, &value, address, sizeof(address))) return "0.0.0.0";
    return address;
}
