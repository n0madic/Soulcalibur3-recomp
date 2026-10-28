#!/usr/bin/env bash
# Trial cross-build of the runner for Windows x86_64 with llvm-mingw, from the source tree that
# recomp/build.sh has already patched and fed with the generated code.
# Usage: LLVM_MINGW_ROOT=<llvm-mingw dir> build-mingw.sh [WORK_DIR]
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${1:-$HERE/../work}"
WORK="$(cd "$WORK" && pwd)"
: "${LLVM_MINGW_ROOT:?set LLVM_MINGW_ROOT to the llvm-mingw directory}"
export LLVM_MINGW_ROOT
BUILD="$WORK/PS2Recomp/out/mingw"

LAUNCHER="/usr/bin/env;CCACHE_SLOPPINESS=pch_defines,time_macros,include_file_mtime,include_file_ctime;CCACHE_MAXSIZE=10G;ccache"
cmake -S "$WORK/PS2Recomp" -B "$BUILD" -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_TOOLCHAIN_FILE="$HERE/llvm-mingw-toolchain.cmake" \
  "-DCMAKE_C_COMPILER_LAUNCHER=$LAUNCHER" "-DCMAKE_CXX_COMPILER_LAUNCHER=$LAUNCHER" \
  "-DCMAKE_CXX_FLAGS=-msse4.1 -Xclang -fno-pch-timestamp" \
  -DPS2X_BUILD_RECOMP=OFF -DPS2X_BUILD_ANALYZER=OFF -DPS2X_BUILD_STUDIO=OFF -DPS2X_BUILD_TEST=OFF \
  -DPS2X_ENABLE_FFMPEG=OFF -DPS2X_ENABLE_DEBUG_UI=OFF -DPS2X_ENABLE_LTO=OFF \
  -DPS2X_ENABLE_AGRESSIVE_LOGS=OFF -DPS2X_ENABLE_RUNTIME_LOGS=OFF -DPS2X_ENABLE_IOP_RPC_TRACE=ON \
  -DFETCHCONTENT_SOURCE_DIR_NLOHMANN_JSON="$WORK/deps/nlohmann_json" \
  -DFETCHCONTENT_SOURCE_DIR_TOML11="$WORK/deps/toml11" \
  -DFETCHCONTENT_SOURCE_DIR_FMT="$WORK/deps/fmt" \
  -DFETCHCONTENT_SOURCE_DIR_RABBITIZER="$WORK/deps/rabbitizer" \
  -DFETCHCONTENT_SOURCE_DIR_RAYLIB="$WORK/deps/raylib" \
  -DPS2X_PARALLEL_GS_DIR="$WORK/deps/parallel-gs"
cmake --build "$BUILD" --target ps2EntryRunner -- -k 0
