import sys, os, math, argparse, time
import bpy
from mathutils import Vector, Euler
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')

ORTHO = {   # name: (location, rotation_deg, ortho_scale, res)
    'front': ((0, -400, 21), (90, 0, 0), 200, (2000, 560)),
    'back':  ((0, 400, 21), (90, 0, 180), 200, (2000, 560)),
    'left':  ((-400, 0, 21), (90, 0, -90), 150, (1500, 560)),
    'right': ((400, 0, 21), (90, 0, 90), 150, (1500, 560)),
    'top':   ((0, 0, 300), (0, 0, 0), 200, (2000, 1333)),
}


CLOSEUPS = {
    'door_main': ((0, -9.5, 1.7), (0, 8, 2.4), 24, [('POINT', (0, 3, 3.5), 3000, (1.0, 0.8, 0.6), 1.5), ('POINT', (0, 18, 4), 20000, (1.0, 0.8, 0.6), 2)], 'door_main'),
    'door_main_open': ((0, -9.5, 1.7), (0, 8, 2.4), 24, [('POINT', (0, 3, 3.5), 3000, (1.0, 0.8, 0.6), 1.5), ('POINT', (0, 18, 4), 20000, (1.0, 0.8, 0.6), 2)], 'door_main_open'),
    'pyr_main_door': ((0, -76, 1.7), (0, -66, 2.0), 30, [('POINT', (0, -60, 3.5), 4000, (0.6, 0.8, 1.0), 2)], 'pyramid_main_entrance'),
    'pyr_sl_door': ((-37, -64, 1.7), (-37, -58, 1.5), 30, [('POINT', (-37, -54, 2.5), 2000, (0.6, 0.8, 1.0), 2)], 'pyramid_smallL_entrance'),
    'pyr_sr_door': ((37, -64, 1.7), (37, -58, 1.5), 30, [('POINT', (37, -54, 2.5), 2000, (0.6, 0.8, 1.0), 2)], 'pyramid_smallR_entrance'),
    'b1_corridor': ((0, -34, 1.6 - 6), (0, 20, 1.2 - 6), 20, [('POINT', (0, -10, -1.2), 600, (1.0, 0.85, 0.65), 0.5), ('POINT', (0, 8, -1.2), 600, (1.0, 0.85, 0.65), 0.5)], 'b1_corridor'),
    'b1_stairmouth': ((0, 2, 1.6 - 6), (0, 20, 1.3 - 6), 20, [('POINT', (0, 8, -1.2), 600, (1.0, 0.85, 0.65), 0.5), ('POINT', (0, 18, -1.5), 300, (1.0, 0.85, 0.65), 0.5)], 'b1_stairmouth'),
    'b1_hall_stairs': ((12, -56, 1.6 - 6), (0, -42, 1.0 - 6), 22, [('POINT', (6, -48, -1.2), 600, (1.0, 0.85, 0.65), 0.5), ('POINT', (-8, -48, -1.2), 600, (1.0, 0.85, 0.65), 0.5)], 'b1_hall_stairs'),
}

def setup_scene(samples=48, res=(1600, 900), transparent=False, denoise=True):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = denoise
    sc.cycles.max_bounces = 6
    sc.cycles.transparent_max_bounces = 12
    sc.cycles.volume_bounces = 0
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.view_settings.view_transform = 'Standard' if transparent else 'Filmic' if False else 'AgX'
    try: sc.view_settings.look = 'None'
    except Exception: pass
    sc.render.image_settings.file_format = 'PNG'
    sc.render.threads = 8
    return sc

def make_world(sc, top=(0.0012, 0.0025, 0.010), horizon=(0.004, 0.006, 0.018)):
    w = bpy.data.worlds.new('night'); w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld'); bg = nt.nodes.new('ShaderNodeBackground')
    tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.35; ramp.color_ramp.elements[0].color = (*horizon, 1)
    ramp.color_ramp.elements[1].position = 0.8; ramp.color_ramp.elements[1].color = (*top, 1)
    nt.links.new(tc.outputs['Generated'], sep.inputs['Vector'])
    nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
    nt.links.new(bg.outputs['Background'], out.inputs['Surface'])
    bg.inputs['Strength'].default_value = 1.0
    sc.world = w

def add_light(kind, loc, energy, color, size=5, rot=None, spot=None):
    ld = bpy.data.lights.new(kind, kind)
    ld.energy = energy; ld.color = color
    if kind == 'AREA': ld.size = size
    if kind == 'POINT': ld.shadow_soft_size = size
    if kind == 'SUN': ld.angle = math.radians(3)
    ob = bpy.data.objects.new(kind, ld); ob.location = loc
    if rot: ob.rotation_euler = Euler([math.radians(a) for a in rot])
    bpy.context.scene.collection.objects.link(ob)
    return ob

