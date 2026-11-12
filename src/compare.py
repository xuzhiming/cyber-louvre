import os, sys, json
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import map_coordinates
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import refmask
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
PPM = 6   # frame pixels per metre
ZMAX = 52.0
# panel calibration in panel-crop pixels: xl,xr = dimension-line end points; half = half span in m; yb = baseline row; ytop = row of 46 m
CAL = {
 'front': dict(xl=51, xr=665, half=90, yb=205, ytop=25),
 'back':  dict(xl=47, xr=665, half=90, yb=205, ytop=25),
 'left':  dict(xl=128, xr=573, half=60, yb=146, ytop=3),
 'right': dict(xl=129, xr=575, half=60, yb=146, ytop=3),
}
# model renders: ortho scale 10 px/m, centre (u=0, z=21)
MODEL = {'front': (2000, 560), 'back': (2000, 560), 'left': (1500, 560), 'right': (1500, 560)}
MARGIN = 20

def grid(name):
    half = CAL[name]['half']
    us = np.arange(-(half + MARGIN), half + MARGIN, 1.0 / PPM) + 0.5 / PPM
    zs = np.arange(ZMAX, 0, -1.0 / PPM) - 0.5 / PPM
    U, Z = np.meshgrid(us, zs)
    return U, Z

def sample_ref(name, arr, order=1):
    c = CAL[name]; U, Z = grid(name)
    sx = (c['xr'] - c['xl']) / (2 * c['half']); sz = (c['yb'] - c['ytop']) / 46.0
    px = c['xl'] + (U + c['half']) * sx; py = c['yb'] - Z * sz
    if arr.ndim == 2: return map_coordinates(arr, [py, px], order=order, mode='constant', cval=0)
    return np.dstack([map_coordinates(arr[..., k], [py, px], order=order, mode='constant', cval=0) for k in range(arr.shape[2])])

def sample_model(name, arr, order=1):
    U, Z = grid(name); H, W = arr.shape[:2]; ppm = W / (MODEL[name][0] / 10.0)
    px = W / 2 + U * ppm - 0.5; py = H / 2 - (Z - 21) * ppm - 0.5
    if arr.ndim == 2: return map_coordinates(arr, [py, px], order=order, mode='constant', cval=0)
    return np.dstack([map_coordinates(arr[..., k], [py, px], order=order, mode='constant', cval=0) for k in range(arr.shape[2])])

def top_profile(m):
    h = np.zeros(m.shape[1])
    for x in range(m.shape[1]):
        ys = np.where(m[:, x])[0]
        h[x] = (m.shape[0] - ys.min()) / PPM if len(ys) else 0
    return h

def compare_view(name, tag):
    ref_img = np.asarray(Image.open(os.path.join(OUT, 'ref/%s.png' % name)).convert('RGB')).astype(float)
    rm = refmask.ref_mask(name).astype(float)
    rmf = sample_ref(name, rm) > 0.5
    ref_rgb = sample_ref(name, ref_img).clip(0, 255).astype(np.uint8)
    mk = np.asarray(Image.open(os.path.join(OUT, 'renders/%s_mask_%s.png' % (name, tag)))).astype(float)[..., 3] / 255
    mmf = sample_model(name, mk) > 0.5
    beauty_p = os.path.join(OUT, 'renders/elev_%s_%s.png' % (name, tag))
    mod_rgb = sample_model(name, np.asarray(Image.open(beauty_p).convert('RGB')).astype(float)).clip(0, 255).astype(np.uint8) if os.path.exists(beauty_p) else np.zeros_like(ref_rgb)
    half = CAL[name]['half']
    U, Z = grid(name)
    inb = np.abs(U) <= half
    def iou(a, b, sel=None):
        if sel is not None: a = a & sel; b = b & sel
        return float((a & b).sum() / max((a | b).sum(), 1))
    s_full = iou(rmf, mmf); s_bld = iou(rmf, mmf, inb)
    pr, pm = top_profile(rmf), top_profile(mmf)
    sel = np.abs(U[0]) <= half
    prof_err = float(np.abs(pr[sel] - pm[sel]).mean())
    # overlay
    ov = np.zeros(rmf.shape + (3,), np.uint8)
    ov[rmf & ~mmf] = (255, 60, 60); ov[mmf & ~rmf] = (60, 200, 255); ov[rmf & mmf] = (235, 235, 235)
    H, W = rmf.shape
    sheet = Image.new('RGB', (W, H * 3 + 40), (20, 20, 30))
    d = ImageDraw.Draw(sheet)
    sheet.paste(Image.fromarray(ref_rgb), (0, 20)); d.text((6, 4), 'sheet panel (%s) - recalibrated to metres' % name, fill=(255, 255, 255))
    sheet.paste(Image.fromarray(mod_rgb), (0, H + 30)); d.text((6, H + 14), 'model render', fill=(255, 255, 255))
    sheet.paste(Image.fromarray(ov), (0, 2 * H + 40)); d.text((6, 2 * H + 24), 'silhouette overlay: white=both  red=sheet only  cyan=model only   IoU(all)=%.3f IoU(building span)=%.3f topEdgeErr=%.2fm' % (s_full, s_bld, prof_err), fill=(255, 255, 255))
    os.makedirs(os.path.join(OUT, 'compare'), exist_ok=True)
    sheet.save(os.path.join(OUT, 'compare/compare_%s_%s.png' % (name, tag)))
    return dict(view=name, iou_all=s_full, iou_building=s_bld, top_err_m=prof_err)

