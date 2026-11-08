#pragma once
#ifdef __cplusplus
extern "C" {
#endif
int nx_loading_set(int enabled);
void nx_loading_tick(void);
const char *nx_lan_address(void);
#ifdef __cplusplus
}
#endif
