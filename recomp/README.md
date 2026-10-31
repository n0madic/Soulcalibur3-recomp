# ps2-native-recomp port notes

`main` uses [exoteric33/ps2-native-recomp](https://github.com/exoteric33/ps2-native-recomp). The old PS2Recomp port, its patch series, Ghidra/TOML setup and investigation history are preserved at branch **`ps2recomp`**, snapshot `4b880ad`. Its original main tip was `56713f1`. Historical performance and platform claims from that implementation do not apply to the current one.

## Reproducible source set

Upstream pin: **`b98334b2c9b5cac112661dc5a94afb1afafb1321`**, stored in `ps2-native-recomp.commit`. It already contains these accepted contributions; none is reapplied locally:

| Contribution | Included upstream |
| --- | --- |
| SIF command completion / keyboard Start | [#32](https://github.com/exoteric33/ps2-native-recomp/pull/32) |
| Original audio recovery allowance | [#33](https://github.com/exoteric33/ps2-native-recomp/pull/33), merged as `91d9b44` |
| POSIX thread CPU timer | [#34](https://github.com/exoteric33/ps2-native-recomp/pull/34) |

`series` applies only the following remaining changes, in order:

| Patch | Purpose and upstream relationship |
| --- | --- |
| `01-pr35-metal.patch` | Direct Cocoa Metal/WebGPU presentation, [#35](https://github.com/exoteric33/ps2-native-recomp/pull/35). |
| `02-pr36-vu0-aot.patch` | Generic recorded VU0 AOT, exact arithmetic, interpreter fallback and differential verification; [Draft #36](https://github.com/exoteric33/ps2-native-recomp/pull/36). |
| `03-pr37-audio-recovery.patch` | Fast recovery after isolated producer pauses, [#37](https://github.com/exoteric33/ps2-native-recomp/pull/37); follows merged #33. |
| `04-window-poll-diagnostics.patch` | SDL event details and a bounded macOS stall sampler; local diagnostic commit `32c8fd7`. |
| `05-host-input-and-audio.patch` | Stop unused IME text input, request 512-frame audio blocks on macOS, log the obtained block size. |
| `06-window-title-and-macos-ram.patch` | Optional `PS2_WINDOW_TITLE` prefix (launcher default: `Soulcalibur III`), and current resident process memory via Mach on macOS. |

The PR labels above describe what is absent from the pinned commit, not a live merge-status check. When updating the pin, remove a patch if its change is now upstream; never apply both copies. The build fingerprint includes the pin, ordered patch names and contents.

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

## Validation of the migrated main

The new pinned checkout plus the five-patch series was built through `make build EXPLORE=0`. All 12 disc-free wrapper tests pass, including repeat preparation, source-edit preservation, rollback, image selection, native-only arguments and failed-build stamp invalidation. `make test-runtime` passes 232/232 audio checks, the watchdog gate test and the exact VU0 differential/CLI/negative-control suite. The pinned base also passes its 84 IOP thread-manager checks and SIF completion checks.

The new root `make run` completed all 8723 frames of the private input playback (exit 0), using a copied card, original ELF/ISO and no VU0 verifier. Audio reported zero dry events, zero dropped samples and 0.29 s stretched output, slowest ratio x1.57. This checks startup/menu/battle progression through the new entry point; it retains the known continue-on-hash-divergence limitation. Local evidence is in `work/migration-validation/`, with build/test logs under `work/`. The executable is about 44.6 MiB on arm64; no executable or game-derived data is tracked.
