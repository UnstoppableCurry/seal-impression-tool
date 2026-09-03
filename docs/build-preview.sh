#!/usr/bin/env bash
# Assemble docs/site for local preview (mirrors CI build)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${ROOT}/_site"
rm -rf "$OUT"
mkdir -p "$OUT/assets/screenshots"
cp -r "${ROOT}/docs/site/"* "$OUT/"
cp "${ROOT}/docs/demo_document.png" "$OUT/assets/"
cp "${ROOT}/docs/screenshots/"*.png "$OUT/assets/screenshots/"
echo "Built preview at ${OUT}"
echo "Run: python3 -m http.server 8765 --directory ${OUT}"
