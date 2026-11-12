#!/bin/bash
cd /workspace/outputs/cyber_louvre/src
./loop.sh r5 0.5 > ../compare/loop_r5.log 2>&1
python3 render.py --views hero,hero2,front,back,left,right,top,section,atrium,hall,stairs,gallery,cutaway --tag final --samples 96 --scale 1.0 > ../renders/final_render.log 2>&1
echo ALLDONE >> ../renders/final_render.log