def night_lights():
    add_light('SUN', (0, 0, 100), 0.18, (0.45, 0.55, 1.0), rot=(55, 0, 35))
    for (x, y, c) in [(-37, -52, (0.7, 0.3, 1.0)), (37, -52, (0.7, 0.3, 1.0)), (0, -48, (0.3, 0.7, 1.0))]:
        add_light('POINT', (x, y, 6), 6000, c, size=3)
    for (x, y) in [(-30, -10), (30, -10), (0, 20)]:
        add_light('POINT', (x, y, 4), 8000, (1.0, 0.7, 0.4), size=3)
    for (x, y) in [(-67, -110), (67, -110), (0, -100)]:
        add_light('AREA', (x, y, 18), 25000, (1.0, 0.65, 0.4), size=30, rot=(80, 0, 0))

def camera(loc, rot=None, target=None, ortho=None, lens=35):
    cd = bpy.data.cameras.new('cam'); cob = bpy.data.objects.new('cam', cd)
    bpy.context.scene.collection.objects.link(cob)
    cob.location = loc
    if ortho:
        cd.type = 'ORTHO'; cd.ortho_scale = ortho
    else:
        cd.lens = lens
    cd.clip_start = 0.1; cd.clip_end = 2000
    if target is not None:
        d = Vector(target) - Vector(loc)
        cob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    else:
        cob.rotation_euler = Euler([math.radians(a) for a in rot])
    bpy.context.scene.camera = cob
    return cob

def render_to(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

def mask_material():
    m = bpy.data.materials.new('mask'); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    em = nt.nodes.new('ShaderNodeEmission'); out = nt.nodes.new('ShaderNodeOutputMaterial')
    em.inputs['Color'].default_value = (1, 1, 1, 1); em.inputs['Strength'].default_value = 1
    nt.links.new(em.outputs['Emission'], out.inputs['Surface'])
    return m

def clip_materials(axis, value, keep_less=True, lo=None):
    """make everything beyond plane transparent; back faces shown as flat poche"""
    for m in bpy.data.materials:
        if not m.use_nodes or m.name == 'mask': continue
        nt = m.node_tree
        out = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]
        link = out.inputs['Surface'].links[0]
        src = link.from_node; srcsock = link.from_socket
        geo = nt.nodes.new('ShaderNodeNewGeometry'); sep = nt.nodes.new('ShaderNodeSeparateXYZ')
        cmp_ = nt.nodes.new('ShaderNodeMath'); cmp_.operation = 'GREATER_THAN' if keep_less else 'LESS_THAN'
        cmp_.inputs[1].default_value = value
        tr = nt.nodes.new('ShaderNodeBsdfTransparent')
        pm = nt.nodes.new('ShaderNodeEmission'); pm.inputs['Color'].default_value = (0.95, 0.45, 0.12, 1); pm.inputs['Strength'].default_value = 1.6
        mixb = nt.nodes.new('ShaderNodeMixShader'); mixc = nt.nodes.new('ShaderNodeMixShader')
        nt.links.new(geo.outputs['Position'], sep.inputs['Vector'])
        nt.links.new(sep.outputs[axis], cmp_.inputs[0])
        nt.links.new(geo.outputs['Backfacing'], mixb.inputs['Fac'])
        nt.links.new(srcsock, mixb.inputs[1]); nt.links.new(pm.outputs['Emission'], mixb.inputs[2])
        fac = cmp_.outputs[0]
        if lo is not None:
            c2 = nt.nodes.new('ShaderNodeMath'); c2.operation = 'LESS_THAN'; c2.inputs[1].default_value = lo
            nt.links.new(sep.outputs[axis], c2.inputs[0])
            ad = nt.nodes.new('ShaderNodeMath'); ad.operation = 'MAXIMUM'
            nt.links.new(cmp_.outputs[0], ad.inputs[0]); nt.links.new(c2.outputs[0], ad.inputs[1]); fac = ad.outputs[0]
        nt.links.new(fac, mixc.inputs['Fac'])
        nt.links.new(mixb.outputs[0], mixc.inputs[1]); nt.links.new(tr.outputs[0], mixc.inputs[2])
        nt.links.new(mixc.outputs[0], out.inputs['Surface'])

def hide(names, state=True):
    for n in names:
        if n in bpy.data.objects:
            bpy.data.objects[n].hide_render = state
            bpy.data.objects[n].hide_viewport = state

def open_model(section=False):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, 'model_section.blend' if section else 'model.blend'))

