// Cloudflare Pages Function: same-origin pass-through for bidder.art artwork media (image.bidder.art sends no CORS header,
// so WebGL cannot use those images / videos directly). Only /media/rare/<ipfs-hash>.<ext> is allowed (not an open proxy).
// Videos (mp4/webm) are streamed with HTTP Range support (206 partial content), which <video> needs to start, seek and loop.
const RE = /^rare\/[A-Za-z0-9]{20,80}\.(jpe?g|png|gif|webp|avif|mp4|m4v|webm)$/i;
const PASS = ['Content-Type', 'Content-Length', 'Content-Range', 'Accept-Ranges', 'ETag', 'Last-Modified'];
export async function onRequest({ request, params }) {
  if (request.method !== 'GET' && request.method !== 'HEAD') return new Response('method not allowed', { status: 405 });
  const path = Array.isArray(params.path) ? params.path.join('/') : String(params.path || '');
  if (!RE.test(path)) return new Response('not allowed', { status: 400 });
  const isVideo = /\.(mp4|m4v|webm)$/i.test(path);
  const fh = new Headers();
  const range = request.headers.get('Range');
  if (range) fh.set('Range', range);
  const r = await fetch('https://image.bidder.art/' + path, { method: request.method, headers: fh, cf: { cacheEverything: true, cacheTtl: 604800 } });
  const h = new Headers();
  for (const k of PASS) { const v = r.headers.get(k); if (v) h.set(k, v); }
  if (!h.get('Content-Type')) h.set('Content-Type', isVideo ? 'video/mp4' : 'application/octet-stream');
  if (isVideo && !h.get('Accept-Ranges')) h.set('Accept-Ranges', 'bytes');
  h.set('Cache-Control', 'public, max-age=604800');
  h.set('Access-Control-Allow-Origin', '*');
  h.set('Access-Control-Expose-Headers', 'Content-Length, Content-Range, Accept-Ranges');
  return new Response(request.method === 'HEAD' ? null : r.body, { status: r.status, headers: h });
}
