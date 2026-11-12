"""t28u: artists in https://bidder.art/artist/list order (POST /rare/artist/artistList opt=Active, as the page does), then every
artist's works (POST /rare/artist/artistArtworkList artistId/id/pageNum/pageSize/text/opt=Newest = the profile 'Created' tab default; opt=Active returns HTTP-200 code 500).
Raw dumps -> data/ (wallet addresses stripped)."""
import json, time, urllib.request, urllib.parse, sys, os
API = 'https://api.bidder.art'
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
def post(path, **kw):
    for k in range(4):
        try:
            req = urllib.request.Request(API + path, data=urllib.parse.urlencode(kw).encode(), headers={'Content-Type': 'application/x-www-form-urlencoded', 'User-Agent': 'Mozilla/5.0'})
            d = json.load(urllib.request.urlopen(req, timeout=30))
            if int(d.get('code', 0)) == 200: return d['result']
            raise RuntimeError(d)
        except Exception as e:
            print('retry', path, kw.get('pageNum'), e, file=sys.stderr); time.sleep(1.5 * (k + 1))
    raise SystemExit('failed ' + path)
PRIV = ('btcAddr', 'email', 'phone', 'mobile', 'ethAddr', 'address', 'walletAddr', 'inviteCode')
import re
EMAIL = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
def strip(o):
    if isinstance(o, dict): return {k: strip(v) for k, v in o.items() if k not in PRIV}
    if isinstance(o, list): return [strip(v) for v in o]
    if isinstance(o, str): return EMAIL.sub('[email removed]', o)        # e-mail addresses inside artist bios
    return o
artists, page = [], 1
while True:
    r = post('/rare/artist/artistList', opt='Active', pageNum=page, pageSize=5, text='')   # the page's own page size (keeps its order)
    artists += r['data']; total = int(r['total'])
    if not r['data'] or len(artists) >= total: break
    page += 1
print('artists', len(artists), 'total', total)
cap = int(sys.argv[1]) if len(sys.argv) > 1 else 10**9
works = {}
for a in artists:
    aid = a['artistId']; got, page = [], 1
    while True:
        r = post('/rare/artist/artistArtworkList', artistId=aid, id=aid, pageNum=page, pageSize=50, text='', opt='Newest')
        got += r['data']; t = int(r['total'])
        if not r['data'] or len(got) >= t or len(got) >= cap: break
        page += 1
    works[aid] = dict(total=t, data=got)
    print(a['artistName'], t, len(got), flush=True)
json.dump(strip(artists), open(os.path.join(ROOT, 'data', 'artist_list_raw.json'), 'w'), ensure_ascii=False, indent=1)
json.dump(strip(works), open(os.path.join(ROOT, 'data', 'artist_artworks_raw.json'), 'w'), ensure_ascii=False, indent=1)
