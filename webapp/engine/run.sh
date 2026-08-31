#!/bin/bash
# Render one LSe 314 generator headless, straight out of the repo's own
# abstractions. No re-implementation: this drives Kacper's patches with
# `pd -nogui -noaudio` and captures the result through writesf~.
#
#   ./run.sh <name> <fast-forward ms>      e.g. ./run.sh bp 12400
#
# Paths are derived from this script's location, so a fresh clone works.
set -u
ENG="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$ENG/../.." && pwd)"
LSE="$ROOT/software/pure data/rpi4_blockas_OS/lse314"
[ -d "$LSE" ] || { echo "patch tree not found: $LSE" >&2; exit 1; }
NAME=$1; FF=$2
cd "$ENG"
timeout 300 pd -nogui -noaudio -r 44100 \
  -path "$LSE/01_AUDIO" -path "$LSE/04_OTHER_subpatches_utilities" \
  -path "$LSE/02_INPUT_Serduino_LDR_etc" -path "$LSE" \
  -lib iemlib -lib cyclone \
  -send "pd dsp 1" -send "pd fast-forward $FF" "r_$NAME.pd" 2>&1 |
  grep -viE "priority|iemlib|musil|cyclone|^::|^---|^$" | head -25
