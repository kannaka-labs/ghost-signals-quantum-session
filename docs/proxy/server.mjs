// Local proxy + static host for the Receipt Machine (Node 18+, no dependencies):
//   node docs/proxy/server.mjs        -> app at http://localhost:8000, proxy at http://localhost:8787
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";
import { handle } from "./handler.mjs";

const PROXY_PORT = Number(process.env.PROXY_PORT || 8787);
const APP_PORT = Number(process.env.APP_PORT || 8000);
const APP_DIR = join(fileURLToPath(new URL(".", import.meta.url)), "..");

createServer(async (req, res) => {
  const chunks = [];
  for await (const c of req) chunks.push(c);
  const request = new Request(`http://localhost:${PROXY_PORT}${req.url}`, {
    method: req.method,
    headers: req.headers,
    body: ["GET", "HEAD", "OPTIONS"].includes(req.method) ? undefined : Buffer.concat(chunks),
  });
  const r = await handle(request);
  res.writeHead(r.status, Object.fromEntries(r.headers));
  res.end(Buffer.from(await r.arrayBuffer()));
}).listen(PROXY_PORT, () => console.log(`proxy  http://localhost:${PROXY_PORT}`));

const TYPES = { ".html": "text/html", ".json": "application/json", ".js": "text/javascript", ".mjs": "text/javascript", ".png": "image/png", ".css": "text/css" };
createServer(async (req, res) => {
  const path = normalize(decodeURIComponent(new URL(req.url, "http://x").pathname)).replace(/^([\\/])+/, "");
  const file = join(APP_DIR, path === "" || path === "." ? "index.html" : path);
  if (!file.startsWith(APP_DIR)) return res.writeHead(403).end();
  try {
    const data = await readFile(file);
    res.writeHead(200, { "Content-Type": TYPES[extname(file)] || "application/octet-stream" }).end(data);
  } catch {
    res.writeHead(404).end("not found");
  }
}).listen(APP_PORT, () => console.log(`app    http://localhost:${APP_PORT}`));
