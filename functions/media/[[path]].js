// Cloudflare Pages Function: same-origin pass-through for bidder.art artwork images (image.bidder.art sends no CORS
// header, so WebGL cannot use those images directly). Only /media/rare/<ipfs-hash>.<ext> is allowed (not an open proxy).
export async function onRequestGet({ params }) {
  const path = Array.isArray(params.path) ? params.path.join('/') : String(params.path || '');
  if (!/^rare\/[A-Za-z0-9]{20,80}\.(jpe?g|png|gif|webp|avif)$/i.test(path)) return new Response('not allowed', { status: 400 });
  const r = await fetch('https://image.bidder.art/' + path, { cf: { cacheEverything: true, cacheTtl: 604800 } });
  const h = new Headers();
  h.set('Content-Type', r.headers.get('Content-Type') || 'application/octet-stream');
  h.set('Cache-Control', 'public, max-age=604800');
  h.set('Access-Control-Allow-Origin', '*');
  return new Response(r.body, { status: r.status, headers: h });
}
