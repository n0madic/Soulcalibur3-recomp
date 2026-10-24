#!/usr/bin/env bash
# Imports the game ELF into Ghidra (headless) with the PS2 Emotion Engine extension and exports the
# function/label map that PS2Recomp consumes as `ghidra_output` (see build.sh).
#
# Prerequisites: `brew install ghidra`, `gh` (GitHub CLI), and the extracted disc in $WORK/game
# (run build.sh once, or extract the ISO yourself).
# Usage: ./recomp/ghidra_export.sh [WORK_DIR]   (default: ./recomp/work)
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${1:-$HERE/work}"
ELF="$WORK/game/SCES_533.12"
GHIDRA="$(brew --prefix ghidra)/libexec"
export JAVA_HOME="${JAVA_HOME:-$(brew --prefix openjdk@21)/libexec/openjdk.jdk/Contents/Home}"
EXT_REPO="chaoticgd/ghidra-emotionengine-reloaded"

[ -f "$ELF" ] || { echo "Missing $ELF (extract the disc first: make build)"; exit 1; }

# 1. EE language extension (matching the installed Ghidra version).
GVER="$(basename "$(readlink -f "$(brew --prefix ghidra)")")"            # e.g. 12.1.4
EXT_DIR="$HOME/Library/ghidra/ghidra_${GVER}_PUBLIC/Extensions"
if [ ! -d "$EXT_DIR/ghidra-emotionengine-reloaded" ]; then
  mkdir -p "$WORK/ghidra-ext" "$EXT_DIR"
  gh release download --repo "$EXT_REPO" --dir "$WORK/ghidra-ext" --clobber \
    --pattern "ghidra_${GVER}_PUBLIC_*_ghidra-emotionengine-reloaded.zip"
  unzip -q -o "$WORK"/ghidra-ext/ghidra_"${GVER}"_PUBLIC_*_ghidra-emotionengine-reloaded.zip -d "$EXT_DIR"
fi

# 2. Import + auto-analysis (about 2 minutes).
mkdir -p "$WORK/ghidra-proj"
if [ ! -f "$WORK/ghidra-proj/sc3.gpr" ]; then
  "$GHIDRA/support/analyzeHeadless" "$WORK/ghidra-proj" sc3 -import "$ELF" \
    -processor "r5900:LE:32:default" -overwrite -max-cpu 8
fi

# 3. Export the function map. The upstream script asks for two output files; in headless mode they
#    are passed as positional script arguments (TOML first, CSV second).
mkdir -p "$WORK/ghidra-export"
cp "$WORK/PS2Recomp/ps2xRecomp/tools/ghidra/ExportPS2Functions.java" "$WORK/ghidra-export/"
"$GHIDRA/support/analyzeHeadless" "$WORK/ghidra-proj" sc3 -process SCES_533.12 -noanalysis \
  -scriptPath "$WORK/ghidra-export" \
  -postScript ExportPS2Functions.java "$WORK/ghidra-export/sc3_ghidra.toml" "$WORK/ghidra-export/sc3_functions.csv"

echo "Wrote $WORK/ghidra-export/sc3_functions.csv"
