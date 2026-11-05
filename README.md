# Soulcalibur III — native recompilation

A native port of **Soulcalibur III** for Apple Silicon Macs, based on [ps2-native-recomp](https://github.com/exoteric33/ps2-native-recomp). The game's EE machine code is translated ahead of time into C++; the runtime provides the PS2 hardware, IOP, audio, graphics and input. Recorded VU0/VU1 microprograms can also be compiled.

The previous PS2Recomp implementation is preserved in the **`ps2recomp` branch**. `main` now builds and launches ps2-native-recomp. Its patches, settings and measurements are separate from the old port.

This repository contains tooling and source patches only. Supply your own legally obtained disc image; disc files, generated code, microcode recordings, cards, states and binaries remain local.

## Status

- Tested release: PAL `SCES_533.12`, ELF CRC **`3BA95B70`** (the Europe/Australia v2.00 image used for development). Other revisions are rejected by the build wrapper.
- Boot, menus, input and battles have been exercised on an M1 Pro. Escape is Start.
- Graphics use WebGPU with direct **Metal** presentation on macOS. Window resizing and fullscreen have been checked. SDL presentation remains available.
- Original startup instructions are used: no movie skips, forced PAL60 choice or PNACH overrides. The display-mode dialog remains enabled. Complete FMV coverage is still unverified.
- Audio stretching and recovery after isolated pauses are implemented. Some host/render stalls and cold-load audio starvation remain; this is an experimental port, not a finished release.
- Apple Silicon macOS is the tested platform. Old Linux/Windows PS2Recomp build results do not establish support for this implementation.

## Build

Install Xcode Command Line Tools and the native build dependencies:

```sh
xcode-select --install
brew install bash cmake ninja python3 sdl2
brew install ccache  # optional
```

Python 3.9+, Bash 4+ and a C++20 compiler with `<format>` are required. The wrapper selects Homebrew Bash on macOS; the upstream scripts choose a suitable compiler. Native WebGPU binaries are fetched by upstream setup. Emscripten, Ghidra, FFmpeg and MoltenVK are not required by this build.

Put the disc image in the repository root, then run:

```sh
make build
```

With several images or a disc elsewhere, provide its path:

```sh
make build ISO='/path/to/Soulcalibur III.iso'
```

The wrapper checks out the exact commit in `recomp/ps2-native-recomp.commit`, applies `recomp/series`, validates the boot ELF and calls upstream's native port pipeline. Initial exploration runs discover additional code and record VU entries. They use a separate exploration card. The first build can take several minutes; keep several GB free for builds and caches in addition to the ISO.

The upstream pin was refreshed on 2026-11-05. Metal presentation, audio pause recovery, game window titles/macOS memory reporting, bounded readback diagnostics and the VU0 AOT (with its TOP/ITOP fix) now come from upstream; five local patches remain. See the [patch list](recomp/README.md#reproducible-source-set) for details.

To rebuild using entries and recordings already captured, without automatic exploration:

```sh
make build EXPLORE=0
```

To limit compiler concurrency, set `PS2_JOBS=4`. A different local workspace can be selected with `make build WORK='/path/to/work'`; use the same `WORK` with `make run`. Build configuration and game data live under `recomp/work/ps2-native-recomp/` by default. An already linked disc can be reused on later builds.

## Run

```sh
make run
make run ARGS='--fullscreen'
```

Or double-click `launch.command`. The default executable is:

```
recomp/work/ps2-native-recomp/build/native-sc3/ps2run
```

The launcher reads the boot ELF directly from the ISO. The extracted ELF is needed only while building; it is not required when playing. Saves go to `games/sc3/play.ps2` inside that checkout. Logs, quick states and VU recordings stay in the same game's local directories. `make run` rejects a build whose source pin/patch fingerprint is out of date; rebuild after changing the series.

You can also launch the built runner directly with just the ISO as game input:

```sh
recomp/work/ps2-native-recomp/build/native-sc3/ps2run --disc '/path/to/Soulcalibur III.iso' --game-dir recomp/work/ps2-native-recomp/games/sc3 --window --memcard '/path/to/play.ps2'
```

The memory card is optional user save data. `--game-dir` keeps VU/EE caches and captured build inputs in the game's work folder even if the ISO lives elsewhere. The build still extracts the ELF from the ISO for translation. At launch the runner reads it back from the ISO into memory; live EE compilation uses those same bytes. The native executable contains no additional copy of the ELF.

### Controls

The active game window receives keyboard input. On first launch the port installs its fighting layout from `recomp/keys.ini`; existing local `keys.ini` settings take precedence.

| Action | Input |
| --- | --- |
| Start / Select | **Esc** / Tab or Backspace |
| Square: horizontal attack (A) | **Z** |
| Triangle: vertical attack (B) | **V** |
| Circle: kick (K) | **C** |
| Cross: guard (G) / menu confirm | **X**, Enter or Keypad Enter |
| D-pad / left stick | Arrow keys / W A S D |
| L1 / R1 | Left Shift / F |
| L2 / R2 | Q / R |
| Key help / fullscreen | F1 / F11 |
| Quick save / quick load | F5 / F8 |
| Problem report | F9 |

L3, R3 and the combined rage shortcut are unbound to free X/C/V. Edit `games/sc3/keys.ini` to remap controls; the runtime reloads it when the game regains focus. Delete that file and launch with `make run` to restore the port defaults. Controllers are supported by the runtime, but keyboard input is the locally tested path.

### Useful runtime options

```sh
PS2_SCALE=2 make run             # higher internal resolution, more GPU work
PS2_SDL_RENDERER=1 make run      # fallback presentation instead of direct Metal
PS2_VU0_VERIFY=1 make run        # diagnostic double execution; slower
```

Unknown VU0/VU1 programs are recorded automatically. After playing a new mode, `make build EXPLORE=0` compiles the new recordings. Do not publish those recordings: they contain game microcode. `PS2_VU0_INTERPRET=1` forces the VU0 interpreter for comparisons.

The launcher enables `PS2_HITCH_LOG=30`. `PS2_HITCH_LOG='' make run` disables it. Slow SDL event polling can trigger bounded local stack captures on macOS; see the technical notes.

## Tests and maintenance

```sh
make test          # disc-free wrapper tests
make test-runtime  # synthetic audio, VU0 and watchdog tests
```

The source checkout is managed by the wrapper. It verifies the installed patch tree before reuse, refuses unrelated staged/unstaged edits, and updates its own patch state when the pin or series changes. Use a separate worktree for runtime development. It preserves ignored game files when changing source versions; never run `git clean -fdx` in the game checkout.

[Technical notes](recomp/README.md) describe the patch set, upstream status, validation and remaining limitations. [CLAUDE.md](CLAUDE.md) describes the contribution workflow. The GPL-3.0 license in [LICENSE](LICENSE) covers this repository's tooling; ps2-native-recomp is MIT-licensed and fetched dependencies retain their own licenses.

No game content is distributed. Soulcalibur is a trademark of its owner; this project is not affiliated with or endorsed by Bandai Namco.
