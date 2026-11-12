"""Local test server: serves web/ (with HTTP Range for files, like Cloudflare Pages) and mimics the Pages Function
/media/rare/<hash>.<ext> (functions/media/[[path]].js), incl. Range pass-through for mp4/webm."""
import http.server, urllib.request, urllib.error, re, sys, os, shutil
ROOT = '/workspace/outputs/cyber_louvre/web'
MEDIA = re.compile(r'^/media/(rare/[A-Za-z0-9]{20,80}\.(?:jpe?g|png|gif|webp|avif|mp4|m4v|webm|mp3|m4a|aac|ogg|oga|opus|wav|flac))$', re.I)
class H(http.server.SimpleHTTPRequestHandler):
    def __init__(s, *a, **k): super().__init__(*a, directory=ROOT, **k)
    def log_message(s, *a): pass
    def _media(s, m):
        hd = {'User-Agent': 'Mozilla/5.0'}
        if s.headers.get('Range'): hd['Range'] = s.headers['Range']
        try:
            r = urllib.request.urlopen(urllib.request.Request('https://image.bidder.art/' + m.group(1), headers=hd), timeout=60)
        except urllib.error.HTTPError as e: r = e
        except Exception as e: s.send_error(502, str(e)[:60]); return
        s.send_response(r.status)
        for k in ('Content-Type', 'Content-Length', 'Content-Range', 'Accept-Ranges'):
            if r.headers.get(k): s.send_header(k, r.headers[k])
        s.send_header('Access-Control-Allow-Origin', '*'); s.end_headers()
        try: shutil.copyfileobj(r, s.wfile, 1 << 16)
        except (BrokenPipeError, ConnectionResetError): pass
    def _range_file(s):
        p = s.translate_path(s.path.split('?')[0]); rg = s.headers.get('Range')
        if not rg or not os.path.isfile(p): return False
        m = re.match(r'bytes=(\d*)-(\d*)', rg); n = os.path.getsize(p)
        if not m: return False
        a = int(m.group(1)) if m.group(1) else max(0, n - int(m.group(2))); b = int(m.group(2)) if m.group(1) and m.group(2) else n - 1
        b = min(b, n - 1)
        s.send_response(206); s.send_header('Content-Type', s.guess_type(p)); s.send_header('Accept-Ranges', 'bytes')
        s.send_header('Content-Range', 'bytes %d-%d/%d' % (a, b, n)); s.send_header('Content-Length', str(b - a + 1)); s.end_headers()
        with open(p, 'rb') as f:
            f.seek(a); left = b - a + 1
            try:
                while left > 0:
                    c = f.read(min(1 << 16, left));
                    if not c: break
                    s.wfile.write(c); left -= len(c)
            except (BrokenPipeError, ConnectionResetError): pass
        return True
    def do_GET(s):
        if s.path.startswith('/media/'):
            m = MEDIA.match(s.path)
            if not m: s.send_error(400); return
            return s._media(m)
        if s._range_file(): return
        return super().do_GET()
http.server.ThreadingHTTPServer(('127.0.0.1', int(sys.argv[1]) if len(sys.argv) > 1 else 8765), H).serve_forever()
