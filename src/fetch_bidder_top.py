"""t36u: bidder.top works (https://api.bidder.top/artwork/list, POST form pageNum/pageSize, public) -> data/bidder_top_raw.json
(personal / wallet fields stripped) and appended to web/artworks.json AFTER the bidder.art works (source='bidder.top'),
grouped by artist in list order.  Existing works / placement order untouched (art_assign packs artists contiguously).
Media: images = api.bidder.top/file/getFile/<key> (CORS reflected, Range ok), videos = Cloudflare Stream (videodelivery.net).
usage: fetch_bidder_top.py [--offline]  (offline: reuse data/bidder_top_raw.json)"""
import json, re, sys, urllib.request, urllib.parse
R = '/workspace/outputs/cyber_louvre/'
API = 'https://api.bidder.top/'; FILE = API + 'file/getFile/'; VD = 'https://videodelivery.net/'
SITE = 'https://bidder.top/#/product/'; ARTIST = 'https://bidder.top/#/center/'
STRIP = {'ownerId', 'ownerName', 'artistContractAddr', 'metaMaskAddr', 'createTxnHash', 'artworkOwnerInfoVo', 'lastOwnerId', 'ownerAvatar', 'partnerName'}
EMAIL = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'); WALLET = re.compile(r'0x[0-9a-fA-F]{40}')
def post(path, **kw):
    q = urllib.request.Request(API + path, data=urllib.parse.urlencode(kw).encode(), headers={'User-Agent': 'Mozilla/5.0'})
    return json.load(urllib.request.urlopen(q, timeout=40))
def clean(o):
    if isinstance(o, dict): return {k: clean(v) for k, v in o.items() if k not in STRIP}
    if isinstance(o, list): return [clean(v) for v in o]
    if isinstance(o, str): return WALLET.sub('[wallet removed]', EMAIL.sub('[email removed]', o))
    return o
def fetch():
    items, page = [], 1
    while True:
        r = post('artwork/list', pageNum=page, pageSize=50)['result']; items += r['data']
        if len(items) >= int(r['total']) or not r['data']: break
        page += 1
    info = {}
    for x in items:
        d = post('artwork/info', artworkId=x['id'])
        if d.get('code') == 200: info[x['id']] = d['result']
    return dict(source=API + 'artwork/list (POST pageNum,pageSize) + artwork/info (POST artworkId)', total=len(items), list=clean(items), info=clean(info))
def hls_meta(key):
    try:
        t = urllib.request.urlopen(urllib.request.Request(VD + key + '/manifest/video.m3u8', headers={'User-Agent': 'Mozilla/5.0'}), timeout=30).read().decode()
        res = [tuple(map(int, m.split('x'))) for m in re.findall(r'RESOLUTION=(\d+x\d+)', t)]
        return dict(has_audio=('TYPE=AUDIO' in t) or ('mp4a' in t), res=max(res, key=lambda r: r[0] * r[1]) if res else None)
    except Exception as e: return dict(has_audio=None, res=None, err=str(e)[:60])
