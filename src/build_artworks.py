"""t28u: web/artworks.json grouped by artist, in https://bidder.art/artist/list order.
Inputs: data/artist_list_raw.json + data/artist_artworks_raw.json (src/fetch_artists.py) and the previous normalised records
(media URLs, sizes, animated-GIF metadata, local thumbs) which are reused per artwork id / image hash."""
import json, os, collections
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
A = json.load(open(R + '/data/artist_list_raw.json')); W = json.load(open(R + '/data/artist_artworks_raw.json'))
prev = json.load(open(R + '/web/artworks.json'))
old = {w['id']: w for w in prev['artworks']}
by_img = {w.get('image_path') or w.get('image'): w for w in prev['artworks'] if w.get('image')}
IMG = 'https://image.bidder.art'
artists, works, seen, notes = [], [], set(), []
for a in A:
    aid = a['artistId']; lst = W[aid]['data']
    rec = dict(id=aid, name=a['artistName'].strip(), avatar=(IMG + a['avatar']) if a.get('avatar', '').startswith('/') else (a.get('avatar') or None),
               profile_url='https://bidder.art/artist/' + aid, works_total=int(W[aid]['total']), first=len(works), n=0)
    for r in lst:
        wid = r['artworkId']
        if wid in seen: notes.append(('duplicate', wid)); continue
        seen.add(wid)
        if wid in old: w = dict(old[wid])
        elif r.get('ipfsHash') in by_img:          # same media, re-listed under a new artwork id
            w = dict(by_img[r['ipfsHash']]); notes.append(('same_media_new_id', wid, w['id'])); w['id'] = wid
        elif int(r['type']) == 6:                  # ordinal text inscription: an RGB pixel array (28x28) -> rendered offline
            w = dict(id=wid, type=6, media='image', image=IMG + r['cover'], image_path=r['cover'], thumbnail=IMG + r['cover'],
                     local_thumb='thumbs/%s.png' % wid, width=28, height=28, aspect=1.0, source=r['ipfsHash'])
            notes.append(('type6_pixel_text_rendered', wid))
        else:
            raise SystemExit('unknown new work %s type %s - normalise it' % (wid, r['type']))
        w.update(title=r['artworkName'], artist=rec['name'], artist_id=aid, artist_url=rec['profile_url'],
                 detail_url='https://bidder.art/work/' + wid)
        works.append(w); rec['n'] += 1
    artists.append(rec)
dropped = [w['id'] for w in prev['artworks'] if w['id'] not in seen]
out = dict(source='https://api.bidder.art/rare/artist/artistList + /rare/artist/artistArtworkList', site='https://bidder.art/artist/list',
           order='artist-list order (opt=Active, as the page), each artist\'s works in profile order (opt=Newest)',
           media_base=IMG, fetched=prev.get('fetched'), count=len(works), artists=artists, artworks=works,
           notes=notes, previous_ids_not_listed=dropped)
json.dump(out, open(R + '/web/artworks.json', 'w'), ensure_ascii=False, indent=1)
print('artists', len(artists), 'with works', sum(1 for a in artists if a['n']), 'works', len(works), 'notes', notes, 'dropped', dropped)
