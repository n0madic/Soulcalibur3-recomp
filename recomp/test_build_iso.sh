#!/usr/bin/env bash
# Tests how build.sh finds the disc image. It runs a copy of build.sh in a temporary tree with fake `7z`
# and `git` commands, so nothing is extracted, cloned or built; the script stops at its first `git` call.
# Usage: ./recomp/test_build_iso.sh
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT

mkdir -p "$T/repo/recomp" "$T/bin" "$T/elsewhere"
cp "$HERE/build.sh" "$HERE/PS2Recomp.commit" "$T/repo/recomp/"

# 7z records the image it was given and, with FAKE_ELF=1, "extracts" the boot ELF.
cat >"$T/bin/7z" <<'EOF'
#!/bin/sh
for arg in "$@"; do
  case "$arg" in -o*) out="${arg#-o}" ;; esac
  image="$arg"
done
printf '%s' "$image" >"$FAKE_LOG"
[ "${FAKE_ELF:-}" = 1 ] && : >"$out/SCES_533.12"
exit 0
EOF
cat >"$T/bin/git" <<'EOF'
#!/bin/sh
echo REACHED_CLONE
exit 99
EOF
chmod +x "$T/bin/7z" "$T/bin/git"

failures=0
# run <name> <expected exit> <expected output fragment> [VAR=value ...]: runs build.sh from $RUNDIR
# (default: the repository), the way a user would start it.
RUNDIR="$T/repo"
run() {
  local name="$1" status="$2" fragment="$3" output code
  shift 3
  rm -rf "$T/work"
  [ -n "${PREPARE:-}" ] && eval "$PREPARE"
  output="$(cd "$RUNDIR" && env -u ISO PATH="$T/bin:$PATH" FAKE_LOG="$T/7z.image" "$@" "$T/repo/recomp/build.sh" "$T/work" 2>&1)"
  code=$?
  if [ "$code" = "$status" ] && printf '%s' "$output" | grep -qF -- "$fragment"; then
    echo "ok   $name"
  else
    echo "FAIL $name: exit $code (wanted $status), wanted output containing: $fragment"
    printf '%s\n' "$output" | sed 's/^/       /'
    failures=$((failures + 1))
  fi
}
image_used() { cat "$T/7z.image" 2>/dev/null; }
check_image() {
  if [ "$(image_used)" = "$2" ]; then echo "ok   $1"; else echo "FAIL $1: 7z got '$(image_used)', wanted '$2'"; failures=$((failures + 1)); fi
}

# No image anywhere.
run "no image in the root" 1 "No disc image found"

# One image under an arbitrary name, with spaces, brackets and a capital extension.
touch "$T/repo/My Disc (v1.2) [PAL].ISO"
run "any single image is used" 99 "REACHED_CLONE" FAKE_ELF=1
check_image "  the image it found" "$T/repo/My Disc (v1.2) [PAL].ISO"

# Two images are ambiguous; ISO= settles it, also as a relative path.
touch "$T/repo/other.iso"
run "two images are ambiguous" 1 "More than one .iso" FAKE_ELF=1
run "ISO= overrides the search" 99 "REACHED_CLONE" FAKE_ELF=1 ISO="$T/repo/other.iso"
check_image "  the image it was given" "$T/repo/other.iso"
touch "$T/elsewhere/disc.iso"
RUNDIR="$T/elsewhere" run "a relative ISO= becomes absolute" 99 "REACHED_CLONE" FAKE_ELF=1 ISO=disc.iso
check_image "  absolute path" "$T/elsewhere/disc.iso"

# Errors.
run "ISO= names a missing file" 1 "Disc image not found" FAKE_ELF=1 ISO="$T/nowhere.iso"
run "an image without the boot ELF" 1 "has no SCES_533.12" ISO="$T/repo/other.iso"

# An extracted disc needs no image at all.
rm -f "$T/repo/"*.iso "$T/repo/"*.ISO
PREPARE='mkdir -p "$T/work/game" && : >"$T/work/game/SCES_533.12"' run "an extracted disc needs no image" 99 "REACHED_CLONE"

if [ "$failures" = 0 ]; then echo "all passed"; else echo "$failures failed"; exit 1; fi
