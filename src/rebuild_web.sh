#!/bin/bash
# spec -> model.blend -> model.glb -> web/model_web.glb (meshopt + webp 1024) -> web/preview.html
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
blender --background --python src/build.py
blender --background --python src/export_glb.py
G="npx --yes @gltf-transform/cli"
$G dedup model.glb /tmp/a.glb
$G resize /tmp/a.glb /tmp/b.glb --width 1024 --height 1024
$G webp /tmp/b.glb /tmp/c.glb
$G meshopt /tmp/c.glb web/model_web.glb --level medium
python3 src/make_preview.py
