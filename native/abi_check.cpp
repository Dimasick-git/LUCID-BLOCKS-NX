#include <godot_cpp/variant/vector3.hpp>
#include <godot_cpp/variant/transform3d.hpp>
#include <cstdint>
static_assert(sizeof(godot::real_t)==8, "Lucid Blocks requires Godot double precision");
static_assert(sizeof(godot::Vector3)==24, "Unexpected Vector3 ABI");
static_assert(sizeof(godot::Transform3D)==96, "Unexpected Transform3D ABI");
extern "C" std::uint32_t lucid_nx_native_abi_version() { return 0x00040600; }
