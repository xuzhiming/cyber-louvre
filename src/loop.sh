#!/bin/bash
# usage: loop.sh TAG   -> rebuild, render masks + beauty elevations (half scale), compare
cd /workspace/outputs/cyber_louvre/src
TAG=$1; SC=${2:-0.5}
python3 build.py 2>&1 | grep -E "^tris|rror"
python3 render.py --views front_mask,back_mask,left_mask,right_mask,top_mask,front,back,left,right,top --tag $TAG --samples 24 --scale $SC 2>&1 | grep -E "rror"
python3 compare.py $TAG
