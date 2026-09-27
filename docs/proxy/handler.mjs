// The Receipt Machine's proxy: the Moth Atlas API only answers browsers on its own origin (CORS), so the
// web app talks to this instead. It forwards a WHITELIST of calls and nothing else, with the caller's own
// key (header X-Moth-Key): no server key, no credits of ours to drain, nothing logged.
//
// Runs as a Cloudflare Worker (worker.mjs) or locally under Node 18+ (server.mjs).

const API = "https://api.mothquantum.com";
const ALLOWED_ORIGINS = [
  "https://kannaka-labs.github.io",
  "http://localhost:8000",
  "http://127.0.0.1:8000",
];
const ROUTES = [
  ["GET", /^\/api\/v1\/me$/],
  ["POST", /^\/api\/v1\/engines\/comet-qrng-v1\/process$/],
  ["GET", /^\/api\/v1\/jobs\/[0-9a-f-]{36}\/(status|result)$/],
];
const LIMITS = { num_qubits: [1, 128], shots: [64, 10000], output_bytes: [1, 64] };

function cors(origin) {
  const ok = ALLOWED_ORIGINS.includes(origin);
  return {
    "Access-Control-Allow-Origin": ok ? origin : ALLOWED_ORIGINS[0],
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "X-Moth-Key, Content-Type",
    "Access-Control-Max-Age": "600",
    Vary: "Origin",
  };
}

function reply(status, body, origin) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...cors(origin) },
  });
}

export async function handle(request) {
  const origin = request.headers.get("Origin") || "";
  if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(origin) });
  const url = new URL(request.url);
  if (!ROUTES.some(([m, re]) => m === request.method && re.test(url.pathname))) {
    return reply(404, { error: "not a Receipt Machine route" }, origin);
  }
  const key = request.headers.get("X-Moth-Key") || "";
  if (!/^[A-Za-z0-9_\-.]{16,200}$/.test(key)) return reply(401, { error: "send your Moth Atlas key in X-Moth-Key" }, origin);

  let body;
  if (request.method === "POST") {
    let p;
    try {
      p = (await request.json()).params || {};
    } catch {
      return reply(400, { error: "body must be JSON {params: {...}}" }, origin);
    }
    for (const [k, [lo, hi]] of Object.entries(LIMITS)) {
      if (p[k] !== undefined && !(Number.isInteger(p[k]) && p[k] >= lo && p[k] <= hi)) {
        return reply(400, { error: `${k} must be an integer in [${lo}, ${hi}]` }, origin);
      }
    }
    if (p.mode !== undefined && !["emu", "qpu"].includes(p.mode)) return reply(400, { error: "mode is emu or qpu" }, origin);
    body = JSON.stringify({ params: p });
  }
  const upstream = await fetch(API + url.pathname, {
    method: request.method,
    headers: {
      Authorization: `Bearer ${key}`,
      "Content-Type": "application/json",
      Accept: "application/json",
      "User-Agent": "receipt-machine/1.0 (+https://github.com/kannaka-labs/ghost-signals-quantum-session)",
    },
    body,
  });
  const text = await upstream.text();
  return new Response(text, {
    status: upstream.status,
    headers: { "Content-Type": upstream.headers.get("Content-Type") || "application/json", ...cors(origin) },
  });
}
