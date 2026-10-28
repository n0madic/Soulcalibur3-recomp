# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A static recompilation of Soulcalibur III (PAL, boot ELF `SCES_533.12`) with [ran-j/PS2Recomp](https://github.com/ran-j/PS2Recomp), on macOS arm64. This repository tracks a series of patches against PS2Recomp (one per problem area), recompiler configuration, build/analysis scripts, and progress documentation. PS2Recomp itself, the original disc image, extracted game files, generated game code, recorded VU microcode, captures, working directories, and caches stay local and are excluded from Git by the root `.gitignore` source allowlist. The root `README.md` is the user-facing guide (what the project is, how to build and run it, controls, options, troubleshooting); keep it in step with `Makefile`, `recomp/build.sh`, the pad mapping and the environment variables whenever those change. `recomp/README.md` is the main technical document: it lists the patches and the problem areas they belong to, records findings and measurements, and lists the known gaps. Read it before changing anything, and add or update its row (and its details) for every patch you change. The repository is licensed under the GPL-3.0 (`LICENSE`), like PS2Recomp.

## Layout

- `Makefile` has three targets: `make build` (runs `recomp/build.sh`), `make run` and `make ghidra`.
- `recomp/series` lists the patch series that `build.sh` applies, in that order, to PS2Recomp at the commit in `recomp/PS2Recomp.commit`: 20 local patches `recomp/NNNN-<area>.patch` (the fixes of one problem area in one patch) and 15 upstream PRs in `recomp/upstream/NN-prNNN-*.patch`, interleaved. An upstream patch stays as the PR has it and is dropped when the PR is merged; local fixes of it go into a local patch after it. Until 2026-10-27 the series had 72 patches; `recomp/README.md` maps the former numbers (used in its investigation notes) to the current patches.
- `recomp/debug/*.patch` are diagnostics that are never applied by default.
  - `diagnostics-scene-state.patch`: frame dumps and the `[TEMP-DEBUG globals]` scene/tick line.
  - `diagnostics-vu1-verify.patch`: `PS2_VU_VERIFY=1` shadows each compiled VU run with the interpreter.
  - Both apply on top of the whole series. `diagnostics-full.patch` and `diagnostics-loader-threads.patch` are historical records of the early investigations and no longer apply to the series.
- `recomp/experimental/*.patch` are experiments that are never applied by default and are not in `series`; each applies on top of the whole series, and `recomp/README.md` says what it showed. `gs-pipeline-thread.patch` runs the VIF1, VU1 and GIF work on a worker thread (`PS2_GS_THREAD=1`) and is no faster in battle.
- `recomp/parallel-gs/` holds patches to the paraLLEl-GS clone in `work/deps/parallel-gs`: `*.patch` for its Granite submodule, `gs/*.patch` for paraLLEl-GS itself. `build.sh` applies them only when it clones.
- `recomp/sc3.toml` is the recompiler config, including the stub list that maps library functions to runtime HLE stubs. `recomp/display_mode.toml` holds instruction patches that answer the display-mode dialog with PAL60 (`DISPLAY_DIALOG=1` keeps it), and `recomp/skip_intro.toml` those that skip the movies (`SKIP_INTRO=0` keeps them).
- `recomp/docker/` holds trial builds for other platforms (they compile but are hardly tested), not part of `make build`: a Dockerfile (Linux arm64 build and headless xvfb/lavapipe run) and `build-mingw.sh` with its toolchain file (Windows x86_64 cross-build of the runner with llvm-mingw). `recomp/README.md` ("Linux (Docker) and Windows (llvm-mingw) builds") has the commands and findings.
- `recomp/work/` is local only and must never be committed:
  - `PS2Recomp/` is the patched working tree, which also carries uncommitted `TEMP-DEBUG` instrumentation.
  - `game/` is the extracted disc. The runner must be started from this directory.
  - `gen/` holds the recompiler output.
  - `vu-profiles/` holds the recorded VU microcode.
  - `deps/` holds the dependencies.
- Recorded VU microcode and generated C++ are game data. They stay in `work/` or a scratch directory and never go into a patch.

## Commands

The first full build of the runner takes about 5 minutes (since the Ghidra far-chunk fix in `0001-recompiler-function-boundaries-and-delay-slots`). Changing any runtime header recompiles all ~2100 generated units; ccache helps with this.

