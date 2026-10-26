#!/usr/bin/env bash
# Reproduces the static recompilation of Soulcalibur III (PAL, SCES_533.12) with PS2Recomp.
# Usage: ./recomp/build.sh [WORK_DIR]   (default: ./recomp/work, ~7 GB free space needed)
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
WORK="${1:-$HERE/work}"
ISO="$ROOT/Soulcalibur III (Europe, Australia) (En,Fr,De,Es,It) (v2.00).iso"
COMMIT="$(cat "$HERE/PS2Recomp.commit")"

mkdir -p "$WORK"
cd "$WORK"

# 1. Extract the disc (the runtime resolves cdrom0: relative to the ELF directory).
if [ ! -f game/SCES_533.12 ]; then
  mkdir -p game
  7z x -y -ogame "$ISO"
fi

# 2. Fetch PS2Recomp at the tested commit and apply local patches.
if [ ! -d PS2Recomp ]; then
  git clone --recurse-submodules https://github.com/ran-j/PS2Recomp.git
  git -C PS2Recomp checkout "$COMMIT"
  git -C PS2Recomp apply "$HERE"/[0-9][0-9][0-9][0-9]-*.patch
fi
# Pre-fetch dependencies with shallow clones: FetchContent's full clones of github.com repos failed
# intermittently ("HTTP 400 ... expected 'packfile'"), also for toml11's test submodule.
# Format: <FetchContent name>|<repo>|<tag>
DEPS=(
  "nlohmann_json|https://github.com/nlohmann/json.git|v3.11.3"
  "toml11|https://github.com/ToruNiina/toml11.git|v4.4.0"
  "fmt|https://github.com/fmtlib/fmt.git|12.1.0"
  "rabbitizer|https://github.com/Decompollaborate/rabbitizer.git|1.14.3"
  "raylib|https://github.com/raysan5/raylib.git|5.5"
)
DEP_FLAGS=()
mkdir -p deps
for dep in "${DEPS[@]}"; do
  IFS='|' read -r name repo tag <<<"$dep"
  if [ ! -d "deps/$name" ]; then
    git clone --depth 1 --branch "$tag" "$repo" "deps/$name"
  fi
  upper="$(echo "$name" | tr '[:lower:]' '[:upper:]')"
  DEP_FLAGS+=("-DFETCHCONTENT_SOURCE_DIR_${upper}=$WORK/deps/$name")
