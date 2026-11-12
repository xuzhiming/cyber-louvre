"""t30u: hang the works artist by artist (artist-list order, each artist's works consecutive), packed slot after slot - no
forced new-wall start, no artist name cards - filling the slots from 1F upwards in walking order (slots.json order).
Returns placement[slot] = work index | None (empty reserved frame)."""
def place(art, slots):
    placement = [None] * len(slots); per = []; c = 0; overflow = []
    for a in art['artists']:
        idx = list(range(a['first'], a['first'] + a['n']))
        if not idx: continue
        take = idx[:max(0, len(slots) - c)]
        if len(take) < len(idx): overflow.append((a['name'], len(idx) - len(take)))
        cells = list(range(c, c + len(take)))
        for s, w in zip(cells, take): placement[s] = w
        c += len(take)
        if cells: per.append(dict(artist=a['name'], works=len(take), slots=[slots[s]['id'] for s in cells], floors=sorted(set(slots[s]['band'] for s in cells))))
    return placement, dict(slots=len(slots), used=c, empty=len(slots) - c, overflow=overflow, per_artist=per)
