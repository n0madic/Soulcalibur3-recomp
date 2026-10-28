# Soulcalibur III on macOS — a static recompilation

This project runs **Soulcalibur III** (PlayStation 2, PAL release `SCES_533.12`) natively on Apple Silicon Macs. It does not emulate the PS2's CPU at run time: the game's MIPS code is translated ahead of time into C++ by [PS2Recomp](https://github.com/ran-j/PS2Recomp), which is compiled together with a runtime that provides the rest of the console (kernel, IOP and sound, VU0/VU1, GS graphics, pad, memory card, movies).

This repository holds the patches to PS2Recomp, the recompiler configuration and the build scripts. It contains **no game data**. You supply your own disc image, and everything generated from it stays on your machine.

## Status

- The game boots and runs through its start-up flow, title screen, menus and battles, including the attract-mode demo fights.
- Graphics use [paraLLEl-GS](https://github.com/Arntzen-Software/parallel-gs), a Vulkan GS renderer (MoltenVK on macOS), with optional anti-aliasing and bicubic scaling in the window.
- Sound, the start-up and menu movies (optional, needs FFmpeg), the display-mode choice (PAL60 by default) and two-player controls are in place.
- On an M1 Pro on mains power the demo battle runs at 58–59 frames per second (60 is the target). Speed depends on recorded VU microprograms, see [Speed](#speed).
- It also compiles for Linux (arm64, in Docker) and for Windows (x86_64, cross-compiled with llvm-mingw), but those builds have hardly been tested: on Linux the game only reached the title screen on a software Vulkan driver, and the Windows executable has never been run. macOS on Apple Silicon is the only tested platform; see `recomp/README.md`, "Linux (Docker) and Windows (llvm-mingw) builds".
- Known gaps include the menu and battle background music and some rare issues. `recomp/README.md` lists them with the measurements behind them.

This is a work in progress, not a finished port.

## Requirements

- A Mac with Apple Silicon (developed and tested on an M1 Pro), with the Xcode Command Line Tools (`xcode-select --install`).
- [Homebrew](https://brew.sh).
- About 7 GB of free disk space in addition to the disc image.
- Your own dump of the PAL disc as an `.iso` file, under any name. Put it in the repository root, or pass its path when you build (see [Build](#build)).

  Other regions and revisions are not supported: the recompiled code and the patches are specific to the PAL release, whose boot file is `SCES_533.12`.

Install the tools:

```sh
brew install cmake ninja python3 p7zip molten-vk vulkan-loader
brew install ccache     # optional: speeds up rebuilds
brew install ffmpeg     # optional: only for the movies
```

`p7zip` provides the `7z` command that extracts the disc image.

## Build

```sh
make build
```

The disc image is the only `.iso` file in the repository root. If it is somewhere else, or the root holds several, name it:

```sh
make build ISO=/path/to/disc.iso
```

This runs `recomp/build.sh`, which:

1. extracts the disc image into `recomp/work/game/`;
2. clones PS2Recomp at the commit in `recomp/PS2Recomp.commit` and applies the patch series from `recomp/series`;
3. clones the dependencies (toml11, fmt, nlohmann/json, rabbitizer, raylib, paraLLEl-GS);
4. builds the recompiler and recompiles the game's ELF into C++ (about 68 000 small files with the Ghidra function map, see below);
5. builds the runner, `ps2EntryRunner`, from those files in about 2100 unity-build units.

The compile of the runner alone takes about 5 minutes on an M1 Pro without ccache. The script can be run again at any time: it skips the steps that are already done.

Everything is created under `recomp/work/`, which is not tracked by Git.

### Build options

Set these as environment variables, for example `ENABLE_FFMPEG=ON SKIP_INTRO=0 make build`.

| Variable | Default | Effect |
| --- | --- | --- |
| `ISO` | the only `.iso` in the repository root | Path of the disc image. Only needed for the first build, which extracts it. |
| `ENABLE_FFMPEG` | `OFF` | `ON` builds the MPEG decoder for the game's movies (needs `ffmpeg` from Homebrew). |
| `SKIP_INTRO` | `1` | `1` skips the two start-up movies; `0` plays them (needs `ENABLE_FFMPEG=ON`). |
| `DISPLAY_DIALOG` | `0` | `0` answers the PAL50/PAL60 display-mode dialog with PAL60; `1` shows the dialog. |

### Better function boundaries with Ghidra (recommended)

The recompiler works from a list of the game's functions. Its own analyzer misses jump-table targets and fall-through labels, so the configuration used for all results in `recomp/README.md` takes the list from a Ghidra export. This step is optional but recommended:

```sh
brew install ghidra openjdk@21 gh   # gh must be logged in: gh auth login
make build                           # first build: extracts the disc and clones PS2Recomp
make ghidra                          # imports the ELF into Ghidra (about 2 minutes) and exports the function map
make build                           # picks the export up and recompiles
```

## Run

```sh
make run
```

The runner has to start from the extracted game directory, which `make run` does. To start it by hand:

```sh
cd recomp/work/game
../PS2Recomp/out/build/ps2xRuntime/ps2EntryRunner SCES_533.12
```

A window opens and the game starts in PAL60. Memory card saves go to `recomp/work/game/mc0` and `mc1`.

**The window takes the keyboard focus, and the keyboard is the controller.** Keys typed into another application while the game is in front skip movies and press buttons in the game.

### Controls

Host game controllers work as well: the first controller drives player 1 and the second one player 2.

| Action | Player 1 | Player 2 |
| --- | --- | --- |
| Up / left / down / right | Arrow keys or W / A / S / D | I / J / K / L |
| Square / Cross / Circle / Triangle | Z / X / C / V | F / G / H / T |
| L1 / R1 | Q / E | R / Y |
| L2 / R2 | Left Shift / Right Shift | U / O |
| Start / Select | Enter / Tab | Backspace (Delete on a Mac keyboard) / Right Control |

Player 1 also has Space = Cross, Escape = Circle, keypad 0 = Square and keypad 1 = Triangle. Keys refer to the Latin keyboard layout. There is no remapping yet.

### Picture and renderer options

Set these as environment variables, for example `PS2_HOST_AA=fxaa make run`.

| Variable | Default | Effect |
| --- | --- | --- |
| `PS2_HOST_AA` | `smaa` | Anti-aliasing before the window scales the picture: `smaa`, `fxaa` or `off`. |
| `PS2_HOST_FILTER` | `bicubic` | How the window scales the picture: `bicubic`, `bilinear` or `nearest`. |
| `PS2_GS_SSAA` | `1` | `1` renders at the game's resolution. `4` or more scans the picture out at twice the resolution, which an M1 Pro cannot hold at 60 frames per second in battle. |
| `PS2_GS_BACKEND` | `parallel` | `parallel` is the Vulkan renderer. `cpu` is a very slow software renderer for debugging. |
| `PS2_VULKAN_LIBRARY` | — | Path of the Vulkan loader or MoltenVK library, if it is not in `/opt/homebrew/lib` or `/usr/local/lib`. |

## Speed

- **Use mains power.** Low Power Mode on battery cuts the speed by about a quarter.
- **Record the VU microprograms once.** The game uploads its VU0 and VU1 microcode at run time, so it cannot be recompiled with the ELF. The build compiles the programs you have recorded into the runner; programs that are not recorded are interpreted, which is several times slower in battle (a 3.6x difference was measured for VU1). A fresh checkout has no recording, so do this after the first build:

  ```sh
  cd recomp/work/game
  PS2_VU_PROGRAM_PROFILE=../vu-profiles ../PS2Recomp/out/build/ps2xRuntime/ps2EntryRunner SCES_533.12
  ```

  Leave the title screen alone for a few minutes so that the attract mode plays its demo battles, then quit and run `make build` again. The recording stays in `recomp/work/vu-profiles/` and is picked up automatically. Running with `PS2_VU_PROGRAM_PROFILE` set again while you play other modes adds only the programs that are still missing.
- **Measure speed by VSyncs per second.** Compare it with the game's own logic counter (`0x4f3814`); `recomp/README.md` explains why both numbers are needed.
- `PS2_VU_EXECUTION=interpreter` turns the compiled VU routines off, for comparisons.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| `7z: command not found` | `brew install p7zip`. |
| `Runner not built` or `Disc not extracted` from `make run` | Run `make build` first. |
| `No disc image found` or `More than one .iso` | Keep exactly one `.iso` in the repository root, or name it: `make build ISO=/path/to/disc.iso`. |
| `has no SCES_533.12` | The image is not the PAL release; only that one is supported. |
| The game is very slow and the log warns about a Vulkan device | `brew install molten-vk vulkan-loader`, or set `PS2_VULKAN_LIBRARY`. Without Vulkan the runner falls back to the software renderer. |
| The movies are missing | They are skipped by default. Rebuild with `ENABLE_FFMPEG=ON SKIP_INTRO=0 make build`. |
| A guest function is reported as `missing-target` in the log | The recompiler did not know a code address. Add it to `entry_points` in `recomp/sc3.toml` and rebuild. |
| The game window ignores your keys | The window has to be in front: it only reads the keyboard while it has focus. |

## Repository layout

| Path | What it is |
| --- | --- |
| `Makefile` | `make build`, `make run`, `make ghidra`. |
| `recomp/build.sh` | The end-to-end build script. `recomp/test_build_iso.sh` tests how it finds the disc image. |
| `recomp/series`, `recomp/NNNN-*.patch`, `recomp/upstream/` | The patches applied to PS2Recomp, in order: one local patch per problem area, plus open upstream pull requests taken as they are. |
| `recomp/sc3.toml`, `recomp/display_mode.toml`, `recomp/skip_intro.toml` | The recompiler configuration and the instruction patches for the display-mode dialog and the start-up movies. |
| `recomp/parallel-gs/` | Patches to the paraLLEl-GS renderer. |
| `recomp/docker/` | Trial builds for Linux (Docker) and Windows (llvm-mingw cross-build); they compile but are hardly tested. |
| `recomp/debug/`, `recomp/experimental/` | Diagnostics and experiments that are never applied by default. |
| `recomp/README.md` | The technical record: what each patch does, findings, measurements and known gaps. |
| `CLAUDE.md` | Notes for working on the code: how to run the tests and produce a patch. |
| `recomp/work/` | Local only: the extracted disc, the patched PS2Recomp tree, generated code and build output. |

## Contributing

Changes to the runtime are made as patches in the series, one per problem area, each with a regression test. `CLAUDE.md` describes how to build and run the tests and how to turn a change into a patch, and `recomp/README.md` records what each patch covers.

## License

The patches, scripts and configuration in this repository are licensed under the [GNU General Public License v3.0](LICENSE), the license of [PS2Recomp](https://github.com/ran-j/PS2Recomp), whose code the patches modify. The upstream pull requests in `recomp/upstream/` are contributions to PS2Recomp and stay under its license. The patches to [paraLLEl-GS](https://github.com/Arntzen-Software/parallel-gs) in `recomp/parallel-gs/` stay under that project's license (LGPL-3.0 or later; its Granite submodule is MIT).

## Legal

You need a legally obtained copy of the game. No game binaries, assets, generated game code or recorded microcode are included in this repository or may be added to it. Soulcalibur is a trademark of its owner; this project is not affiliated with or endorsed by Bandai Namco.
