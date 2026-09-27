// Cloudflare Worker entry: `npx wrangler deploy docs/proxy/worker.mjs --name receipt-machine`
import { handle } from "./handler.mjs";

export default { fetch: (request) => handle(request) };
