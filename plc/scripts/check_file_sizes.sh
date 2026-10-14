#!/usr/bin/env bash
# NFR-08 / l1-plc.md: no source file over 300 lines (generated files included).
set -euo pipefail
cd "$(dirname "$0")/.."
fail=0
while IFS= read -r f; do
  n=$(wc -l < "$f")
  if [ "$n" -gt 300 ]; then
    echo "too long: $f ($n lines, limit 300)"
    fail=1
  fi
done < <(find src scripts -type f \( -name '*.st' -o -name '*.py' -o -name '*.sh' \))
[ "$fail" -eq 0 ] && echo "file sizes ok"
exit "$fail"
