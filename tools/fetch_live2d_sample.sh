#!/usr/bin/env bash
# Download one of Live2D's official free sample models for local / CI testing.
#
# The samples in Live2D/CubismWebSamples are provided under the
# "Live2D Free Material License Agreement":
#   https://www.live2d.com/eula/live2d-free-material-license-agreement_en.html
# They are downloaded at test time only and must NOT be committed to this
# repository (the default target .local-test-models/ is git-ignored).
#
# Usage: tools/fetch_live2d_sample.sh [Mark|Hiyori|Haru|...] [target-dir]
# Prints the path of the downloaded *.model3.json on the last line.
set -euo pipefail

MODEL="${1:-Mark}"
TARGET="${2:-.local-test-models/live2d-samples}"
REPO="https://github.com/Live2D/CubismWebSamples.git"
COMMIT="b1de66b0b1f1cb881d95fb6158622aeb6a2827bd"  # pinned for reproducible tests

if [[ ! "$MODEL" =~ ^[A-Za-z0-9_-]+$ ]]; then
  echo "invalid model name: $MODEL" >&2
  exit 2
fi

DEST="$TARGET/$MODEL"
if [[ ! -f "$DEST/$MODEL.model3.json" ]]; then
  WORK="$(mktemp -d)"
  trap 'rm -rf "$WORK"' EXIT
  git clone --quiet --filter=blob:none --no-checkout --sparse "$REPO" "$WORK/cws"
  git -C "$WORK/cws" sparse-checkout set "Samples/Resources/$MODEL"
  git -C "$WORK/cws" -c advice.detachedHead=false checkout --quiet "$COMMIT"
  mkdir -p "$TARGET"
  rm -rf "$DEST"
  mv "$WORK/cws/Samples/Resources/$MODEL" "$DEST"
  cat > "$TARGET/README.txt" <<'TXT'
These Live2D sample models come from https://github.com/Live2D/CubismWebSamples
and are licensed under the Live2D Free Material License Agreement.
They are for local testing only. Do not commit or redistribute them with AmakanoPet.
TXT
fi
echo "$(cd "$DEST" && pwd)/$MODEL.model3.json"
