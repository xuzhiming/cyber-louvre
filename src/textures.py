import numpy as np, os
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import zoom, gaussian_filter
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tex')
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)

def noise(n, sc, seed=0):
    r = np.random.default_rng(seed)
    g = r.random((sc, sc))
    z = zoom(np.tile(g, (3, 3)), n / sc, order=3, mode='nearest')
    o = n
    return z[o:2 * o, o:2 * o]

def save(name, arr):
    arr = np.clip(arr, 0, 1)
    Image.fromarray((arr * 255).astype(np.uint8)).save(os.path.join(OUT, name + '.png'))

def stone(n=512, base=(0.80, 0.68, 0.50), rows=6, cols=3, emit_k=0.42, name='stone'):
    img = np.zeros((n, n, 3))
    nz = noise(n, 8, 1) * 0.5 + noise(n, 32, 2) * 0.35 + noise(n, 128, 3) * 0.15
    mort = np.zeros((n, n))
    rh = n // rows
    for r in range(rows):
        off = (r % 2) * (n // cols // 2)
        y0 = r * rh
        mort[y0:y0 + 3, :] = 1
        for c in range(cols):
            x0 = (c * (n // cols) + off) % n
            mort[y0:y0 + rh, x0:x0 + 3] = 1
            # per block tone
            tone = 0.9 + 0.2 * rng.random()
            xs = np.arange(n)
            idx_x = ((xs - x0) % n) < (n // cols)
            img[y0:y0 + rh, idx_x] = np.array(base) * tone
    img = img * (0.85 + 0.3 * nz[..., None])
    img[mort > 0] *= 0.55
    save(name + '_albedo', img)
    save(name + '_emit', img * np.array([1.0, 0.82, 0.55]) * emit_k * 1.6)
    # normal map from height
    h = gaussian_filter(1 - mort * 0.8 + nz * 0.3, 1.0)
    gx, gy = np.gradient(h)
    nrm = np.dstack([-gx * 6, gy * 6, np.ones_like(h)]); nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    save(name + '_normal', nrm * 0.5 + 0.5)

def slate(n=512):
    img = np.zeros((n, n, 3)); rows = 16
    nz = noise(n, 64, 5)
    for r in range(rows):
        y0 = r * n // rows
        for c in range(12):
            x0 = (c * n // 12 + (r % 2) * n // 24) % n
            t = 0.7 + 0.5 * rng.random()
            xs = np.arange(n); m = ((xs - x0) % n) < (n // 12 - 2)
            img[y0:y0 + n // rows - 2, m] = np.array([0.08, 0.11, 0.18]) * t
    img = img * (0.8 + 0.4 * nz[..., None]) + 0.01
    save('slate_albedo', img)
    save('slate_emit', img * 1.1 + np.array([0.0, 0.01, 0.03]))

def slate_grey(n=512):
    r = np.random.default_rng(11)
    img = np.zeros((n, n, 3)); rows = 16
    nz = noise(n, 64, 5)
    for rr in range(rows):
        y0 = rr * n // rows
        for c in range(12):
            x0 = (c * n // 12 + (rr % 2) * n // 24) % n
            t = 0.8 + 0.4 * r.random()
            xs = np.arange(n); m = ((xs - x0) % n) < (n // 12 - 2)
            img[y0:y0 + n // rows - 2, m] = np.array([0.40, 0.42, 0.44]) * t
    img = img * (0.85 + 0.3 * nz[..., None]) + 0.02
    save('slate_grey_albedo', img)

def flat(name, base, var=0.08, sc=64, seed=3, n=256, grid=None, emit=None):
    nz = noise(n, sc, seed)
    img = np.array(base)[None, None, :] * (1 - var + 2 * var * nz[..., None])
    if grid:
        for k in range(0, n, grid):
            img[k:k + 2, :] *= 0.6; img[:, k:k + 2] *= 0.6
    save(name + '_albedo', img)
    if emit is not None: save(name + '_emit', img * np.array(emit))

def portrait(name, hue, seed):
    W, H = 256, 512
    r = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W] / np.array([H, W])[:, None, None]
    bg = np.dstack([0.10 + 0.5 * hue[0] * yy, 0.06 + 0.4 * hue[1] * (1 - yy), 0.25 + 0.7 * hue[2] * (0.5 + 0.5 * xx)])
    im = Image.fromarray((np.clip(bg, 0, 1) * 255).astype(np.uint8))
    d = ImageDraw.Draw(im, 'RGBA')
    cx = W // 2
    # shoulders & head
    d.polygon([(20, H), (40, 400), (100, 360), (156, 360), (216, 400), (236, H)], fill=(40, 30, 80, 255))
    d.rectangle([cx - 22, 330, cx + 22, 380], fill=(180, 150, 190, 255))
    d.ellipse([cx - 64, 120, cx + 64, 350], fill=(215, 175, 200, 255))
    d.ellipse([cx - 70, 100, cx + 70, 220], fill=(60, 30, 90, 255))        # hair
    d.ellipse([cx - 42, 215, cx - 14, 235], fill=(30, 20, 60, 255)); d.ellipse([cx + 14, 215, cx + 42, 235], fill=(30, 20, 60, 255))
    d.ellipse([cx - 36, 220, cx - 22, 230], fill=(90, 230, 255, 255)); d.ellipse([cx + 22, 220, cx + 36, 230], fill=(90, 230, 255, 255))
    d.polygon([(cx, 235), (cx - 10, 285), (cx + 10, 285)], fill=(170, 130, 160, 255))
    d.ellipse([cx - 22, 305, cx + 22, 322], fill=(190, 60, 120, 255))
    for k in range(6):
        d.line([(cx - 64, 150 + k * 10), (cx - 90 - k * 3, 170 + k * 20)], fill=(120, 80, 255, 200), width=2)
        d.line([(cx + 64, 150 + k * 10), (cx + 90 + k * 3, 170 + k * 20)], fill=(120, 80, 255, 200), width=2)
    im = im.filter(ImageFilter.GaussianBlur(1.2))
    a = np.asarray(im).astype(float) / 255
    a[::4] *= 0.8   # scan lines
    a = np.clip(a * 1.15, 0, 1)
    Image.fromarray((a * 255).astype(np.uint8)).save(os.path.join(OUT, name + '.png'))

def tint_lavender():
    """one-off: re-tint the existing warm stone/trim/plaster textures to light purple (#c9b8dc), keeping the luminance
    pattern (block tones, mortar, noise) and the emission/albedo ratio; the stair texture keeps the old warm trim."""
    import shutil
    for n in ('trim_albedo', 'trim_emit'):
        shutil.copy(os.path.join(OUT, n + '.png'), os.path.join(OUT, n.replace('trim', 'stair') + '.png'))
    tgt = np.array([0xc9, 0xb8, 0xdc]) / 255.0
    W = np.array([0.2126, 0.7152, 0.0722])
    for name, base in (('stone', (0.80, 0.68, 0.50)), ('trim', (0.88, 0.78, 0.60)), ('plaster', (0.78, 0.70, 0.58))):
        a = np.asarray(Image.open(os.path.join(OUT, name + '_albedo.png')).convert('RGB')).astype(float) / 255
        e = np.asarray(Image.open(os.path.join(OUT, name + '_emit.png')).convert('RGB')).astype(float) / 255
        la = (a @ W)[..., None]; ratio = (e @ W)[..., None] / np.maximum(la, 1e-4)
        na = la / (np.array(base) @ W) * tgt
        ne = na * ratio * np.array([0.92, 0.88, 1.0])
        save(name + '_albedo', na); save(name + '_emit', ne)

def tint_exterior_slate(target_hex=(0x69, 0x6a, 0x71)):
    """exterior wall + facade trim -> warm-neutral grey #696A71 (was #3A3F4B) (mean sRGB albedo == target), same luminance pattern.
    The light-purple trim texture is kept as trim_in_* for interior props. Run after tint_lavender()."""
    import shutil
    for n in ('trim_albedo', 'trim_emit'):
        dst = os.path.join(OUT, n.replace('trim', 'trim_in'))
        if not os.path.exists(dst + '.png'): shutil.copy(os.path.join(OUT, n + '.png'), dst + '.png')
    tgt = np.array(target_hex) / 255.0; W = np.array([0.2126, 0.7152, 0.0722])
    for name in ('stone', 'trim'):
        a = np.asarray(Image.open(os.path.join(OUT, name + '_albedo.png')).convert('RGB')).astype(float) / 255
        e = np.asarray(Image.open(os.path.join(OUT, name + '_emit.png')).convert('RGB')).astype(float) / 255
        la = (a @ W)[..., None]; ratio = (e @ W)[..., None] / np.maximum(la, 1e-4)
        na = la / la.mean() * tgt
        ne = na * ratio * np.array([0.9, 0.95, 1.0])
        save(name + '_albedo', na); save(name + '_emit', ne)

def tint_roof_dark(target_hex=(0x4c, 0x4d, 0x52)):
    """roof slate -> #4C4D52 = 0.725 x the #696A71 wall colour (same hue family, darker; same ratio as the old #2A2E37 / #3A3F4B): mean sRGB albedo == target."""
    a = np.asarray(Image.open(os.path.join(OUT, 'slate_grey_albedo.png')).convert('RGB')).astype(float) / 255
    la = (a @ np.array([0.2126, 0.7152, 0.0722]))[..., None]
    save('slate_grey_albedo', la / la.mean() * (np.array(target_hex) / 255.0))

if __name__ == '__main__':
    stone(emit_k=0.26)
    stone(base=(0.88, 0.78, 0.60), rows=8, cols=3, emit_k=0.30, name='trim')
    slate()
    flat('plaster', (0.78, 0.70, 0.58), emit=(0.35, 0.28, 0.2))
    flat('slab', (0.40, 0.38, 0.42), var=0.1, emit=(0.2, 0.18, 0.22))
    flat('plaza', (0.16, 0.17, 0.24), var=0.1, grid=32, emit=(0.5, 0.5, 0.8))
    flat('ground', (0.05, 0.06, 0.09), var=0.2, sc=128, emit=(0.4, 0.4, 0.6))
    flat('concrete', (0.42, 0.42, 0.45), var=0.12, emit=(0.18, 0.18, 0.22))
    tint_lavender()
    tint_exterior_slate()
    slate_grey(); tint_roof_dark()
    portrait('screen_a', (1.0, 0.5, 1.0), 1)
    portrait('screen_b', (0.4, 1.0, 1.0), 2)
    print(os.listdir(OUT))
