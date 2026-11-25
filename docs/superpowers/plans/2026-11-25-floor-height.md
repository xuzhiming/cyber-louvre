# 层高与门高 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Raise every structural storey by 2 m and every real door by 1 m, keeping the 1/6 m stair riser by adding flights inside the existing outer footprint.

**Architecture:** `src/spec.py` owns floors, doors, and stair polygons. Walls, slabs, windows, roofs, and art slots are regenerated from those datums. The web viewer stores the few absolute heights that are not in the glTF. A pure-Python test locks riser, door, and lintel rules before Blender checks the mesh.

**Tech Stack:** Python 3, Blender bpy, Three.js page in `src/web_template.html`, gltf-transform, Playwright.

## Global Constraints

- 1F floor stays z=0. New floors: B1=-8, L2=10, L3=20, L4=30, band top=40. Dome spring 40, glass apex 53.
- Door width unchanged. Door height +1 m except pyramid glass doors (4.5 and 2.8 stay).
- Stair riser stays 1/6 m, tread 0.30 m, ≤18 risers per flight. Do not relax `RISER_MAX` or stair-rule R4.
- Outer mass rectangles stay. Artwork frame 2.0×1.5 m and hang height 1.6 m above the local floor stay.
- Windows keep `z1 = storey_top - 1`.
- L4 shaft wall height becomes 4.0 m so the 3.4 m door has a 0.6 m lintel.
- Do not deploy. Do not print or edit credentials.

---

### Task 1: Failing datum test

**Files:**
- Create: `src/test_floor_height.py`
- Test: `src/test_floor_height.py`

**Interfaces:**
- Consumes: `spec.build()`, `spec.LEVELS`, `spec.BAND_Z`, `spec.DOORS`, `spec.STAIRS`, `spec.SPACES`, `spec.DOME`, `spec.MASSES`
- Produces: `python3 src/test_floor_height.py` exits 0 only when the approved datums and stair rules hold

- [ ] **Step 1: Write the failing test**

Assert the floor table, dome spring, mass tops, door heights, 1/6 m risers, flight limits, and L4 shaft lintel. Run `python3 src/test_floor_height.py` and confirm it fails on the current 6 m / 8 m model.

- [ ] **Step 2: Implement `src/spec.py`**

Set `LEVELS` / `BAND_Z`, default room heights (10 / 8 / 5), mass tops, dome `z0=40`, lobby and atrium `h=40`, elevator `h=10`. Add 1 m to every non-pyramid door. Rebuild stairs as specified in the spec. Move each pavilion shaft south wall to y=42.8 in template coordinates and set the L4 shaft `h=4.0` with its floor covering the arrival zone.

- [ ] **Step 3: Re-run the test**

`python3 src/test_floor_height.py` exits 0.

### Task 2: Mesh, lights, viewer, paths

**Files:**
- Modify: `src/arch.py`, `src/exterior.py`, `src/props.py`, `src/verify.py`, `src/make_preview.py`, `src/circulation.py`, `src/web_template.html`, `src/rebuild_web.sh`, `src/export_glb.py`, and the `src/*` scripts whose root is hardcoded to `/workspace/outputs/cyber_louvre`

**Interfaces:**
- Consumes: `LEVELS`, `BAND_Z`, `SLAB`, door height
- Produces: geometry whose absolute z follows the new datums; `bash src/rebuild_web.sh` runs from this repo

- [ ] **Step 1: Replace hardcoded storey lists** with `LEVELS` in `arch.py`, `verify.py`, `make_preview.py`.
- [ ] **Step 2: Translate roofs** rigidly: wing/pavilion eave = `LEVELS['L4']` (30) with the old offsets; center/dome/gable/turrets = band top 40. Keep neon material names. Lengthen the portico only up to the new entablature. Tie the ground pad top to `LEVELS['B1'] - SLAB`. Move the hologram rings with L2/L3. Facade band test uses `LEVELS['L4']`, not the literal 24.
- [ ] **Step 3: Update the viewer** floor labels, cut planes (9.5 / 19.5 / 29.5), spawns, minimap threshold, and fill lights. Leave the 1.6 m artwork focus math and the pale-yellow roof materials.
- [ ] **Step 4: Point scripts at the repo root** via `dirname`.

### Task 3: Blender verify, routes, walk, PR

- [ ] **Step 1:** `blender --background --python src/verify.py`. Doors, stairs, windows, slots, and stair rules must pass. Fix geometry if a real clearance fails. Do not widen the riser band to force a pass.
- [ ] **Step 2:** `bash src/rebuild_web.sh`.
- [ ] **Step 3:** Regenerate `src/test_route*.json` from the new mesh. Run the existing walk scripts. A stuck old last waypoint is a failure to report, not a test to delete.
- [ ] **Step 4:** Save stair, door, and exterior screenshots. Commit on `cursor/floor-height-dee9` and open the PR. Do not push `main`.

## Self-review

- Spec floors, doors, dome, windows, art, and stair table each have a task.
- L4 lintel and the 1/6 m riser are tests, not comments.
- No placeholder steps. Path fixes stay inside the scripts this build runs, plus the other copies of the same dead root so those scripts can be launched from this checkout.
