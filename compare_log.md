# Compare log – Cyber Louvre (silhouette IoU vs. design sheet)

Method: the sheet's elevation / roof-plan panels are segmented into a mask and calibrated to metres with the panel's own dimension lines
(x: 180 m / 120 m span, z: 46 m arrow). The model is rendered with orthographic cameras and a white-emission override (mask), cropped at z>=0, and scored on a 6 px/m grid.
`iou_all` = whole silhouette (building + pyramids + court); `iou_bldg` = building span only (ignores pyramids that the sheet draws at both ends of the side views);
`top_err` = mean absolute error of the upper silhouette edge in metres. Side-by-side + overlay sheets: `compare/compare_<view>_<round>.png`.

| round | front all/bldg (top err m) | back | left | right | top (court+footprint) | change made before the next round |
|---|---|---|---|---|---|---|
| r1 | 0.867 / 0.869 (5.21) | 0.853 / 0.856 (5.56) | 0.839 / 0.925 (2.94) | 0.840 / 0.922 (3.06) | 0.926 | baseline. Found: corner-pavilion mansard too low, wing roof ridge too low, ground box leaked B1 into the mask |
| r2 | 0.892 / 0.896 (3.93) | 0.909 / 0.914 (3.08) | 0.853 / 0.942 (2.23) | 0.854 / 0.939 (2.34) | 0.926 | pavilion mansards taller/steeper, central pavilion & dome position/height tuned, mask cropped to z>=0 |
| r3 | 0.895 / 0.899 (3.83) | 0.929 / 0.933 (2.33) | 0.847 / 0.935 (2.51) | 0.848 / 0.931 (2.65) | 0.926 | north-wing roof / bump (h=24) heights, pyramid footprint/height to 36 m x 21 m |
| r4 | 0.899 / 0.903 (3.69) | 0.930 / 0.935 (2.29) | 0.851 / 0.938 (2.39) | 0.849 / 0.931 (2.65) | 0.928 | dome base ring + spire, minor roof edges; lighting/emission toned down (beauty look) |
| r5 (final) | 0.899 / 0.903 (3.69) | 0.930 / 0.935 (2.29) | 0.851 / 0.938 (2.39) | 0.849 / 0.931 (2.65) | 0.928 (strict footprint-only 0.619) | drum roof opened under the dome so the atrium looks up into it (silhouette unchanged) |
| r6/r7 (door round) | 0.899 / 0.903 (3.69) | 0.930 / 0.935 (2.29) | 0.851 / 0.938 (2.39) | 0.849 / 0.931 (2.65) | 0.928 (strict 0.620) | pyramid entrances cleaned + auto doors, B1 earth block hollowed, B1 light fixtures re-laid, lobby door cleared: silhouette unchanged |

Residual differences (not closed because the sheet is internally inconsistent or would break the circulation spec):
* Sheet side views show pyramids at both ends; the plan/front show them only on the south side -> model follows plan/front (hence `iou_all` < `iou_bldg` on left/right).
* Sheet wing roof reads ~7 m tall in the silhouette vs 12 m in the dimension table -> model follows the dimension table.
* Sheet section puts the dome over the middle of the 120 m depth; the plan puts it north -> model follows the plan.
* Strict top-view footprint IoU is low (0.62) because the sheet's roof-plan colouring blends courtyard/ground into the building; with the courtyard counted it is 0.93.
| r8 (stair round) | 0.899 / 0.903 (3.69) | 0.930 / 0.935 (2.29) | 0.851 / 0.938 (2.39) | 0.849 / 0.931 (2.65) | 0.928 (strict 0.620) | stairs redesigned (interior only) - silhouettes unchanged |
| r9 (top-stair roof fix) | 0.899 / 0.903 (3.69) | 0.930 / 0.935 (2.29) | 0.851 / 0.938 (2.39) | 0.849 / 0.931 (2.65) | 0.928 (strict 0.620) | corner mansards hollowed underneath; silhouettes unchanged |
r10 (grey roofs + glass windows): front 0.899 back 0.930 left 0.851 right 0.849 top 0.928 (unchanged vs r9)
r11 (lavender walls + dark day glass): IoU unchanged (0.899/0.930/0.851/0.849/0.928)
r12 (exterior walls #3A3F4B): IoU unchanged
r13 (dark slate roofs #2A2E37): IoU unchanged
r14 (hollow dormers + gable window opening; blocked facade windows dropped): IoU front .899 back .930 left .851 right .849 top .928 (unchanged)
- r16 (windows simplified: one centred floor-to-ceiling window per room, halls every 2nd/3rd bay symmetric; 746 -> 270 facade windows): IoU 0.899 / 0.930 / 0.851 / 0.849 / 0.928 (unchanged); windows 270/270, panes 371/371, doors 146/146, stairs 20/20, walk 164/164 x3
- r17 (open rooms: 72 small-gallery door walls removed, partitions kept): IoU 0.899 / 0.930 / 0.851 / 0.849 / 0.928 (unchanged); doors 74/74 (was 146), open-room remnant check 72/72, windows 270/270, panes 371/371, walk 164/164 x3
- r18 (exterior walls #696A71, roofs #4C4D52, copings #5D5E65): IoU unchanged
- r19 (art walls: 288 display slots 2.0x1.5 m, floor exhibits removed): IoU unchanged; slots 288/288, floor_props ok, doors 74/74, walk 164/164 x3
