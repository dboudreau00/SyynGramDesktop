// Contact sheet of Lottie (.tgs) animations, rendered with lottie-web in headless Chromium.
//
//   node render_tgs.mjs <out.png> <bg-hex> <frame-fraction> <file.tgs> [more.tgs ...]
//
// Needs playwright-core and lottie-web (npm i playwright-core lottie-web) and a Chromium, found via
// CHROMIUM_PATH or the Playwright cache. A development aid only: nothing here ships in the app.
import { readFileSync, existsSync, readdirSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import { createRequire } from "node:module";
import { basename } from "node:path";
import { homedir } from "node:os";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright-core");
const lottiePath = require.resolve("lottie-web/build/player/lottie.min.js");

const [out, bg, fraction, ...files] = process.argv.slice(2);
if (!out || !files.length) {
  console.error("usage: node render_tgs.mjs <out.png> <bg-hex> <frame-fraction> <files...>");
  process.exit(2);
}

function findChromium() {
  if (process.env.CHROMIUM_PATH) return process.env.CHROMIUM_PATH;
  const base = `${homedir()}/AppData/Local/ms-playwright`;
  if (existsSync(base)) {
    for (const dir of readdirSync(base)) {
      const exe = `${base}/${dir}/chrome-win64/chrome.exe`;
      if (dir.startsWith("chromium-") && existsSync(exe)) return exe;
    }
  }
  return undefined;
}

const items = files.map((f) => {
  const raw = readFileSync(f);
  const text = raw[0] === 0x1f && raw[1] === 0x8b ? gunzipSync(raw).toString("utf8") : raw.toString("utf8");
  return { name: basename(f).replace(/\.(tgs|json)$/, ""), data: JSON.parse(text) };
});

const tile = 168;
const cols = Math.min(6, items.length);
const rows = Math.ceil(items.length / cols);
const html = `<!doctype html><meta charset="utf-8"><body style="margin:0;background:${bg};font:11px Segoe UI,sans-serif;color:#888">
<div id="grid" style="display:grid;grid-template-columns:repeat(${cols},${tile}px);gap:6px;padding:8px;width:${cols * (tile + 6) + 10}px"></div>`;

const browser = await chromium.launch({ executablePath: findChromium(), headless: true });
const page = await browser.newPage({ viewport: { width: cols * (tile + 6) + 24, height: rows * (tile + 24) + 24 } });
await page.setContent(html);
await page.addScriptTag({ path: lottiePath });
await page.evaluate(({ items, tile, fraction }) => {
  const grid = document.getElementById("grid");
  for (const item of items) {
    const cell = document.createElement("div");
    const box = document.createElement("div");
    box.style.cssText = `width:${tile}px;height:${tile}px`;
    const label = document.createElement("div");
    label.textContent = item.name;
    cell.append(box, label);
    grid.append(cell);
    const anim = window.lottie.loadAnimation({ container: box, renderer: "svg", loop: false, autoplay: false, animationData: item.data });
    const frame = Math.max(0, Math.min(anim.totalFrames - 1, Math.round(anim.totalFrames * fraction)));
    anim.goToAndStop(frame, true);
  }
}, { items, tile, fraction: Number(fraction) });
await page.waitForTimeout(400);
await page.screenshot({ path: out, fullPage: true });
await browser.close();
console.log("wrote", out, `(${items.length} animations)`);
