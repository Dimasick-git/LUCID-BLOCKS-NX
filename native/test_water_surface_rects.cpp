#include "water_surface_rects.h"
#include <cstdio>
#include <cstdlib>
#include <random>

static int verify(uint8_t (&input)[16][16]) {
    uint8_t work[16][16];
    int seen[16][16] = {}, count = 0;
    for (int z=0; z<16; ++z) for (int x=0; x<16; ++x) work[z][x]=input[z][x];
    lucid_nx::water_surface_rects(work, [&](int x,int z,int width,int depth,uint8_t level) {
        if (!level || x<0 || z<0 || x+width>16 || z+depth>16) std::abort();
        ++count;
        for (int dz=0; dz<depth; ++dz) for (int dx=0; dx<width; ++dx) {
            if (input[z+dz][x+dx]!=level || ++seen[z+dz][x+dx]!=1) std::abort();
        }
    });
    for (int z=0; z<16; ++z) for (int x=0; x<16; ++x)
        if (seen[z][x] != int(input[z][x]!=0) || work[z][x]) std::abort();
    return count;
}
int main() {
    uint8_t layer[16][16] = {};
    if (verify(layer)!=0) return 1;
    for (auto &row:layer) for (auto &cell:row) cell=255;
    if (verify(layer)!=1) return 2;
    for (int z=0;z<16;++z) for (int x=0;x<16;++x) layer[z][x]=(x+z)%2?255:127;
    if (verify(layer)!=256) return 3;
    // Deterministic coverage tests include holes, arbitrary partial heights,
    // contiguous pools, and every outer edge. No tolerance/rounding is allowed.
    std::mt19937 rng(0x4e585732);
    for (int i=0;i<10000;++i) {
        for (int z=0;z<16;++z) for (int x=0;x<16;++x)
            layer[z][x]=i%2 ? uint8_t(rng()%256) : uint8_t((rng()%3)*127);
        verify(layer);
    }
    std::puts("WATER_RECT_COVERAGE_PASSED: 10003 layers; flat pool 256 -> 1 quad");
}