def run(views, tag, samples, scale=1.0):
    outdir = os.path.join(OUT, 'renders'); os.makedirs(outdir, exist_ok=True)
    for v in views:
        open_model(v == 'section')
        t0 = time.time()
        sc = bpy.context.scene
        if v.endswith('_mask'):
            base = v[:-5]
            loc, rot, osc, res = ORTHO[base]
            setup_scene(samples=8, res=(int(res[0] * scale), int(res[1] * scale)), transparent=True, denoise=False)
            sc.render.film_transparent = True
            sc.view_settings.view_transform = 'Standard'
            mm = mask_material()
            sc.view_layers[0].material_override = mm
            hide(['Ground'])
            camera(loc, rot=rot, ortho=osc)
            render_to(os.path.join(outdir, '%s_%s.png' % (v, tag)))
        elif v in ORTHO:
            loc, rot, osc, res = ORTHO[v]
            setup_scene(samples=samples, res=(int(res[0] * scale), int(res[1] * scale)))
            make_world(sc); night_lights()
            camera(loc, rot=rot, ortho=osc)
            render_to(os.path.join(outdir, 'elev_%s_%s.png' % (v, tag)))
        elif v == 'hero':
            setup_scene(samples=samples, res=(int(1920 * scale), int(1080 * scale)))
            make_world(sc); night_lights()
            camera((-175, -200, 62), target=(0, 5, 16), lens=40)
            render_to(os.path.join(outdir, 'hero_%s.png' % tag))
        elif v == 'hero2':
            setup_scene(samples=samples, res=(int(1920 * scale), int(1080 * scale)))
            make_world(sc); night_lights()
            camera((0, -150, 14), target=(0, 0, 20), lens=42)
            render_to(os.path.join(outdir, 'hero_front_%s.png' % tag))
        elif v == 'section':
            setup_scene(samples=samples, res=(int(2000 * scale), int(840 * scale)))
            make_world(sc)
            hide(['Ground'])
            add_light('SUN', (0, 0, 100), 3.0, (1.0, 0.85, 0.7), rot=(0, 90, 0))
            add_light('POINT', (0, -48, 8), 20000, (0.3, 0.7, 1.0), size=3)
            add_light('POINT', (0, 46, 10), 40000, (0.7, 0.4, 1.0), size=3)
            camera((300, 0, 17), rot=(90, 0, 90), ortho=135)
            render_to(os.path.join(outdir, 'section_AA_%s.png' % tag))
        elif v == 'atrium':
            setup_scene(samples=samples, res=(int(1920 * scale), int(1080 * scale)))
            make_world(sc)
            add_light('POINT', (0, 46, 14), 60000, (1.0, 0.75, 0.5), size=2)
            add_light('POINT', (0, 46, 26), 80000, (0.7, 0.5, 1.0), size=2)
            add_light('POINT', (0, 46, 4), 30000, (0.4, 0.8, 1.0), size=2)
            add_light('POINT', (0, 46, 36), 90000, (0.75, 0.6, 1.0), size=3)
            add_light('POINT', (0, 20, 3), 30000, (1.0, 0.75, 0.5), size=2)
            camera((9.0, 34.5, 1.7), target=(-2, 49, 20), lens=15)
            render_to(os.path.join(outdir, 'interior_atrium_%s.png' % tag))
        elif v == 'hall':
            setup_scene(samples=samples, res=(int(1920 * scale), int(1080 * scale)))
            make_world(sc)
            add_light('POINT', (0, 46, 14), 60000, (1.0, 0.75, 0.5), size=2)
            add_light('POINT', (0, 46, 26), 80000, (0.7, 0.5, 1.0), size=2)
            add_light('POINT', (0, 46, 4), 30000, (0.4, 0.8, 1.0), size=2)
            add_light('POINT', (0, 46, 36), 90000, (0.75, 0.6, 1.0), size=3)
            add_light('POINT', (0, 20, 3), 30000, (1.0, 0.75, 0.5), size=2)
            camera((0.0, 12.5, 2.0), target=(0, 46, 14), lens=14)
            render_to(os.path.join(outdir, 'interior_hall_%s.png' % tag))
        elif v == 'gallery':
            setup_scene(samples=samples, res=(int(1920 * scale), int(1080 * scale)))
            make_world(sc)
            for yy in (-20, 0, 20): add_light('POINT', (-64, yy, 14), 25000, (1.0, 0.8, 0.55), size=1.5)
            camera((-64, -31, 9.7), target=(-64, 30, 11.0), lens=18)
            render_to(os.path.join(outdir, 'interior_corridor_%s.png' % tag))
        elif v == 'stairs':
            setup_scene(samples=samples, res=(int(1920 * scale), int(1080 * scale)))
            make_world(sc)
            add_light('POINT', (0, 18, 12), 80000, (1.0, 0.8, 0.55), size=2)
            add_light('POINT', (0, 28, 22), 60000, (0.7, 0.5, 1.0), size=2)
            camera((0, 8.6, 1.9), target=(0, 30, 11), lens=14)
            render_to(os.path.join(outdir, 'interior_grand_stairs_%s.png' % tag))
        elif v == 'stairs_hi':
            setup_scene(samples=samples, res=(int(1920 * scale), int(1080 * scale)))
            make_world(sc)
            add_light('POINT', (0, 18, 12), 80000, (1.0, 0.8, 0.55), size=2)
            add_light('POINT', (0, 28, 22), 60000, (0.7, 0.5, 1.0), size=2)
            add_light('POINT', (0, 12, 4), 30000, (1.0, 0.8, 0.55), size=2)
            camera((-1.5, 9.4, 6.4), target=(0, 26, 7.5), lens=14)
            render_to(os.path.join(outdir, 'interior_lobby_hi_%s.png' % tag))
        elif v == 'stairs_side':
            setup_scene(samples=samples, res=(int(1920 * scale), int(1080 * scale)))
            make_world(sc)
            add_light('POINT', (0, 18, 12), 80000, (1.0, 0.8, 0.55), size=2)
            add_light('POINT', (0, 28, 22), 60000, (0.7, 0.5, 1.0), size=2)
            add_light('POINT', (0, 12, 4), 30000, (1.0, 0.8, 0.55), size=2)
            camera((1.0, 12.5, 1.7), target=(-11, 22, 4.0), lens=16)
            render_to(os.path.join(outdir, 'interior_lobby_side_%s.png' % tag))
        elif v == 'tower_top':
            setup_scene(samples=samples, res=(int(1600 * scale), int(900 * scale)))
            make_world(sc)
            add_light('POINT', (-74.5, 55, 22.5), 3000, (1.0, 0.8, 0.55), size=1.0)
            add_light('POINT', (-74.5, 50, 20.5), 2500, (0.6, 0.8, 1.0), size=1.0)
            camera((-74.0, 58.9, 21.9), target=(-72.5, 49.0, 24.6), lens=17)
            render_to(os.path.join(outdir, 'tower_top_stairs_%s.png' % tag))
        elif v == 'tower_cut':
            setup_scene(samples=samples, res=(int(1600 * scale), int(900 * scale)))
            make_world(sc)
            clip_materials('Y', 53.0, keep_less=True)
            night_lights()
            add_light('SUN', (0, 0, 100), 2.5, (1.0, 0.85, 0.7), rot=(35, 0, 25))
            add_light('POINT', (-74, 50, 24), 20000, (1.0, 0.8, 0.55), size=2)
            camera((-52, 88, 40), target=(-72, 50, 20), lens=30)
            render_to(os.path.join(outdir, 'tower_cutaway_%s.png' % tag))
        elif v == 'central_top':
            setup_scene(samples=samples, res=(int(1600 * scale), int(900 * scale)))
            make_world(sc)
            add_light('POINT', (0, 18, 12), 80000, (1.0, 0.8, 0.55), size=2)
            add_light('POINT', (0, 28, 22), 60000, (0.7, 0.5, 1.0), size=2)
            add_light('POINT', (0, 28, 18), 20000, (1.0, 0.8, 0.55), size=2)
            camera((0.0, 9.0, 17.7), target=(0, 27, 18.0), lens=14)
            render_to(os.path.join(outdir, 'central_top_%s.png' % tag))
        elif v in CLOSEUPS:
            cam, tgt, lens, lights, fname = CLOSEUPS[v]
            setup_scene(samples=samples, res=(int(1600 * scale), int(900 * scale)))
            make_world(sc); night_lights()
            for (lk, loc, en, col, sz) in lights: add_light(lk, loc, en, col, size=sz)
            camera(cam, target=tgt, lens=lens)
            render_to(os.path.join(outdir, '%s_%s.png' % (fname, tag)))
        elif v == 'cutaway':
            setup_scene(samples=samples, res=(int(1920 * scale), int(1080 * scale)))
            make_world(sc)
            hide(['Roofs', 'Dome', 'Screens'])
            clip_materials('Z', 22.8, keep_less=True)
            night_lights()
            add_light('SUN', (0, 0, 100), 2.5, (1.0, 0.85, 0.7), rot=(35, 0, 25))
            add_light('POINT', (0, 46, 16), 90000, (0.7, 0.5, 1.0), size=2)
            camera((-120, -140, 130), target=(0, 5, 8), lens=38)
            render_to(os.path.join(outdir, 'cutaway_%s.png' % tag))
        print(v, 'done', round(time.time() - t0, 1), 's')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--views', required=True); ap.add_argument('--tag', default='r1')
    ap.add_argument('--samples', type=int, default=32); ap.add_argument('--scale', type=float, default=1.0)
    a = ap.parse_args()
    run(a.views.split(','), a.tag, a.samples, a.scale)
