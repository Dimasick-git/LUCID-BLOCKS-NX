<p align="center">
  <img src="docs/images/lucid-blocks-banner.png" alt="Lucid Blocks NX — LAN voxel world" width="1200">
</p>

<h1 align="center">Lucid Blocks — NX</h1>

<p align="center">
  Experimental Nintendo Switch port with a complete NSP installer and LAN co-op for 2–4 players.
</p>

<p align="center">
  <a href="https://github.com/Dimasick-git/LUCID-BLOCKS-NX/releases/tag/v0.1.0">Download v0.1.0</a> ·
  <a href="docs/INSTALL_RU.md">Установка</a> ·
  <a href="CHANGELOG.md">Changelog</a> ·
  <a href="https://github.com/Dimasick-git/LUCID-BLOCKS-NX/issues">Report a bug</a>
</p>

> **v0.1.0 is an experimental public release.** The project is not an official Lucid Blocks release. Install only on a console and software setup you control, and keep a backup of your saves.

## What is included

`v0.1.0` is based on the NSP07 build and includes the engine, game resources, prepared item meshes and the full compressed game pack in one DBI-ready NSP. The pack is compressed losslessly from about **1.50 GB to 815 MB**, and resources are read from the installed title instead of being unpacked to the microSD card at launch.

- LAN co-op for **2–4 Nintendo Switch consoles**: create or find a room without entering an IP address.
- Shared world, nearby spawn and separate guest save/cache data.
- Combat, revive, item meshes, player appearance and multiplayer actions synchronized over LAN.
- 321 prepared item meshes with geometry reuse for shared icons.
- Lightweight water rendering, matte block lighting and disabled local shadows for a practical Switch profile.
- Optional SaltyNX/FPSLocker integration.

## Performance profile

The release profile uses 75% render scale, 32-block view distance and reduced effects. Current device results are approximately:

| System profile | Observed result |
| --- | --- |
| Stock settings, no overclock | **30–40 FPS** |
| Overclocked system | **60+ FPS** |

Results depend on the scene, world state, LAN activity and the selected system profile. Stable 60 FPS is not promised for stock settings.

## Installation

1. Download `LUCID_BLOCKS_NX_FULL_NSP07.nsp` from the [v0.1.0 release](https://github.com/Dimasick-git/LUCID-BLOCKS-NX/releases/tag/v0.1.0).
2. Install the NSP with DBI on every console that will join a LAN session.
3. Launch the installed title from HOME. Do not launch through Album because of its reduced memory budget.
4. For LAN: the host chooses **LAN Co-op → Create Room → world**; other consoles choose **Find Game**.

All consoles must use the same v0.1.0/NSP07 protocol. Internet rooms are not included. Preserve `/switch/lucid-blocks/LucidBlocksNX/` when updating because it contains saves, settings and the writable cache. See the complete [Russian installation guide](docs/INSTALL_RU.md).

## Development

The port is built around Godot/Horizon, GLES Compatibility and a statically linked gdblocks runtime with double precision. This repository contains patches, the loader, packaging tools and validation documentation. Game packages, console keys and personal saves are not committed to Git.

- [Build and validation guide](docs/DEVELOPMENT_RU.md)
- [Build status](docs/BUILD_STATUS.md)
- [Compressed pack format](docs/PACK_FORMAT.md)
- [Credits and third-party code](Credits.md)

## Disclaimer

Lucid Blocks is the original game by its respective authors: [Lucid Blocks on Steam](https://store.steampowered.com/app/3495730/). This Nintendo Switch port is unofficial and is not affiliated with or endorsed by the original developers or Nintendo.
