#!/usr/bin/env bash
# Concatenates plc/src into one ST file, because OpenPLC Runtime takes a single file (risk R4).
# Order: types → functions → function blocks → programs → CONFIGURATION (globals + task).
# Usage: plc/scripts/build.sh [output]        (default plc/build/line1.st)
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="${1:-build/line1.st}"
TASK_INTERVAL="${PLC_TASK_INTERVAL:-T#50ms}"
mkdir -p "$(dirname "$OUT")"

POUS=(
  src/generated/types/Contract_Enums.st
  src/types/*.st
  src/generated/types/Contract_Structs.st
  src/packml/PackMLHasStarted.st
  src/time/*.st
  src/packml/FB_*.st
  src/alarms/*.st
  src/generated/alarms/*.st
  src/process/*.st
  src/machines/*.st
  src/recipe/*.st
  src/generated/io/*.st
  src/generated/bridge/*.st
  src/PRG_Main.st
)

{
  echo "(* Line 1 PLC program. Built by plc/scripts/build.sh from plc/src. Do not edit. *)"
  for f in "${POUS[@]}"; do
    printf '\n(* ===== %s ===== *)\n' "$f"
    cat "$f"
  done
  printf '\nCONFIGURATION Config0\n'
  for f in src/generated/gvl/*.st; do
    grep -v '^(\*' "$f"
  done
  printf '  RESOURCE Res0 ON PLC\n'
  printf '    TASK MainTask(INTERVAL := %s, PRIORITY := 0);\n' "$TASK_INTERVAL"
  # Programs run in this order each scan: I/O and bridge images first, then the logic.
  for f in "${POUS[@]}"; do
    sed -n 's/^PROGRAM \([A-Za-z0-9_]*\).*/    PROGRAM \1_Inst WITH MainTask : \1;/p' "$f"
  done
  printf '  END_RESOURCE\nEND_CONFIGURATION\n'
} > "$OUT"
echo "built $OUT ($(wc -l < "$OUT") lines, $(grep -c '^PROGRAM ' "$OUT") programs)"