def compare_top(tag):
    """plan: bbox-normalised IoU against the sheet's roof plan (footprint incl. courtyard paving)"""
    ref = Image.open(os.path.join(OUT, 'ref/plan.png')).convert('RGB')
    arr = np.asarray(ref).astype(float)
    bg = np.median(arr[2:10, 2:10].reshape(-1, 3), axis=0)
    d = np.abs(arr - bg).sum(2)
    m = d > 38
    roi = np.zeros_like(m); roi[40:262, 38:388] = True
    m &= roi
    from scipy import ndimage as ndi
    m = ndi.binary_closing(m, np.ones((3, 3)), iterations=3); m = ndi.binary_fill_holes(m)
    lab, n = ndi.label(m)
    sizes = ndi.sum(m, lab, range(1, n + 1)); m = lab == (1 + int(np.argmax(sizes)))
    ys, xs = np.where(m); bb = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
    mk = np.asarray(Image.open(os.path.join(OUT, 'renders/top_mask_%s.png' % tag))).astype(float)[..., 3] > 127
    ys2, xs2 = np.where(mk); bb2 = (xs2.min(), ys2.min(), xs2.max() + 1, ys2.max() + 1)
    W, H = 540, 360
    rc = Image.fromarray((m[bb[1]:bb[3], bb[0]:bb[2]] * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
    mc = Image.fromarray((mk[bb2[1]:bb2[3], bb2[0]:bb2[2]] * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
    a = np.asarray(rc) > 127; b = np.asarray(mc) > 127
    s_raw = float((a & b).sum() / (a | b).sum())
    # fill courtyard (open U) in the model mask to compare "footprint + paving" like the sheet's plan
    from scipy import ndimage as ndi2
    bf = b.copy()
    # courtyard paving rectangle in model coordinates (x -54..54, y -70..30) -> plan-mask coordinates
    fx = lambda x: (x - (-90)) / 180 * W; fy = lambda y: (60 - y) / 120 * H
    bf[int(fy(30)):int(fy(-60)), int(fx(-54)):int(fx(54))] = True
    s_fill = float((a & bf).sum() / (a | bf).sum())
    ov = np.zeros((H, W, 3), np.uint8); ov[a & ~bf] = (255, 60, 60); ov[bf & ~a] = (60, 200, 255); ov[a & bf] = (235, 235, 235)
    ref_c = ref.crop(bb).resize((W, H)); top_p = os.path.join(OUT, 'renders/elev_top_%s.png' % tag)
    mod_c = Image.open(top_p).convert('RGB').crop(bb2).resize((W, H)) if os.path.exists(top_p) else Image.new('RGB', (W, H))
    sheet = Image.new('RGB', (W * 3, H + 20), (20, 20, 30)); sheet.paste(ref_c, (0, 20)); sheet.paste(mod_c, (W, 20)); sheet.paste(Image.fromarray(ov), (2 * W, 20))
    dd = ImageDraw.Draw(sheet); dd.text((6, 4), 'sheet roof plan | model top view | overlay (white both, red sheet only, cyan model only)  IoU(footprint+courtyard)=%.3f  IoU(strict U footprint)=%.3f' % (s_fill, s_raw), fill=(255, 255, 255))
    sheet.save(os.path.join(OUT, 'compare/compare_top_%s.png' % tag))
    return dict(view='top', iou_all=s_fill, iou_building=s_raw, top_err_m=float('nan'))

def run(tag, views=('front', 'back', 'left', 'right', 'top')):
    res = []
    for v in views:
        res.append(compare_top(tag) if v == 'top' else compare_view(v, tag))
    json.dump(res, open(os.path.join(OUT, 'compare/scores_%s.json' % tag), 'w'), indent=1)
    for r in res: print(r)
    return res

if __name__ == '__main__':
    run(sys.argv[1])
