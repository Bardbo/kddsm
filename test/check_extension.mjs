// 真·扩展加载检查：把扩展装进 Chromium，直接打开 popup 页面，验证 manifest/资源/API 都正常
import { chromium, chromeExe } from './pw.mjs';
import os from 'node:os';
import path from 'node:path';
import fs from 'node:fs';

const ext = 'C:/Users/Administrator/Desktop/kddsm？';
const userDataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'kd-ext-'));
const ctx = await chromium.launchPersistentContext(userDataDir, {
  executablePath: chromeExe(),
  headless: false,
  args: [`--disable-extensions-except=${ext}`, `--load-extension=${ext}`],
  viewport: { width: 900, height: 800 },
});
let sw = ctx.serviceWorkers()[0];
if (!sw) sw = await ctx.waitForEvent('serviceworker', { timeout: 15000 });
const id = new URL(sw.url()).host;
console.log('extension id:', id);

const page = await ctx.newPage();
const errs = [];
page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()); });
page.on('pageerror', (e) => errs.push('pageerror: ' + e.message));
await page.goto(`chrome-extension://${id}/popup/popup.html`);
await page.waitForTimeout(2000);
const state = await page.evaluate(() => ({
  ver: document.getElementById('ver') && document.getElementById('ver').textContent,
  cards: document.querySelectorAll('.dog-card').length,
  count: document.getElementById('dog-count') && document.getElementById('dog-count').textContent,
  label: document.getElementById('dog-shop-label') && document.getElementById('dog-shop-label').textContent,
  brandOk: (() => { const i = document.getElementById('brand-dog'); return i && i.naturalWidth > 0; })(),
  thumbsOk: [...document.querySelectorAll('.dog-card img')].every((i) => i.naturalWidth > 0),
  state: document.getElementById('page-state') && document.getElementById('page-state').textContent,
  devToggle: !!document.getElementById('kd-dev-all'),
}));
console.log(JSON.stringify(state, null, 1));
await page.setViewportSize({ width: 380, height: 900 });
await page.screenshot({ path: '/tmp/popup_real.png', fullPage: true });

// 再验证一次：在真实扩展里跑一个普通网页，看 content script 是否注入 + 狗狗图能加载
const p2 = await ctx.newPage();
const errs2 = [];
p2.on('pageerror', (e) => errs2.push(e.message));
p2.on('response', (r) => { if (r.status() >= 400) errs2.push('HTTP ' + r.status() + ' ' + r.url()); });
await p2.goto('http://127.0.0.1:8123/test/dog_demo.html', { waitUntil: 'load' });
await p2.waitForTimeout(2500);
console.log(await p2.evaluate(() => {
  const d = document.querySelector('.kd-dog');
  return {
    injected: !!window.__KD,
    enabled: window.__KD && window.__KD.KD.state.enabled,
    tokens: window.__KD && window.__KD.KD.tokens.length,
    dog: !!document.querySelector('.kd-dog-wrap'),
    frames: d && d.style.getPropertyValue('--kd-frames'),
    bgSize: d && getComputedStyle(d).backgroundSize,
  };
}));
if (errs.length) console.log('popup errors:', errs);
if (errs2.length) console.log('page errors:', errs2.slice(0, 10));
await ctx.close();
fs.rmSync(userDataDir, { recursive: true, force: true });