Full build: extract the disc image (the only `*.iso` in the repository root, or `ISO=<path>`), clone and patch PS2Recomp, recompile, build the runner.
```sh
make build
```

Run the game:
```sh
make run
```

Rebuild the runner after editing runtime code in `recomp/work/PS2Recomp`:
```sh
cmake --build recomp/work/PS2Recomp/out/build --target ps2EntryRunner
```

### Tests

Tests use a separate build directory with `-DPS2X_BUILD_TEST=ON`. Here it is `recomp/work/PS2Recomp/out/test`, configured with `PS2X_VU_PROGRAM_PROFILES=<fixture dir>`.

Build and run them from that directory:
```sh
ninja ps2x_tests
PS2_TEST_REQUIRE_GPU=1 PS2_VU_PROGRAM_FIXTURES=<fixture dir> PS2_VU_REQUIRE_PROGRAMS=1 ./ps2xTest/ps2x_tests
```

- **Fixtures.** The VU fixtures come from `python3 ps2xTest/data/vu_programs.py <dir>`. Configure CMake with that directory and pass the same directory at run time.
- **Single test.** The MiniTest runner has no filter. Run the whole binary and grep the output for the test case name; failures print as `[Failed]` followed by `- message` lines.
- **Other suites.**
  - Disc image lookup of `build.sh`: `./recomp/test_build_iso.sh` (fake `7z` and `git`, nothing is built).
  - Generator tests: `python3 -m unittest discover tools/tests`.
  - `gs_cache` suites: `ctest` in `ps2xTest`.
  - IOP suites: `ctest` in `ps2xIOP`, after configuring with `-DPS2X_IOP_BUILD_TESTS=ON`.

### Producing a patch

**Add and fix patches inside the patch group of their area; do not stack a new patch for every fix.** A fix, extension or test for something an existing patch already covers is folded into that patch. Only a new problem area gets a new numbered patch. A patch that merely corrects another patch should have been part of it. Upstream patches are never edited; their local fixes go into a local patch of the same area.

`build.sh` applies the patches of `recomp/series` only to a fresh clone. The working tree contains debug code, so do not diff it to make a patch. Instead:
1. In a clean checkout at the base commit, apply the series with `git am --whitespace=nowarn` (the patches are mailbox files; one commit each), at least up to the patch of the area you change. A fix belongs to the patch of its area; an upstream patch is never edited.
2. Make the change with its regression test, build and run the tests there.
3. Fold the change into that patch's commit (`git commit --fixup=<commit>`, `git rebase -i --autosquash`) or, for a new area, commit it as a new patch; apply the rest of the series on top so that all of it still applies.
4. Write each changed patch with `git format-patch -1 --stdout --no-signature --zero-commit > recomp/NNNN-<area>.patch`, and list a new patch in `recomp/series` (local: `NNNN-<area>.patch`, upstream: `upstream/NN-prNNN-<name>.patch`).
5. Check that the series applied to the base commit gives the tree you tested, and that `debug/diagnostics-*.patch` still applies on top.

## Architecture (PS2Recomp as used here)

- **Pipeline.** `ps2xAnalyzer` produces the function map; the Ghidra export from `make ghidra` gives better function boundaries. `ps2xRecomp` turns each MIPS function into a C++ function (`FUN_<addr>` / `entry_<addr>` in `ps2xRuntime/src/runner/`). `pointer_entries.py` adds a second pass of entry points for code that is reachable only through data pointers.
- **Guest calls.** Generated code calls known functions directly. Indirect branches go through `PS2Runtime::dispatchGuestBranch`. Library functions listed as stubs in `sc3.toml` run as HLE code in `ps2xRuntime/src/lib/Kernel/Stubs`; for example, `sceGsSyncV` waits on the scheduler. Syscalls go through `Kernel/Syscalls`.
- **Time and threads: `EeScheduler`.**
  - It runs the guest EE threads cooperatively on one host "GameThread".
  - EE time is an estimate, not an instruction count: every dispatch or loop checkpoint charges a fixed 8 or 32 cycles (`checkpointDue` → `accountCycles`). `accountCycles` also advances the EE timers and feeds the IOP emulator (`ps2xIOP`), so IOP emulation runs inside checkpoints.
  - A VBlank is a deadline that needs both the emulated cycle count and host wall time. Host time is the pacing source.
  - Events posted from other threads (`postEvent`) are handled in `processPendingEvents`, which runs between guest calls.