done
# paraLLEl-GS (LGPL-3.0+), the default GS renderer: Vulkan compute, MoltenVK on macOS
# (brew install molten-vk vulkan-loader). Only the submodules its standalone build needs, a macOS
# fix for Granite (no clock_nanosleep), and fixes to paraLLEl-GS itself (parallel-gs/gs/).
if [ ! -d deps/parallel-gs ]; then
  git clone https://github.com/Arntzen-Software/parallel-gs.git deps/parallel-gs
  git -C deps/parallel-gs checkout "$(cat "$HERE/parallel-gs.commit")"
  (cd deps/parallel-gs && ./checkout_submodules.sh)
  for p in "$HERE"/parallel-gs/*.patch; do git -C deps/parallel-gs/Granite apply "$p"; done
  for p in "$HERE"/parallel-gs/gs/*.patch; do git -C deps/parallel-gs apply "$p"; done
fi
DEP_FLAGS+=("-DPS2X_PARALLEL_GS_DIR=$WORK/deps/parallel-gs")
# ccache (brew install ccache) for the ~2200 generated translation units: a regeneration rewrites
# every file even when most functions come out identical, and those are then cache hits. The runner
# uses a precompiled header, so ccache needs pch_defines/time_macros sloppiness and clang must not
# stamp the PCH with header mtimes (-fno-pch-timestamp; that also stops a touched header from
# invalidating the PCH). The settings travel in the launcher so they apply to every build of this tree.
if command -v ccache >/dev/null 2>&1; then
  LAUNCHER="/usr/bin/env;CCACHE_SLOPPINESS=pch_defines,time_macros,include_file_mtime,include_file_ctime;CCACHE_MAXSIZE=10G;ccache"
  DEP_FLAGS+=("-DCMAKE_C_COMPILER_LAUNCHER=$LAUNCHER" "-DCMAKE_CXX_COMPILER_LAUNCHER=$LAUNCHER"
              "-DCMAKE_CXX_FLAGS=-Xclang -fno-pch-timestamp")
fi

# 3. Build recompiler + runtime. ENABLE_FFMPEG=ON enables movies; the ImGui debug UI is disabled. LTO is off
#    (patch 0005): the thin-LTO link of ~2100 generated objects took over an hour per iteration.
cd PS2Recomp
cmake -S . -B out/build -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DPS2X_BUILD_STUDIO=OFF -DPS2X_BUILD_TEST=OFF \
  "-DPS2X_ENABLE_FFMPEG=${ENABLE_FFMPEG:-OFF}" -DPS2X_ENABLE_DEBUG_UI=OFF \
  -DPS2X_ENABLE_LTO=OFF \
  -DPS2X_ENABLE_AGRESSIVE_LOGS=OFF -DPS2X_ENABLE_RUNTIME_LOGS=OFF -DPS2X_ENABLE_IOP_RPC_TRACE=ON \
  "${DEP_FLAGS[@]}"
cmake --build out/build --target ps2_recomp
cd ..

# 4. Recompile the ELF (sc3.toml uses GAME_DIR as a placeholder for the extracted disc).
#    Two passes: the first one produces the function table, from which pointer_entries.py derives the
#    code addresses that are only reachable through data pointers (vtables, callbacks). They are added
#    as entry points in the second pass, otherwise the game dies on the first such indirect call.
mkdir -p gen && cd gen
sed "s#GAME_DIR#$WORK/game#g" "$HERE/sc3.toml" > sc3.base.toml
# Use the Ghidra function/label map when present (./ghidra_export.sh); the analyzer-only function
# boundaries miss jump-table targets and fall-through labels.
if [ -f "$WORK/ghidra-export/sc3_functions.csv" ]; then
  sed -i.bak "s#^ghidra_output = .*#ghidra_output = \"$WORK/ghidra-export/sc3_functions.csv\"#" sc3.base.toml
fi
# PAL60 without the display-mode dialog (see display_mode.toml); DISPLAY_DIALOG=1 keeps the dialog.
if [ "${DISPLAY_DIALOG:-0}" != 1 ]; then
  cat "$HERE/display_mode.toml" >> sc3.base.toml
fi
# The two start-up movies (see skip_intro.toml); SKIP_INTRO=0 keeps them (they need ENABLE_FFMPEG=ON).
if [ "${SKIP_INTRO:-1}" = 1 ]; then
  cat "$HERE/skip_intro.toml" >> sc3.base.toml
fi
rm -rf output
"$WORK/PS2Recomp/out/build/ps2xRecomp/ps2_recomp" sc3.base.toml
python3 -I "$HERE/pointer_entries.py" "$WORK/game/SCES_533.12" output/register_functions.cpp > ptr_entries.toml
cat ptr_entries.toml sc3.base.toml > sc3.toml
rm -rf output
"$WORK/PS2Recomp/out/build/ps2xRecomp/ps2_recomp" sc3.toml
cd ..

# 5. Feed the generated code to the runner and build it.
RT=PS2Recomp/ps2xRuntime
# rsync instead of cp: with the Ghidra map there are ~66 000 generated files (argument list too long).
rsync -a --delete --include='*.cpp' --exclude='*' gen/output/ "$RT/src/runner/"
rsync -a --include='*.h' --exclude='*' gen/output/ "$RT/include/"
# VU0 and VU1 microprograms recorded with PS2_VU_PROGRAM_PROFILE=$WORK/vu-profiles are compiled into the runner
# (game data: the directory stays local). Without it every VU program is interpreted.
VU_PROFILES=""
if [ -f "$WORK/vu-profiles/entries.txt" ]; then
  VU_PROFILES="$WORK/vu-profiles"
fi
cmake -S PS2Recomp -B PS2Recomp/out/build -DPS2X_VU_PROGRAM_PROFILES="$VU_PROFILES" >/dev/null
cmake --build PS2Recomp/out/build --target ps2EntryRunner -j"$(sysctl -n hw.ncpu 2>/dev/null || nproc)"

echo
echo "Done. Launch the game with:"
echo "  make run"
