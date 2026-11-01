# ps2-native-recomp port notes

`main` uses [exoteric33/ps2-native-recomp](https://github.com/exoteric33/ps2-native-recomp). The old PS2Recomp port, its patch series, Ghidra/TOML setup and investigation history are preserved at branch **`ps2recomp`**. Commit IDs differ from the original local history because personal author email addresses were replaced with GitHub noreply addresses before publication. Historical performance and platform claims from that implementation do not apply to the current one.

## Reproducible source set

Upstream pin: **`783b4b1fc39330033b6f73f070c4185d2a6309b7`**, the upstream `main` tip checked on 2026-11-01, stored in `ps2-native-recomp.commit`. It contains these accepted contributions; none is reapplied locally:

| Contribution | Included upstream |
| --- | --- |
| SIF command completion / keyboard Start | [#32](https://github.com/exoteric33/ps2-native-recomp/pull/32) |
| Original audio recovery allowance | [#33](https://github.com/exoteric33/ps2-native-recomp/pull/33), merged as `91d9b44` |
| POSIX thread CPU timer | [#34](https://github.com/exoteric33/ps2-native-recomp/pull/34) |
| Direct Cocoa Metal/WebGPU presentation | [#35](https://github.com/exoteric33/ps2-native-recomp/pull/35), merge `4ba502d` |
| Fast audio recovery after isolated producer pauses | [#37](https://github.com/exoteric33/ps2-native-recomp/pull/37), merge `384736a` |
| Optional game window title and macOS resident memory | [#38](https://github.com/exoteric33/ps2-native-recomp/pull/38), merge `8c6f712` |
| Opt-in, bounded GPU readback diagnostics | [#40](https://github.com/exoteric33/ps2-native-recomp/pull/40), merge `6f84ba1` |

The update removes the former local patches `01`, `03`, `06` and `09`. In particular, `PS2_READBACK_LOG=1` now uses upstream's bounded logging (the first 20 slow reads, then every 100th slow read). The new base also includes upstream's disc/input bounds checks, safer card/state writes and build/test tooling changes.

`series` applies only the following remaining changes, in order:

| Patch | Purpose and upstream relationship |
| --- | --- |
| `02-pr36-vu0-aot.patch` | Generic recorded VU0 AOT, exact arithmetic, interpreter fallback and differential verification; [Draft #36](https://github.com/exoteric33/ps2-native-recomp/pull/36). |
| `04-window-poll-diagnostics.patch` | SDL event details and a bounded macOS stall sampler; local diagnostic commit `32c8fd7`. |
| `05-host-input-and-audio.patch` | Stop unused IME text input, request 512-frame audio blocks on macOS, log the obtained block size. |
| `07-compact-raster-setup.patch` | Load GS setup fields on demand and keep only three words live; [Draft #39](https://github.com/exoteric33/ps2-native-recomp/pull/39). Retained for the tested M1 Pro/Metal port; upstream's Intel iGPU tests found a performance regression. |
| `08-upscaled-metal-latency.patch` | Prefer one presentation frame in flight on Metal when `PS2_SCALE>1`; an explicit `PS2_FRAME_LATENCY=1..8` overrides this. |

PR states above were checked on 2026-11-01. The five remaining patches apply without changes to the new pin. Patch numbers are retained so they still identify the same changes. When updating the pin, remove a patch if its change is now upstream; never apply both copies. The build fingerprint includes the pin, ordered patch names and contents.

## Build and local data

`make build` calls `python3 recomp/port.py build --work "$(WORK)"` directly. The Python tool finds an explicit `ISO`, an already linked disc, or the only `.iso` in the repository root. It checks `SYSTEM.CNF` and the extracted ELF's PCSX2 CRC: `SCES_533.12`, `3BA95B70`. Upstream `setup.sh --native-only` builds tools and fetches WebGPU; `port.sh sc3 ... --native-only` translates the game, explores for missing entries and compiles recorded VU programs. `EXPLORE=0` skips exploration on a rebuild. No PNACH patches, forced display mode or startup skips are supplied.

Default paths under `work/ps2-native-recomp/`:

| Path | Contents |
| --- | --- |
| `games/sc3/disc.iso`, `disc/` | Original image link and extracted ELF. |
| `games/sc3/entries.txt`, `generated/sc3/` | Discovered entry points and generated game code. |
| `games/sc3/vu0/`, `vu1/` | Private raw microcode recordings. |
| `games/sc3/play.ps2`, `keys.ini` | Player card and keyboard settings. |
| `games/sc3/logs/`, `states/` | Logs, reports and quick states. |
| `build/native-sc3/ps2run` | Native executable. |
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

Pin `783b4b1` plus the five remaining patches built successfully through `make build EXPLORE=0`: 218 EE units and 36 VU programs. All five patch files are unchanged; the managed source tree and completed build fingerprints match the new configuration.

- All 12 wrapper tests pass. `make test-runtime` passes 232/232 audio checks, the poll watchdog test and the VU0 exact-state, override, verifier negative-control and recording/CLI tests. The native VU1/interpreter/Wasm checks also pass.
- Upstream's synthetic tests pass: 84 IOP thread checks, SIF command completion, 39 save-file checks, 32 disc/ELF input checks, 48 IOP bounds checks and 10 Python disc-extraction checks. Translator regressions and the FPU half-float exhaustive test pass.
- The full ps2autotests run reports **54 PASS, 1 known DIFF (`vu/lower/efu`), 0 HANG, 0 FAIL**, exit 0. The EFU difference is the existing 13-line baseline.
- A saved battle was run from frame 2800 to 3100 with the old and new binaries at both 1× and 2×. All 10 sampled framebuffer images match byte for byte. The two post-update runs checked at least 4,380,000 compiled VU0 calls against the interpreter with zero mismatches.
- The updated root launcher completed the 3484-frame power-on input playback using a copied card. As in the earlier control, the replay hash diverges at frame 2325; exit 3 with `--replay-continue` is a continuity check, not deterministic replay equivalence. These game checks ran alongside test builds and are not performance or audio-pacing benchmarks; host stalls and stretched audio remain possible.

The existing player card, keyboard settings, entry list and 33 VU recordings retain their pre-update hashes. Local evidence is in `work/upstream-update-20261101/`, with autotest results under the runtime's `games/_autotests/`. Linux, Windows, other games, and manual input/resize/fullscreen checks were not repeated for this refresh.

## Validation of the original migration

The original migration at pin `b98334b` plus its then-five-patch series was built through `make build EXPLORE=0`. All 12 disc-free wrapper tests passed, including repeat preparation, source-edit preservation, rollback, image selection, native-only arguments and failed-build stamp invalidation. `make test-runtime` passed 232/232 audio checks, the watchdog gate test and the exact VU0 differential/CLI/negative-control suite. That pinned base also passed its 84 IOP thread-manager checks and SIF completion checks.

At that pin, `make run` completed all 8723 frames of the private input playback (exit 0), using a copied card, original ELF/ISO and no VU0 verifier. Audio reported zero dry events, zero dropped samples and 0.29 s stretched output, slowest ratio x1.57. This checks startup/menu/battle progression through the new entry point; it retains the known continue-on-hash-divergence limitation. Local evidence is in `work/migration-validation/`, with build/test logs under `work/`. That executable was about 44.6 MiB on arm64; no executable or game-derived data is tracked.

## Graphics performance

`PS2_SCALE=2 make run` renders at twice the native width and height. This increases pixel work fourfold; it can still exceed the PAL 20 ms frame budget on an M1 Pro. `PS2_LOOK=soft_edges` only softens the final image and does not replace texture minification filtering.

The compact GS setup patch reduced the sampled scene's raster benchmark from 19.2 to 16.1 ms at 2× (6.8 to 6.5 ms at 1×), with unchanged framebuffer checks in the test scene. These are measurements of one captured scene on Metal, not a guarantee for every scene or GPU. In [upstream testing](https://github.com/exoteric33/ps2-native-recomp/pull/39#issuecomment-6549698000), 840 images across five games matched, but raster time increased by about 2% on D3D12 and 6–9% on Vulkan on an Intel laptop iGPU. The patch remains a draft and is retained here for the tested Mac configuration. The shorter upscaled Metal presentation queue reduces work ahead of synchronous VRAM reads; it does not make those reads free. Set `PS2_FRAME_LATENCY=2` to compare the previous presentation queue setting.
