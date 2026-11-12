#!/bin/bash
cd /workspace/outputs/cyber_louvre/src
./loop.sh r7 0.5 > ../compare/loop_r7.log 2>&1
python3 render.py --views door_main,pyr_main_door,pyr_sl_door,pyr_sr_door,b1_stairmouth,b1_corridor,b1_hall_stairs,hero,hero2 --tag final --samples 64 --scale 1.0 > ../renders/final2_render.log 2>&1
echo ALLDONE >> ../renders/final2_render.log