- **Memory and hardware: `PS2Memory`.** It owns RAM, the I/O registers (an `unordered_map`), DMA, the VIF1 interpreter (`ps2_vif1_interpreter.cpp`) and the EE timers. The timer counters are brought up to date lazily, and Timer 3 counts H-blanks. GS privileged registers live in `GSRegisters`.
- **Sound.** The game's own sound IRX modules run on the emulated IOP and drive the SPU2 emulation in `ps2xIOP` (`iop_spu2.cpp`; `upstream/13-pr308-spu2` and `0015-spu2-autodma-and-audio-queue`), including AutoDMA for the ADX streams. Its output goes to a raylib `AudioStream`.
- **Movies.** CRI Sofdec feeds its MPEG video bitstream to the IPU itself over the toIPU DMA (channel 4) and libmpeg's Nodata callback. `PS2Memory` hands that DMA to an IPU input sink, and the HLE `sceMpeg*` stubs decode it with FFmpeg (`0016-movies-mpeg-ipu`). Sofdec and ADX stream from disc in the ADX manager's idle thread, which needs `ResumeThread` to return the thread id (`0013-kernel-memory-and-dma`). Building with movies needs `ENABLE_FFMPEG=ON SKIP_INTRO=0 ./recomp/build.sh`.
- **Graphics.** paraLLEl-GS (Vulkan via MoltenVK) is the default GS. `PS2_GS_BACKEND=cpu` selects the software GS. paraLLEl-GS publishes each vsync's picture one vsync later; the host window takes a picture only when a new one is published (`GS::latchNewHostPresentationFrame`, `0018-gs-presentation-and-super-sampling`), not when the vsync tick changes. At every rate the game's final blit is replaced by its 32-bit source (`0019-gs-backbuffer-promotion`; the paraLLEl-GS fixes `recomp/parallel-gs/gs/0001` and `0002`, tested by the same patch, make the promotion work in game and skip it for blits that fade the picture or are split over two render passes). `PS2_GS_SSAA` defaults to 1: 4 or more (8 and 16 run as 4 on Apple GPUs) scans out at twice the resolution (`0018`) but cannot hold 60 frames/s in battle on an M1 Pro. The window smooths edges with SMAA (default, built from the paraLLEl-GS checkout's Granite) or FXAA at the picture's own resolution (`PS2_HOST_AA`) and scales the picture with a bicubic shader (`PS2_HOST_FILTER`; all in `0020-host-picture-scaling-and-aa`).
- **VU0/VU1.** There is an interpreter (`ps2xRuntime/src/lib/vu`), plus compiled routines. Microcode recorded with `PS2_VU_PROGRAM_PROFILE` is compiled into the runner by `tools/compile_vu_programs.py` (CMake `PS2X_VU_PROGRAM_PROFILES`). `ps2_vu_program::run` enters a compiled routine only from a drained pipeline. `Run::handBack` returns in-flight results to the interpreter in the interpreter's own view. `PS2_VU_EXECUTION=interpreter` disables the compiled routines.

## Measuring and debugging

- **Speed.** Measure speed as VSyncs (displayed frames) per second, and read the game's counter at `0x4f3814` (logic steps) beside it. VSyncs follow the emulator's clock, so they can stay at 60 while the game itself runs slowly: with the worker-thread experiment a lost GS interrupt left the title at 60 VSyncs/s and 14 logic steps/s. The counter alone is not a speed measure either (it moves with the scene and the game's frame skip: the demo battle shows ~56 steps/s at ~59 VSyncs/s), so a run is healthy when both are near their usual values for the scene (title: both ~60). Measure on mains power; macOS Low Power Mode cuts speed by about 25%. Compare builds with alternating A/B runs, because run-to-run noise is several percent.
- **Keep your hands off the game window.** It takes the keyboard focus, and the keyboard is the pad (Enter = Start, Space = Cross, most letters). Keys typed while it is in front skip the movies and change the attract loop, which looks like speed or movie bugs. Runs that must not be disturbed can be made so by testing a build that ignores the keyboard (TEMP-DEBUG).
- **One instance at a time.** Run one game instance at a time; parallel runs slow each other down.
- **Profiling.** Use `sample <pid> 15` and read the "GameThread" section.
- **Temporary instrumentation.** Mark temporary code with `// TEMP-DEBUG` and remove it before producing a patch.
