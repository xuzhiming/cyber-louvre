#!/bin/bash
# model.blend -> model.glb -> web/model_web.glb (meshopt + webp 1024) -> web/preview.html
cd /workspace/outputs/cyber_louvre/src
python3 export_glb.py 2>&1 | tail -1
G="npx --yes @gltf-transform/cli"
cd ..
$G dedup model.glb /tmp/a.glb >/dev/null 2>&1 && $G resize /tmp/a.glb /tmp/b.glb --width 1024 --height 1024 >/dev/null 2>&1 && $G webp /tmp/b.glb /tmp/c.glb >/dev/null 2>&1 && $G meshopt /tmp/c.glb web/model_web.glb --level medium 2>&1 | tail -1
python3 src/make_preview.py
