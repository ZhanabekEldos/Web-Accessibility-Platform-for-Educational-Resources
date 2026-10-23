// Сборка фронтенда: esbuild → dist/. Запуск: `npm run build`.
import { build } from "esbuild";
import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";

export const options = (production) => ({
  entryPoints: { app: "src/main.jsx" },
  bundle: true,
  splitting: true, // страницы с lazy import() попадают в отдельные чанки
  format: "esm",
  target: "es2022", // современные браузеры (CSS light-dark() требует Chrome 123+, Firefox 120+, Safari 17.5+)
  outdir: "dist/assets",
  entryNames: production ? "[name]-[hash]" : "[name]",
  minify: production,
  sourcemap: production ? false : "inline",
  metafile: true,
  jsx: "automatic",
  loader: { ".svg": "text" },
  define: { "process.env.NODE_ENV": JSON.stringify(production ? "production" : "development") },
  logLevel: "info",
});

export async function writeIndex(metafile) {
  const outputs = Object.keys(metafile.outputs);
  const js = outputs.find((f) => metafile.outputs[f].entryPoint).replace(/^dist\//, "");
  const css = outputs.find((f) => f.endsWith(".css")).replace(/^dist\//, "");
  const html = (await readFile("index.html", "utf8")).replace("%CSS%", `/${css}`).replace("%JS%", `/${js}`);
  await writeFile("dist/index.html", html);
}

if (process.argv[1].endsWith("build.mjs")) {
  const check = process.argv.includes("--check");
  if (!check) await rm("dist", { recursive: true, force: true });
  await mkdir("dist", { recursive: true });
  const result = await build({ ...options(true), ...(check ? { outdir: "/tmp/accessedu-check", write: false } : {}) });
  if (!check) {
    await cp("public", "dist", { recursive: true });
    await writeIndex(result.metafile);
    const size = Object.values(result.metafile.outputs).reduce((n, o) => n + o.bytes, 0);
    console.log(`Готово: dist/ (${(size / 1024).toFixed(0)} КБ)`);
  }
}
