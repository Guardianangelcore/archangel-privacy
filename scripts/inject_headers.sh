#!/usr/bin/env bash
# Inject Guardian Angel copyright headers into every source file (idempotent).
set -e

PY_HEADER='# Copyright © 2026 Guardian Angel. All Rights Reserved.
# This source code and its logic are the sole property of Guardian Angel.
# Unauthorized duplication, modification, or distribution is strictly prohibited.'

TS_HEADER='/* Copyright © 2026 Guardian Angel. All Rights Reserved. This source code and its logic are the sole property of Guardian Angel. Unauthorized duplication, modification, or distribution is strictly prohibited. */'

MARK='Copyright © 2026 Guardian Angel'
count=0

while IFS= read -r f; do
  if head -3 "$f" | grep -q "$MARK"; then continue; fi
  case "$f" in
    *.py)
      printf '%s\n' "$PY_HEADER" | cat - "$f" > "$f.tmp" && mv "$f.tmp" "$f" ;;
    *.ts|*.tsx|*.js)
      printf '%s\n' "$TS_HEADER" | cat - "$f" > "$f.tmp" && mv "$f.tmp" "$f" ;;
  esac
  count=$((count+1))
done < <(find /app/backend /app/frontend/app /app/frontend/src -type f \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" \) -not -path "*/node_modules/*" -not -path "*/.expo/*" -not -path "*/__pycache__/*")

echo "Headers injected into $count files"
