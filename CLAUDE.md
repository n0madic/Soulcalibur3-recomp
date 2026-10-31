# Working on this port

`main` uses **exoteric33/ps2-native-recomp**, not ran-j/PS2Recomp. The former implementation and its technical history are preserved in branch `ps2recomp`. Read `README.md` for user commands and `recomp/README.md` for the current source pin, patches and validation.

## Source ownership

- `recomp/ps2-native-recomp.commit` pins the upstream commit.
- `recomp/series` names the remaining patches in order. Accepted upstream changes are not duplicated: #32 (SIF/Start), #33 (initial audio pacing) and #34 (CPU clock) are already in the current base.
- `recomp/patches/` contains pending upstream contributions and local host/diagnostic changes. Keep each independent area in one patch; do not revive the obsolete PS2Recomp/paraLLEl-GS/TOML/Ghidra series.
- `recomp/port.py` manages source preparation, disc validation, build and launch. `Makefile` and `launch.command` call it directly.
- `recomp/tests/` tests the wrapper without a disc. `make test-runtime` runs synthetic audio, VU0 and watchdog tests in the prepared runtime.
- `recomp/work/` is entirely private: upstream checkouts, ISO/ELF, generated code, entry lists, VU recordings, memory cards, states, measurements and build caches must never be committed or included in patches. The root `.gitignore` is a source allowlist.

## Commands

```sh
make build ISO='/path/to/disc.iso'
make build EXPLORE=0
make run
make run ARGS='--fullscreen'
make test
make test-runtime
```

The tested disc is PAL `SCES_533.12`, CRC `3BA95B70`. The wrapper uses original instructions, retains the display-mode dialog, and supplies no movie-skip or PNACH overrides. Escape is Start; help is F1. Defaults come from upstream `host/keymap.cpp` and are remappable through the private `games/sc3/keys.ini`.

The default runner is `recomp/work/ps2-native-recomp/build/native-sc3/ps2run`. The launcher uses its checkout as cwd and supplies the original ELF, ISO and `games/sc3/play.ps2`. Do not use the former `work/game` cwd, `ps2EntryRunner`, raylib controls or Vulkan/paraLLEl-GS options.

## Changing patches

The default checkout is managed: patches are staged in its index and recorded by a source stamp. Direct edits there are detected on the next preparation. Develop in a separate clean worktree at the pinned commit, apply the current series, change only the owning area, run its regression tests, and export a source-only diff. Keep upstream patch contents intact until superseded, with separate local fixes where needed. Do not generate patches from a dirty trial tree containing temporary instrumentation.

When a PR is merged, advance the pin and remove its now-redundant patch. Rebuild and test the complete remaining series; update both documentation files, controls and build commands when behavior changes. The old working trees remain useful references, not the current build source.

## Measuring

Run one game instance at a time. Measure on mains power with Low Power Mode disabled; compare runs on the same saved state or with a controlled pause. Natural host scheduling and GPU waits vary. Old input replays have a known hash divergence; continue-on-divergence runs do not prove deterministic state equivalence. Do not describe their aggregate timing difference as a controlled speedup.

`PS2_HITCH_LOG=30` is enabled by the launcher; logs separate sound/window waits from EE CPU time. GPU readback waiting and startup render warmup are separate from audio recovery. `PS2_VU0_VERIFY=1` compares compiled VU0 state against the exact interpreter, retaining/blacklisting mismatches, but double execution is slower. Remove all temporary test hooks before exporting patches. Keep user-facing instructions free of experimental diagnostic procedures unless they solve a concrete problem.

This repository's tooling retains GPL-3.0. The fetched ps2-native-recomp runtime is MIT; third-party code retains its licenses. Game-derived files remain local regardless of source license.
