#pragma once
#include "core/object/ref_counted.h"
#include "core/object/class_db.h"
extern "C" int nx_loading_set(int enabled);
extern "C" const char *nx_lan_address(void);
class NxPlatform : public RefCounted {
    GDCLASS(NxPlatform, RefCounted);
protected:
    static void _bind_methods() {
        ClassDB::bind_method(D_METHOD("set_loading", "enabled"), &NxPlatform::set_loading);
        ClassDB::bind_method(D_METHOD("get_lan_address"), &NxPlatform::get_lan_address);
    }
public:
    int set_loading(bool enabled) { return nx_loading_set(enabled); }
    String get_lan_address() const { return String::utf8(nx_lan_address()); }
};
