#pragma once
#include <cstdint>

// Consume a single horizontal layer. Zero denotes a hidden/absent surface;
// equal nonzero values denote the exact water height (1..255). The callback
// receives disjoint rectangles covering precisely those original faces.
namespace lucid_nx {
template <int Width, int Depth, class Emit>
void water_surface_rects(uint8_t (&height)[Depth][Width], Emit emit) {
    for (int z = 0; z < Depth; ++z) {
        for (int x = 0; x < Width; ++x) {
            const uint8_t level = height[z][x];
            if (!level) continue;
            int width = 1;
            while (x + width < Width && height[z][x + width] == level) ++width;
            int depth = 1;
            while (z + depth < Depth) {
                bool matches = true;
                for (int dx = 0; dx < width; ++dx) {
                    if (height[z + depth][x + dx] != level) { matches = false; break; }
                }
                if (!matches) break;
                ++depth;
            }
            for (int dz = 0; dz < depth; ++dz)
                for (int dx = 0; dx < width; ++dx) height[z + dz][x + dx] = 0;
            emit(x, z, width, depth, level);
        }
    }
}
}
