import bpy, os
TEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tex')

# name: (albedo(tex or rgb), emission(tex or rgb or None), emission strength, rough, metal, alpha, uv_scale)
MATS = {
 'stone_wall':  ('stone_albedo', 'stone_emit', 1.0, 0.85, 0.0, 1.0, 4.0),
 'stone_trim':  ('trim_albedo',  'trim_emit',  1.0, 0.8, 0.0, 1.0, 3.0),
 'stone_trim_in': ('trim_in_albedo', 'trim_in_emit', 1.0, 0.8, 0.0, 1.0, 3.0),   # interior props: stays light purple
 'plaster':     ('plaster_albedo', 'plaster_emit', 1.0, 0.9, 0.0, 1.0, 4.0),
 'slab':        ('slab_albedo', 'slab_emit', 1.0, 0.5, 0.0, 1.0, 4.0),
 'concrete':    ('concrete_albedo', 'concrete_emit', 1.0, 0.8, 0.0, 1.0, 4.0),
 'stair':       ('stair_albedo', 'stair_emit', 0.8, 0.6, 0.0, 1.0, 3.0),
 'plaza':       ('plaza_albedo', 'plaza_emit', 1.0, 0.35, 0.0, 1.0, 8.0),
 'ground':      ('ground_albedo', 'ground_emit', 1.0, 0.9, 0.0, 1.0, 12.0),
 'roof_metal':  ('slate_grey_albedo', None, 0, 0.6, 0.15, 1.0, 5.0),   # #4C4D52 mean: 0.725 x the #696A71 walls (same hue family, darker)
 'roof_cap':    ((0.1095, 0.1119, 0.1301), None, 0, 0.5, 0.3, 1.0, 4.0),   # copings / lanterns / dome rings #5D5E65 (0.89 x walls)
 # window glass: default (= day look) is dark grey tinted glass ~#3a3d42; the web night mode swaps in the light tint (0.70,0.83,0.92 a=.38 / 0.72,0.88,0.82 a=.42)
 'win_glass':   ((0.042, 0.047, 0.054), None, 0, 0.08, 0.15, 0.55, 4.0),
 'win_glass_g': ((0.044, 0.052, 0.052), None, 0, 0.08, 0.15, 0.50, 4.0),
 'frame_dark':  ((0.03, 0.03, 0.05), None, 0, 0.5, 0.6, 1.0, 4.0),
 'rail_metal':  ((0.7, 0.55, 0.3), None, 0, 0.35, 1.0, 1.0, 4.0),
 'rail_glass':  ((0.6, 0.8, 1.0), (0.3, 0.6, 1.0), 0.2, 0.05, 0.0, 0.25, 4.0),
 'gold':        ((0.85, 0.62, 0.25), (0.9, 0.6, 0.2), 0.6, 0.35, 1.0, 1.0, 4.0),
 'glass':       ((0.45, 0.65, 1.0), (0.35, 0.45, 1.0), 0.55, 0.05, 0.0, 0.28, 4.0),
 'glass_dome':  ((0.4, 0.55, 1.0), (0.30, 0.45, 1.0), 0.6, 0.05, 0.0, 0.32, 4.0),
 'glass_frame': ((0.55, 0.42, 0.22), (0.9, 0.6, 0.3), 0.5, 0.35, 1.0, 1.0, 4.0),
 'window_warm': ((1.0, 0.72, 0.35), (1.0, 0.68, 0.30), 5.0, 0.5, 0.0, 1.0, 4.0),
 'window_pink': ((1.0, 0.25, 0.65), (1.0, 0.18, 0.60), 5.0, 0.5, 0.0, 1.0, 4.0),
 'window_purple': ((0.55, 0.30, 1.0), (0.55, 0.25, 1.0), 5.0, 0.5, 0.0, 1.0, 4.0),
 'window_cyan': ((0.2, 0.9, 1.0), (0.2, 0.9, 1.0), 5.0, 0.5, 0.0, 1.0, 4.0),
 'neon_magenta': ((1.0, 0.1, 0.7), (1.0, 0.08, 0.65), 9.0, 0.4, 0.0, 1.0, 4.0),
 'neon_cyan':   ((0.1, 0.9, 1.0), (0.1, 0.9, 1.0), 9.0, 0.4, 0.0, 1.0, 4.0),
 'neon_purple': ((0.6, 0.2, 1.0), (0.6, 0.2, 1.0), 8.0, 0.4, 0.0, 1.0, 4.0),
 'neon_roof':   ((1.0, 0.815, 0.434), (1.0, 0.815, 0.434), 9.0, 0.4, 0.0, 1.0, 4.0),      # t38u roof / dome strips: pale yellow #FFE9B0 (linear)
 'neon_roof_ridge': ((1.0, 0.761, 0.352), (1.0, 0.761, 0.352), 8.0, 0.4, 0.0, 1.0, 4.0),  # roof ridge lines: #FFE2A0 (was neon_purple)
 'water':       ((0.02, 0.06, 0.12), (0.05, 0.4, 0.6), 0.6, 0.02, 0.0, 1.0, 4.0),
 'light_panel': ((1.0, 0.9, 0.7), (1.0, 0.85, 0.6), 7.0, 0.5, 0.0, 1.0, 4.0),
 'exhibit_a':   ((0.3, 0.9, 1.0), (0.3, 0.9, 1.0), 4.0, 0.4, 0.0, 1.0, 4.0),
 'exhibit_b':   ((1.0, 0.5, 0.2), (1.0, 0.5, 0.2), 4.0, 0.4, 0.0, 1.0, 4.0),
 'exhibit_c':   ((0.9, 0.3, 0.9), (0.9, 0.3, 0.9), 4.0, 0.4, 0.0, 1.0, 4.0),
 'exhibit_d':   ((1.0, 0.9, 0.5), (1.0, 0.9, 0.5), 4.0, 0.4, 0.0, 1.0, 4.0),
 'art_canvas':  ((0.035, 0.035, 0.042), None, 0, 0.9, 0.0, 1.0, 4.0),   # empty display-slot backing
 'exhibit_art': ((1.0, 0.75, 0.4), (1.0, 0.7, 0.35), 3.0, 0.4, 0.0, 1.0, 4.0),
 'holo_purple': ((0.7, 0.3, 1.0), (0.7, 0.3, 1.0), 8.0, 0.2, 0.0, 0.85, 4.0),
 'holo_cyan':   ((0.2, 0.9, 1.0), (0.2, 0.9, 1.0), 8.0, 0.2, 0.0, 0.7, 4.0),
 'poche':       ((0.95, 0.5, 0.15), (0.95, 0.5, 0.15), 1.4, 0.8, 0.0, 1.0, 4.0),
 'screen_a':    ('screen_a', 'screen_a', 2.2, 0.3, 0.0, 1.0, 1.0),
 'screen_b':    ('screen_b', 'screen_b', 2.2, 0.3, 0.0, 1.0, 1.0),
}

_img = {}
def img(name, noncolor=False):
    if name in _img: return _img[name]
    im = bpy.data.images.load(os.path.join(TEX, name + '.png'), check_existing=True)
    if noncolor: im.colorspace_settings.name = 'Non-Color'
    im.pack()
    _img[name] = im
    return im

def make_material(name):
    alb, emi, es, rough, metal, alpha, uv = MATS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    def tex(imname):
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = img(imname); return t
    if isinstance(alb, str):
        nt.links.new(tex(alb).outputs['Color'], b.inputs['Base Color'])
    else:
        b.inputs['Base Color'].default_value = (*alb, 1)
    if emi is not None:
        if isinstance(emi, str):
            nt.links.new(tex(emi).outputs['Color'], b.inputs['Emission Color'])
        else:
            b.inputs['Emission Color'].default_value = (*emi, 1)
        b.inputs['Emission Strength'].default_value = es
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if alpha < 1.0:
        b.inputs['Alpha'].default_value = alpha
        try: m.surface_render_method = 'BLENDED'
        except Exception: pass
        try: m.blend_method = 'BLEND'
        except Exception: pass
    return m
