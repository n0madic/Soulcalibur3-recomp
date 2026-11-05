# ps2-native-recomp port notes

`main` uses [exoteric33/ps2-native-recomp](https://github.com/exoteric33/ps2-native-recomp). The old PS2Recomp port, its patch series, Ghidra/TOML setup and investigation history are preserved at branch **`ps2recomp`**. Commit IDs differ from the original local history because personal author email addresses were replaced with GitHub noreply addresses before publication. Historical performance and platform claims from that implementation do not apply to the current one.

## Reproducible source set

Upstream pin: **`c683565b7d70a739e8c6a61fec7480ceafe8b5d9`**, the upstream `main` tip checked on 2026-11-05, stored in `ps2-native-recomp.commit`. It contains these accepted contributions; none is reapplied locally:

| Contribution | Included upstream |
| --- | --- |
| SIF command completion / keyboard Start | [#32](https://github.com/exoteric33/ps2-native-recomp/pull/32) |
| Original audio recovery allowance | [#33](https://github.com/exoteric33/ps2-native-recomp/pull/33), merged as `91d9b44` |
| POSIX thread CPU timer | [#34](https://github.com/exoteric33/ps2-native-recomp/pull/34) |
| Direct Cocoa Metal/WebGPU presentation | [#35](https://github.com/exoteric33/ps2-native-recomp/pull/35), merge `4ba502d` |
| Fast audio recovery after isolated producer pauses | [#37](https://github.com/exoteric33/ps2-native-recomp/pull/37), merge `384736a` |
| Optional game window title and macOS resident memory | [#38](https://github.com/exoteric33/ps2-native-recomp/pull/38), merge `8c6f712` |
| Opt-in, bounded GPU readback diagnostics | [#40](https://github.com/exoteric33/ps2-native-recomp/pull/40), merge `6f84ba1` |
| Generic recorded VU0 AOT, with the TOP/ITOP unit-selection fix | [#36](https://github.com/exoteric33/ps2-native-recomp/pull/36), merge `874d506` (merged 2026-11-05) |
| Accurate GPU backend start-up diagnostics | [#45](https://github.com/exoteric33/ps2-native-recomp/pull/45), merge `2635083` |

The earlier update removed the former local patches `01`, `03`, `06` and `09`; the 2026-11-05 update removes `02` and `10` (both Draft #36, now merged). In particular, `PS2_READBACK_LOG=1` now uses upstream's bounded logging (the first 20 slow reads, then every 100th slow read). The new base also includes upstream's disc/input bounds checks, safer card/state writes and build/test tooling changes.

`series` applies only the following remaining changes, in order:

| Patch | Purpose and upstream relationship |
| --- | --- |
| `04-window-poll-diagnostics.patch` | SDL event details and a bounded macOS stall sampler; local diagnostic commit `32c8fd7`; rebased onto the 2026-11-05 pin (only the `#include` context changed). |
| `05-host-input-and-audio.patch` | Stop unused IME text input, request 512-frame audio blocks on macOS, log the obtained block size. |
| `07-compact-raster-setup.patch` | Load GS setup fields on demand and keep only three words live; [Draft #39](https://github.com/exoteric33/ps2-native-recomp/pull/39). Retained for the tested M1 Pro/Metal port; upstream's Intel iGPU tests found a performance regression. |
| `08-upscaled-metal-latency.patch` | Prefer one presentation frame in flight on Metal when `PS2_SCALE>1`; an explicit `PS2_FRAME_LATENCY=1..8` overrides this. |
| `11-disc-boot-elf.patch` | Universal native boot from SYSTEM.CNF in the ISO, memory-based loader/live analysis and input replay; [PR #46](https://github.com/exoteric33/ps2-native-recomp/pull/46) (open). Rebased onto the 2026-11-05 pin: `--help` text, the ELF error messages of the span-based loader and the `main.cpp` placement were merged by hand. |

PR states above were checked on 2026-11-05: #36 merged, #39 is still a draft, #46 is open. Patches `05`, `07` and `08` apply unchanged to the new pin; `04` needed one context line (`quickmenu.hpp` now sits between its `#include` anchors); `11` needed the hand merge described above. Patches `02` and `10` were verified to be fully contained in upstream: applying both to the old pin and diffing the touched files against the new pin leaves only unrelated upstream changes, with no VU0 AOT or TOP/ITOP line missing.

Patch numbers are retained so they still identify the same changes. When updating the pin, remove a patch if its change is now upstream; never apply both copies. The build fingerprint includes the pin, ordered patch names and contents.

## Build and local data

`make build` calls `python3 recomp/port.py build --work "$(WORK)"` directly. The Python tool finds an explicit `ISO`, an already linked disc, or the only `.iso` in the repository root. It checks `SYSTEM.CNF` and the extracted ELF's PCSX2 CRC: `SCES_533.12`, `3BA95B70`. Upstream `setup.sh --native-only` builds tools and fetches WebGPU; `port.sh sc3 ... --native-only` translates the game, explores for missing entries and compiles recorded VU programs. `EXPLORE=0` skips exploration on a rebuild. No PNACH patches, forced display mode or startup skips are supplied.

Default paths under `work/ps2-native-recomp/`:

| Path | Contents |
| --- | --- |
| `games/sc3/disc.iso`, `disc/` | Original image link and extracted ELF (build input; not needed at run time). |
| `games/sc3/entries.txt`, `generated/sc3/` | Discovered entry points and generated game code. |
| `games/sc3/vu0/`, `vu1/` | Private raw microcode recordings. |
| `games/sc3/play.ps2`, `keys.ini` | Player card and keyboard settings. |
| `games/sc3/logs/`, `states/` | Logs, reports and quick states. |
| `build/native-sc3/ps2run` | Native executable; the boot ELF is read from the ISO. |
| `build/sc3-port-source.json` | Managed base/tree/fingerprint, allowing repeatable patch application. |
| `build/sc3-port-build.json` | Fingerprint of the last completed game build. |

All of `work/` is ignored. Only explicitly allowed source files are tracked. A patch update resets only the exact source tree previously installed by this wrapper; staged/unstaged user source edits cause an error. Ignored cards, recordings and builds are retained. Keep one game instance running at a time and avoid concurrent builds in the same workspace.

The previous private `work/PS2Recomp/` and `work/ps2-native-recomp-trial/` directories are not deleted. Existing SC3 entries, seven VU0 recordings, 29 VU1 entries, keyboard settings and the memory card were copied to the new default checkout during the local migration. Fresh clones must discover/record their own microcode; these files are not part of this repository. Old PS2Recomp card directories are a different format and are not automatically imported.

## Evidence and limitations

The pre-migration trial's generic VU0 build completed 8723 replay frames with at least 41,970,000 compiled calls compared with the exact interpreter, zero mismatches. A clean upstream-based VU0 build also passed a 700-frame saved-battle test. Synthetic native VU1 and Wasm JIT regressions passed. VU0 AOT remains a draft: broader game/platform coverage, background VU0 compilation and browser recording/export remain follow-up work.

The audio follow-up's disc-free suite passes **232/232** checks; the previous implementation passes 204/232 against the same tests. Coverage includes slow production, 48–160 ms isolated pauses, 512/1024-frame callbacks, PAL50/NTSC60 production, repeated pauses, clicks, starvation after resumption and headroom release. In SC3, a controlled 79 ms pause at battle frame 4800 recovered after resumption in **0.228 s**, versus **1.212 s** before it. In the following 100 frames, audio-pacing frames over 30 ms fell from four to zero; neither run starved audio. A full ordinary trial run completed 8723 frames with four frames over 30 ms, no dry queue/drops and 0.31 s stretched output.

These are local M1 Pro observations. Input playback continues after a known hash divergence, so whole-run counts are not proof of identical guest workloads. Natural host pauses vary. Cold saved-state rendering once consumed 95.8 ms and exhausted audio for about 0.05 s. GPU readback requests can wait about 24–27 ms even though copying the completed data takes under 0.02 ms. Replacing Metal's blocking poll with frequent polling did not improve frame times and was rejected. Some primary host/game pauses remain unattributed; the audio change shortens their aftermath, not their cause.

The Metal path passed direct/single-thread/SDL/software-fallback checks; the user verified resizing and fullscreen. Native keyboard Start is fixed by accepted #32. Original movies/display dialog are enabled, but complete FMV coverage is unverified. Mains power and disabling Low Power Mode help performance. Linux, Windows and browser builds have not been validated for this port configuration.

## Updating the runtime

1. Check upstream PR states and choose an explicit new commit.
2. Change `ps2-native-recomp.commit`; remove merged patches from `series` and `patches/`.
3. Run `make test`, `make test-runtime`, then `make build EXPLORE=0` with your private image/recordings.
4. Test original startup, Escape/Start, a battle, audio, resizing and fullscreen. Use `PS2_VU0_VERIFY=1` only for correctness diagnostics; it double-executes compiled calls and affects performance.
5. Keep generated code, ELF bytes, VU recordings, cards, states, profiles and captures out of commits. Document the new pin, remaining patches and actual validation.

The previous experimental source patches and long investigation notes remain available in `ps2recomp`; they are intentionally not part of the active series.

## Validation of the 2026-11-01 upstream refresh

The initial refresh at pin `783b4b1` plus its then-five remaining patches built successfully through `make build EXPLORE=0`: 218 EE units and 36 VU programs. Those five patch files were unchanged; the managed source tree and completed build fingerprints matched that configuration.

- All 12 wrapper tests pass. `make test-runtime` passes 232/232 audio checks, the poll watchdog test and the VU0 exact-state, override, verifier negative-control and recording/CLI tests. The native VU1/interpreter/Wasm checks also pass.
- Upstream's synthetic tests pass: 84 IOP thread checks, SIF command completion, 39 save-file checks, 32 disc/ELF input checks, 48 IOP bounds checks and 10 Python disc-extraction checks. Translator regressions and the FPU half-float exhaustive test pass.
- The full ps2autotests run reports **54 PASS, 1 known DIFF (`vu/lower/efu`), 0 HANG, 0 FAIL**, exit 0. The EFU difference is the existing 13-line baseline.
- A saved battle was run from frame 2800 to 3100 with the old and new binaries at both 1× and 2×. All 10 sampled framebuffer images match byte for byte. The two post-update runs checked at least 4,380,000 compiled VU0 calls against the interpreter with zero mismatches.
- The updated root launcher completed the 3484-frame power-on input playback using a copied card. As in the earlier control, the replay hash diverges at frame 2325; exit 3 with `--replay-continue` is a continuity check, not deterministic replay equivalence. These game checks ran alongside test builds and are not performance or audio-pacing benchmarks; host stalls and stretched audio remain possible.

The existing player card, keyboard settings, entry list and 33 VU recordings retain their pre-update hashes. Local evidence is in `work/upstream-update-20261101/`, with autotest results under the runtime's `games/_autotests/`. Linux, Windows, other games, and manual input/resize/fullscreen checks were not repeated for this refresh.

## Validation of the 2026-11-05 upstream refresh

Pin `c683565` plus the five remaining patches built through `make build EXPLORE=0` (218 EE units, 36 VU programs; the runtime reports 36 statically registered compiled vector programs). All 12 wrapper tests and `make test-runtime` pass (232/232 audio checks, the poll watchdog test, the TOP/ITOP, exact-state and fallback VU0 checks, the verifier negative control and the CLI checks). A 300-frame headless smoke run boots from the ISO alone (`--disc` plus `--game-dir`, no ELF argument) on Metal and writes non-black frames, using a scratch memory card.

Not repeated: upstream's own synthetic suites and ps2autotests, the saved-battle framebuffer comparison, manual window/input/fullscreen checks, and Linux/Windows builds.

## VU0 TOP/ITOP follow-up validation

Historical: patches `02` and `10` mentioned here are now part of upstream (#36).

The new synthetic regression failed before the correction: compiled VU0 read VU1's nonzero TOP/ITOP while the interpreter returned VU0's zero TOP and VIF0 ITOP. After the fix, all 36 mixed-unit cases per driver run pass, including updated VIF values with a cached program, VI0 writes, conditional branches and addressed loads/stores. The VU0 suite is now included in upstream's Linux/macOS CI. VU1's live-library ABI is unchanged and the generator version is bumped to invalidate stale generated-code caches.

On the PR branch, VU0, native VU1/Wasm, the VU control-flow regressions, the native build, IOP/SIF checks and the full 54 PASS / 1 known EFU DIFF suite pass. On the pinned port with all six patches, `make build EXPLORE=0`, all 12 wrapper tests and `make test-runtime` pass (232 audio checks, watchdog and the extended VU0 suite). The 300-frame saved battle at both 1× and 2× again matches all 10 pre-fix framebuffer samples, with at least 4,380,000 verified VU0 calls and zero mismatches. These runs used verification and framebuffer capture and were deliberately slower than ordinary play; the launcher does not enable those diagnostics by default. Existing player files retain their hashes.

This fixes a reproduced VU0 unit-selection bug. Local evidence is in `work/ps2-native-recomp-vu0-pr/validation/top-itop-fix/`; no game code or diagnostic memory dump is included in the patch.

## Validation of the original migration

The original migration at pin `b98334b` plus its then-five-patch series was built through `make build EXPLORE=0`. All 12 disc-free wrapper tests passed, including repeat preparation, source-edit preservation, rollback, image selection, native-only arguments and failed-build stamp invalidation. `make test-runtime` passed 232/232 audio checks, the watchdog gate test and the exact VU0 differential/CLI/negative-control suite. That pinned base also passed its 84 IOP thread-manager checks and SIF completion checks.

At that pin, `make run` completed all 8723 frames of the private input playback (exit 0), using a copied card, original ELF/ISO and no VU0 verifier. Audio reported zero dry events, zero dropped samples and 0.29 s stretched output, slowest ratio x1.57. This checks startup/menu/battle progression through the new entry point; it retains the known continue-on-hash-divergence limitation. Local evidence is in `work/migration-validation/`, with build/test logs under `work/`. That executable was about 44.6 MiB on arm64; no executable or game-derived data is tracked.

## Graphics performance

`PS2_SCALE=2 make run` renders at twice the native width and height. This increases pixel work fourfold; it can still exceed the PAL 20 ms frame budget on an M1 Pro. `PS2_LOOK=soft_edges` only softens the final image and does not replace texture minification filtering.

The compact GS setup patch reduced the sampled scene's raster benchmark from 19.2 to 16.1 ms at 2× (6.8 to 6.5 ms at 1×), with unchanged framebuffer checks in the test scene. These are measurements of one captured scene on Metal, not a guarantee for every scene or GPU. In [upstream testing](https://github.com/exoteric33/ps2-native-recomp/pull/39#issuecomment-6549698000), 840 images across five games matched, but raster time increased by about 2% on D3D12 and 6–9% on Vulkan on an Intel laptop iGPU. The patch remains a draft and is retained here for the tested Mac configuration. The shorter upscaled Metal presentation queue reduces work ahead of synchronous VRAM reads; it does not make those reads free. Set `PS2_FRAME_LATENCY=2` to compare the previous presentation queue setting.

## Boot directly from ISO (2026-11-02)

The universal ISO-boot change is developed against upstream `8cd87cd`; `11-disc-boot-elf.patch` backports it onto the pinned runtime plus the six existing patches, preserving local VU0 recording. `ps2run --disc /path/to/disc.iso --window` reads SYSTEM.CNF and its BOOT2 ELF into memory through the existing ISO9660 reader, with no extraction or extra embedded payload. Explicit ELF arguments preserve the existing path for patched/special executables and disc-free programs. The build still extracts its translation inputs; the wrapper no longer requires those files when launching the game.

Live EE translation and deferred program analysis use the same ELF bytes, so caches remain compatible with external-file boot. The transient host boot buffer is freed after loading; the live translator retains its analysis input when enabled. `--game-dir` keeps both live caches, VU recording and existing entries/overlays in the game folder independently of the ISO location; the wrapper and `port.sh` pass it explicitly. An explicit memory card/quick directory continues to control user save locations. New recordings carry `disc-program 1` and the selected game folder; the replay helper preserves both.

The source-only patch includes bounded configuration/ELF reads, malformed-image checks, a synthetic end-to-end regression that removes its original ELF and forces live translation, CI wiring for Linux/macOS, and upstream documentation in `docs/disc-boot.md`. The native runner's CMake embedding path from the earlier local experiment is removed. The upstream-ready description and local evidence are kept in `work/iso-boot-validation/`.

The 2026-11-04 review update fixes the Windows live-EE call's string/path shadowing and adds `--game-dir` to select the work folder independently of an external ISO. llvm-mingw targeting Windows x86_64 reproduces the old compilation error and accepts the updated host in window/GPU and headless configurations (syntax checks; no full Windows run). The synthetic ISO/live/cache/replay test also covers a portable runner, separate Unicode game folder, persistent entries/overlays, environment overrides and invalid directories. Save-file checks pass 43/43, including game/card/quick-folder precedence; the full ps2autotests rerun remains 54 PASS / 1 known EFU DIFF with no failures or hangs. SH2 on Metal with the external ISO and game folder matches all six prior framebuffers, raw SPU2 audio and 120 checkpoints over 1,800 frames, and replays identically. A 30-frame window run places VU recording, live caches, keys and logs in that game folder.

Validation on Apple Silicon macOS: the clean upstream worktree at `8cd87cde45d841cb660f00b1d682b1a1201e5b4f` passes 49 synthetic disc/input checks, the ISO-only boot/live/cache/replay regression, and the tail-call/BSS/fallthrough regressions. The full ps2autotests run is 54 PASS / 1 known EFU DIFF, 0 HANG / 0 FAIL. A separate run of all 55 built free programs with `--disc` only produces exactly the same test output as external-ELF boot. The local port passes all 12 wrapper tests and `make test-runtime` (232 audio checks, watchdog and VU0/CLI regressions).

SC3 reaches 360 frames with its extracted ELF temporarily moved away: three sampled framebuffers and raw SPU2 audio are byte-identical to the pre-feature binary, and the original player card is unchanged. A standalone copied runner starts and replays a new 30-frame recording with ISO only. The rebuilt binary is about 2 KiB larger than the original runner, rather than carrying the earlier 5 MB ELF resource. Windows, Linux and browser builds have not been run locally; the new regression is wired into existing Linux/macOS CI. Upstream submission text is in `work/iso-boot-validation/PR.md`; the patch itself is `patches/11-disc-boot-elf.patch`.

Silent Hill 2 was also checked using the local `disc.iso` in `work/ps2-native-recomp-vu0-pr/games/sh2-top-itop/` (USA `SLUS_202.28`). PR commit `40bb555`, without additional runtime patches, completes 1,800 frames through difficulty selection on M1 Pro / Metal: all six frame captures, raw SPU2 audio and 120 EE checkpoints match external-ELF boot. A fresh recording replays to the end with EE live enabled and the test ELF absent. Source player files remain unchanged. Private evidence: `work/iso-boot-validation/sh2/REPORT.md`.
