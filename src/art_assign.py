"""t28u/t29u: hang the works artist by artist (artist-list order), filling the slots from 1F upwards in walking order.
Each artist starts on a new wall face (2 slots per face); an odd leftover slot on the artist's last face shows the artist's
name card (avatar, name, works count, profile link).  Returns placement[slot] = work index | 'a<k>' (artist card k) | None."""
def place(art, slots):
    faces = []
    for i, s in enumerate(slots):
        key = (s['band'], s.get('face', s['room'] + str(s['normal'])))
        if not faces or faces[-1][0] != key: faces.append((key, []))
        faces[-1][1].append(i)
    placement = [None] * len(slots); fi = 0; overflow = []; per = []
    for k, a in enumerate(art['artists']):
        idx = list(range(a['first'], a['first'] + a['n']))
        if not idx: continue
        need = -(-len(idx) // 2)
        if fi + need > len(faces):
            overflow.append((a['name'], len(idx))); continue
        cells = [c for f in faces[fi:fi + need] for c in f[1]]
        for c, w in zip(cells, idx): placement[c] = w
        rest = cells[len(idx):]
        if rest: placement[rest[0]] = 'a%d' % k
        floors = sorted(set(slots[c]['band'] for c in cells[:len(idx)]))
        per.append(dict(artist=a['name'], works=len(idx), slots=[slots[c]['id'] for c in cells[:len(idx)]], floors=floors))
        fi += need
    return placement, dict(faces=len(faces), faces_used=fi, overflow=overflow, per_artist=per)
