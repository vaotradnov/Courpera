#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

OUT="${1:-submission.zip}"

INCLUDE=(
  accounts activity api assignments config courses discussions materials messaging static templates ui \
  manage.py mypy.ini pytest.ini README.md requirements.txt runtime.txt SECURITY.md Procfile .pre-commit-config.yaml bandit.yaml
)
EXCLUDE=(.venv htmlcov __pycache__ .pytest_cache .mypy_cache .ruff_cache media)

TMP=$(mktemp -d)
for p in "${INCLUDE[@]}"; do
  cp -R "$p" "$TMP/$p"
done
for p in "${EXCLUDE[@]}"; do
  rm -rf "$TMP/$p" 2>/dev/null || true
done

rm -f "$OUT"
cd "$TMP"
zip -r "$OLDPWD/$OUT" . >/dev/null
cd "$OLDPWD"
rm -rf "$TMP"
echo "Wrote $OUT"
