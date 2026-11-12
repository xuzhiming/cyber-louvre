import base64, json
r = '/workspace/outputs/cyber_louvre/'
t = open(r + 'src/web_template.html').read()
g = base64.b64encode(open(r + 'web/model_web.glb', 'rb').read()).decode()
# artworks + slots inlined (works from file:// too); web/artworks.json + web/slots.json are published alongside
A = json.load(open(r + 'web/artworks.json'))
keep = ('id', 'title', 'artist', 'media', 'detail_url', 'price', 'edition', 'compilation', 'headline', 'quote', 'image', 'image_path',
        'video', 'video_id', 'thumbnail', 'width', 'height', 'aspect', 'animated', 'frames', 'poster_frame', 'local_thumb', 'video_path', 'video_codec', 'video_local', 'text', 'text_source')
keep = keep + ('artist_id', 'artist_url')
S = json.load(open(r + 'web/slots.json'))
import sys; sys.path.insert(0, r + 'src')
from art_assign import place
placement, rep = place(A, S['slots'])
A['placement'] = placement; A['placement_report'] = rep          # kept in web/artworks.json too (published next to the page)
json.dump(A, open(r + 'web/artworks.json', 'w'), ensure_ascii=False, indent=1)
artists = [{k: a[k] for k in ('id', 'name', 'avatar', 'profile_url', 'n', 'works_total') if a.get(k) not in (None, '')} for a in A['artists']]
art = dict(source=A['source'], count=A['count'], artworks=[{k: w[k] for k in keep if w.get(k) not in (None, '')} for w in A['artworks']],
           artists=artists, placement=placement)
if rep['overflow']: print('ART OVERFLOW (no free wall face):', rep['overflow'])
slots = dict(count=S['count'], slots=[{k: s[k] for k in ('id', 'room', 'band', 'pos', 'normal', 'size', 'inner')} for s in S['slots']])
js = lambda o: json.dumps(o, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
out = t.replace('__ART_JSON__', js(art)).replace('__SLOTS_JSON__', js(slots)).replace('__GLB_BASE64__', g)
open(r + 'web/preview.html', 'w').write(out)
print(len(out))