def normalize(raw):
    works, artists, order = [], {}, []
    for x in raw['list']:
        i = raw['info'].get(x['id'], {}); t = int(x['artworkType']); aid = x['artistId']
        files = i.get('artworkFileVos') or []
        w = dict(id=x['id'], source='bidder.top', title=x['name'].strip(), artist=x['artistName'].strip(), artist_id=aid, type=t,
                 detail_url=SITE + x['id'], artist_url=ARTIST + aid, ipfs=[f.get('ipfsHash') for f in files if f.get('ipfsHash')])
        cover = x.get('cover') or ''
        if t == 3:
            m = hls_meta(x['storageKey'])
            w.update(media='video', video_id=x['storageKey'], video=VD + x['storageKey'] + '/manifest/video.m3u8',
                     thumbnail=VD + x['storageKey'] + '/thumbnails/thumbnail.jpg?height=480', has_audio=m['has_audio'])
            w['image'] = FILE + cover if cover else w['thumbnail']
            W, H = (i.get('coverWidth') or 0), (i.get('coverHeight') or 0)
            if not (W and H) and m['res']: W, H = m['res']
        else:
            w.update(media='image', image=FILE + cover if cover else FILE + x['storageKey'], image_full=FILE + x['storageKey'])
            W, H = (i.get('coverWidth') or 0), (i.get('coverHeight') or 0)
            if re.search(r'\.gif$', x['storageKey'], re.I): w['animated'] = True; w['image'] = FILE + x['storageKey']
        if W and H: w.update(width=W, height=H, aspect=round(W / H, 4))
        intro = (i.get('intro') or i.get('details') or '').strip()
        if intro: w['intro'] = intro[:400]
        if aid not in artists:
            av = i.get('artistAvatar'); artists[aid] = dict(id=aid, name=w['artist'], avatar=(FILE + av) if av else None, profile_url=ARTIST + aid, source='bidder.top', works=[]); order.append(aid)
        artists[aid]['works'].append(w)
    for aid in order:                       # grouped by artist, first-appearance (list) order
        works += artists[aid]['works']
    return works, [artists[a] for a in order]
def merge(A, works, artists):
    """append to artworks.json dict A (idempotent: previous bidder.top entries replaced)"""
    prev_thumb = {w['id']: w['local_thumb'] for w in A['artworks'] if w.get('source') == 'bidder.top' and w.get('local_thumb')}
    for w in works:                         # pre-resized covers (web/thumbs/top_<id>.jpg; wsrv.nl refuses the .top TLD) survive a rebuild
        if w['id'] in prev_thumb: w['local_thumb'] = prev_thumb[w['id']]
    keep_w = [w for w in A['artworks'] if w.get('source') != 'bidder.top']; keep_a = [a for a in A['artists'] if a.get('source') != 'bidder.top']
    have = {w['id'] for w in keep_w}; hashes = set()
    for w in keep_w:
        for k in ('image_path', 'video', 'audio', 'thumbnail', 'image'):
            for h in re.findall(r'(Qm[1-9A-HJ-NP-Za-km-z]{44}|[0-9a-f]{32})', w.get(k) or ''): hashes.add(h)
    overlaps, add = [], []
    for w in works:
        hit = w['id'] in have or any(h in hashes for h in w.get('ipfs', []) + [w.get('video_id') or ''])
        if hit: overlaps.append(w['id'])
        else: add.append(w)
    first = len(keep_w); out_a = []
    for a in artists:
        ws = [w for w in a['works'] if w in add]
        if not ws: continue
        out_a.append(dict(id=a['id'], name=a['name'], avatar=a['avatar'], profile_url=a['profile_url'], source='bidder.top', works_total=len(a['works']), first=first, n=len(ws)))
        first += len(ws)
    A['artworks'] = keep_w + [w for a in artists for w in a['works'] if w in add]
    A['artists'] = keep_a + out_a; A['count'] = len(A['artworks'])
    A['bidder_top'] = dict(api=API + 'artwork/list', total=len(works), added=len(add), overlaps=overlaps)
    return A
if __name__ == '__main__':
    raw = json.load(open(R + 'data/bidder_top_raw.json')) if '--offline' in sys.argv else fetch()
    json.dump(raw, open(R + 'data/bidder_top_raw.json', 'w'), ensure_ascii=False, indent=1)
    works, artists = normalize(raw)
    A = merge(json.load(open(R + 'web/artworks.json')), works, artists)
    json.dump(A, open(R + 'web/artworks.json', 'w'), ensure_ascii=False, indent=1)
    print('bidder.top total', len(works), 'added', A['bidder_top']['added'], 'overlaps', A['bidder_top']['overlaps'], 'artworks now', A['count'], 'artists', len(artists))
