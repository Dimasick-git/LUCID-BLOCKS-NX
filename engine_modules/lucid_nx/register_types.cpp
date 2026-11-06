#include "register_types.h"
#include "core/extension/gdextension_manager.h"
#include "core/error/error_macros.h"
#include "core/string/print_string.h"

extern "C" GDExtensionBool gdblocks_init(GDExtensionInterfaceGetProcAddress,
    GDExtensionClassLibraryPtr, GDExtensionInitialization *);

void initialize_lucid_nx_module(ModuleInitializationLevel level) {
    // Core GDExtension interfaces exist now, and SCENE extension callbacks
    // will run immediately after this module initialization phase.
    if (level != MODULE_INITIALIZATION_LEVEL_SCENE) return;
    auto *manager = GDExtensionManager::get_singleton();
    ERR_FAIL_NULL(manager);
    static const GDExtensionInitializationFunction entry = &gdblocks_init;
    auto status = manager->load_extension_from_function(
        "libgodot://lucid_blocks_gdblocks",
        GDExtensionConstPtr<const GDExtensionInitializationFunction>(&entry));
    ERR_FAIL_COND_MSG(status != GDExtensionManager::LOAD_STATUS_OK &&
        status != GDExtensionManager::LOAD_STATUS_ALREADY_LOADED,
        "Lucid Blocks static voxel extension could not initialize");
    print_line("[lucid-nx] static voxel library registered with extension manager");
}

void uninitialize_lucid_nx_module(ModuleInitializationLevel level) {
    // The extension manager owns its initialization levels and teardown.
}
