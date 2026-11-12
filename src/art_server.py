"""Local test server: serves web/ and mimics the Cloudflare Pages Function /media/rare/<hash>.<ext> (functions/media/[[path]].js)."""
import http.server, urllib.request, re, sys, os
ROOT = '/workspace/outputs/cyber_louvre/web'
class H(http.server.SimpleHTTPRequestHandler):
    def __init__(s, *a, **k): super().__init__(*a, directory=ROOT, **k)
    def log_message(s, *a): pass
    def do_GET(s):
        m = re.match(r'^/media/(rare/[A-Za-z0-9]{20,80}\.(?:jpe?g|png|gif|webp|avif))$', s.path, re.I)
        if s.path.startswith('/media/'):
            if not m: s.send_error(400); return
            try:
                r = urllib.request.urlopen(urllib.request.Request('https://image.bidder.art/' + m.group(1), headers={'User-Agent': 'Mozilla/5.0'}), timeout=60)
                b = r.read(); s.send_response(200); s.send_header('Content-Type', r.headers.get('Content-Type', 'application/octet-stream'))
                s.send_header('Access-Control-Allow-Origin', '*'); s.send_header('Content-Length', str(len(b))); s.end_headers(); s.wfile.write(b)
            except Exception as e: s.send_error(502, str(e)[:60])
            return
        return super().do_GET()
http.server.ThreadingHTTPServer(('127.0.0.1', int(sys.argv[1]) if len(sys.argv) > 1 else 8765), H).serve_forever()
