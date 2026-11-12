import numpy as np
from PIL import Image
from scipy import ndimage as ndi
ROI = {  # panel: (x0,x1,ybase) in panel-crop pixel coords: building region above ybase
 'front': (38, 676, 207), 'back': (36, 676, 207), 'left': (30, 664, 148), 'right': (30, 664, 148)}
DIM = {'front': None, 'back': None, 'left': None, 'right': None}

def ref_mask(name, thr=38):
    im = np.asarray(Image.open('/workspace/outputs/cyber_louvre/ref/%s.png' % name).convert('RGB')).astype(float)
    bg = np.median(im[2:10, 2:10].reshape(-1, 3), axis=0)
    d = np.abs(im - bg).sum(2)
    m = d > thr
    x0, x1, yb = ROI[name]
    roi = np.zeros_like(m); roi[:yb, x0:x1] = True
    m &= roi
    m = ndi.binary_closing(m, structure=np.ones((3, 3)), iterations=3)
    m = ndi.binary_fill_holes(m)
    m = ndi.binary_opening(m, structure=np.ones((3, 3)), iterations=1)
    lab, n = ndi.label(m)
    if n > 1:
        sizes = ndi.sum(m, lab, range(1, n + 1))
        keep = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s > 400])
        m = keep
    return m

if __name__ == '__main__':
    for n in ROI:
        m = ref_mask(n)
        ys, xs = np.where(m)
        print(n, m.shape, 'bbox x', xs.min(), xs.max(), 'y', ys.min(), ys.max(), 'area', m.sum())
        Image.fromarray((m * 255).astype(np.uint8)).save('/tmp/rm_%s.png' % n)
