// Режим разработки: пересборка при изменениях + сервер на :5173 с прокси /api → бэкенд (:8000).
import { context } from "esbuild";
import { cp, mkdir, readFile } from "node:fs/promises";
import { createServer, request } from "node:http";
import { extname, join, normalize } from "node:path";
import { options, writeIndex } from "./build.mjs";

const BACKEND = { host: "127.0.0.1", port: Number(process.env.BACKEND_PORT || 8000) };
const PORT = Number(process.env.PORT || 5173);
const MIME = { ".js": "text/javascript", ".css": "text/css", ".html": "text/html; charset=utf-8", ".svg": "image/svg+xml", ".json": "application/json" };

await mkdir("dist", { recursive: true });
await cp("public", "dist", { recursive: true });
const ctx = await context({
  ...options(false),
  plugins: [{ name: "index", setup: (b) => b.onEnd((r) => r.metafile && writeIndex(r.metafile)) }],
});
await ctx.watch();

createServer(async (req, res) => {
  if (req.url.startsWith("/api/")) {
    const proxied = request({ ...BACKEND, path: req.url, method: req.method, headers: req.headers }, (up) => {
      res.writeHead(up.statusCode, up.headers);
      up.pipe(res);
    });
    proxied.on("error", () => { res.writeHead(502, { "Content-Type": "application/json" }); res.end('{"error":{"code":"backend_down","message":"Бэкенд не запущен на порту ' + BACKEND.port + '"}}'); });
    req.pipe(proxied);
    return;
  }
  const path = normalize(decodeURIComponent(req.url.split("?")[0])).replace(/^(\.\.[/\\])+/, "");
  try {
    const file = await readFile(join("dist", path === "/" ? "index.html" : path));
    res.writeHead(200, { "Content-Type": MIME[extname(path)] || "application/octet-stream" });
    res.end(file);
  } catch {
    res.writeHead(200, { "Content-Type": MIME[".html"] });
    res.end(await readFile("dist/index.html")); // SPA-фолбэк
  }
}).listen(PORT, () => console.log(`Интерфейс: http://localhost:${PORT}  (API → :${BACKEND.port})`));
