import sys, os, math, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import bpy
import spec, arch, exterior, props, art
from geom import Acc
import mats

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')

def make_acc(xclip=None):
    acc = Acc(); acc.xclip = xclip
    arch.build_arch(acc)
    exterior.build_exterior(acc)
    props.props(acc)
    art.build_frames(acc, write=xclip is None)
    return acc

def to_blender(acc):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mat_cache = {}
    def getmat(n):
        if n not in mat_cache: mat_cache[n] = mats.make_material(n)
        return mat_cache[n]
    objs = {}
    for gname, gm in acc.g.items():
        verts, faces, midx, mlist = [], [], [], list(gm.keys())
        for mi, mname in enumerate(mlist):
            v, f = gm[mname]
            o = len(verts); verts.extend(v)
            faces.extend([tuple(i + o for i in q) for q in f]); midx.extend([mi] * len(f))
        mesh = bpy.data.meshes.new(gname)
        mesh.from_pydata(verts, [], faces)
        mesh.update()
        for mn in mlist: mesh.materials.append(getmat(mn))
        mesh.polygons.foreach_set('material_index', midx)
        # UVs (world projected, per material scale)
        V = np.array(verts, dtype=np.float32)
        uvl = mesh.uv_layers.new(name='UVMap')
        uvs = np.zeros((len(mesh.loops), 2), dtype=np.float32)
        for p in mesh.polygons:
            idx = list(p.vertices)
            pts = V[idx]
            n = np.abs(np.array(p.normal))
            ax = int(np.argmax(n))
            sc = mats.MATS[mlist[midx[p.index]]][6]
            if ax == 0: uv = pts[:, [1, 2]]
            elif ax == 1: uv = pts[:, [0, 2]]
            else: uv = pts[:, [0, 1]]
            if mlist[midx[p.index]].startswith('screen'):
                # map to 0..1 over the quad bbox
                mn_, mx_ = uv.min(0), uv.max(0)
                uv = (uv - mn_) / np.maximum(mx_ - mn_, 1e-6)
                if ax == 0 and False: pass
                uvs[p.loop_start:p.loop_start + p.loop_total] = uv
                continue
            uvs[p.loop_start:p.loop_start + p.loop_total] = uv / sc
        uvl.data.foreach_set('uv', uvs.ravel())
        ob = bpy.data.objects.new(gname, mesh)
        bpy.context.scene.collection.objects.link(ob)
        objs[gname] = ob
    return objs

if __name__ == '__main__':
    t0 = time.time()
    section = '--section' in sys.argv
    acc = make_acc((-18.0, 0.0) if section else None)
    print('tris', acc.stats(), acc.tri_by_group())
    objs = to_blender(acc)
    # screen UV fix: oriented per face; fine
    if section:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'model_section.blend')); sys.exit(0)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'model.blend'))
    json.dump(dict(tris=acc.stats(), by_group=acc.tri_by_group()), open(os.path.join(OUT, 'tri_stats.json'), 'w'), indent=1)
    print('built in', time.time() - t0)
