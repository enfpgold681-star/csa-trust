const json = (data, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', 'Cache-Control': 'public, max-age=60' }
  });
const ADDR = /^0x[0-9a-fA-F]{40}$/;

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === '/api/health') return json({ ok: true, version: '0.1.0' });

    const m = url.pathname.match(/^\/api\/score\/(.+)$/);
    if (m) {
      const addr = m[1].toLowerCase();
      if (!ADDR.test(addr)) return json({ error: 'invalid address' }, 400);
      const row = env.SCORES ? await env.SCORES.get(addr, 'json') : null;
      return row ? json(row) : json({ address: addr, status: 'unknown' }, 404);
    }
    return env.ASSETS.fetch(request);   // ที่เหลือให้ไฟล์ static
  },
  async scheduled(event, env, ctx) { /* เฟส 2 */ }
};
