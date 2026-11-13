"""t37u: per-work intro for the click-to-focus info panel.  bidder.art list APIs carry no description, so each work's public
detail (POST /rare/artwork/artworkInfo id=...) is fetched once: description, tags, curator comments (name + text).  Wallet /
e-mail / owner fields are NOT kept.  Raw subset -> data/artwork_info_raw.json; merged into web/artworks.json:
  work.intro (description), work.tags, work.curator [{name, text}], artists[].bio (public artist statement, e-mails removed)."""
import json, os, re, sys, time, urllib.request, urllib.parse
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
API = 'https://api.bidder.art/rare/artwork/artworkInfo'
EMAIL = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
PHONE = re.compile(r'(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)')
BTC = re.compile(r'\b(?:bc1[a-z0-9]{20,}|[13][a-km-zA-HJ-NP-Z1-9]{25,34}|0x[a-fA-F0-9]{40})\b')
def clean(s, n):
    s = BTC.sub('[地址已移除]', PHONE.sub('[电话已移除]', EMAIL.sub('[邮箱已移除]', str(s or '')))).replace('\r\n', '\n').strip()
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s if len(s) <= n else s[:n].rstrip() + '…'
def info(i):
    for k in range(4):
        try:
            req = urllib.request.Request(API, data=urllib.parse.urlencode({'id': i}).encode(), headers={'Content-Type': 'application/x-www-form-urlencoded', 'User-Agent': 'Mozilla/5.0'})
            d = json.load(urllib.request.urlopen(req, timeout=30))
            if int(d.get('code', 0)) == 200: return d['result']
            raise RuntimeError(str(d)[:120])
        except Exception as e:
            print('retry', i, e, file=sys.stderr); time.sleep(1.5 * (k + 1))
    return None
A = json.load(open(os.path.join(ROOT, 'web/artworks.json')))
cache_p = os.path.join(ROOT, 'data/artwork_info_raw.json')
raw = json.load(open(cache_p)) if os.path.exists(cache_p) else {}
bios = {}
for w in A['artworks']:
    if w.get('source') == 'bidder.top': continue
    if w['id'] not in raw:
        r = info(w['id']); time.sleep(0.35)
        if not r: print('FAILED', w['id']); continue
        cm = r.get('comments') or []
        raw[w['id']] = dict(description=clean(r.get('description'), 4000), tag=clean(r.get('tag'), 400),
                            comments=[dict(name=clean(c.get('name'), 40), comment=clean(c.get('comment'), 2000)) for c in cm if isinstance(c, dict) and c.get('comment')],
                            artist_id=str((r.get('creator') or {}).get('id') or ''), artist_bio=clean((r.get('creator') or {}).get('description'), 4000))
        print(w['id'], len(raw[w['id']]['description']), len(raw[w['id']]['comments']), flush=True)
    d = raw[w['id']]
    if d['description']: w['intro'] = clean(d['description'], 1200)
    else: w.pop('intro', None)
    tags = [t.strip() for t in re.split(r'[,，]', d['tag']) if t.strip()]
    if tags: w['tags'] = tags[:16]
    if d['comments']: w['curator'] = [dict(name=c['name'], text=clean(c['comment'], 700)) for c in d['comments'][:2]]
    if d['artist_bio'] and d['artist_id']: bios[d['artist_id']] = d['artist_bio']
json.dump(raw, open(cache_p, 'w'), ensure_ascii=False, indent=1)
for a in A['artists']:
    b = bios.get(str(a.get('id')))
    if b: a['bio'] = clean(b, 600)
json.dump(A, open(os.path.join(ROOT, 'web/artworks.json'), 'w'), ensure_ascii=False, indent=1)
ws = [w for w in A['artworks'] if w.get('source') != 'bidder.top']
print('works', len(ws), 'intro', sum(1 for w in ws if w.get('intro')), 'tags', sum(1 for w in ws if w.get('tags')), 'curator', sum(1 for w in ws if w.get('curator')), 'artist bios', sum(1 for a in A['artists'] if a.get('bio')))
