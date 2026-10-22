// 只看狗：把跟读暂停在固定位置，然后对 .kd-dog-wrap 元素截图 3 次（不同帧）
import { chromium, chromeExe } from './pw.mjs';
const b = await chromium.launch({
  executablePath: chromeExe(),
  headless: true,
});
const p = await b.newPage({ viewport: { width: 900, height: 700 }, deviceScaleFactor: 3 });
await p.goto('http://127.0.0.1:8123/test/dog_demo.html', { waitUntil: 'load' });
await p.waitForTimeout(1500);
// 冻结在某个词上，避免狗跑出画面
await p.evaluate(() => {
  const K = window.__KD, KD = K.KD;
  KD.paceCharPos = Math.floor(KD.fullText.length * 0.35);
  K.tickPace();
});
await p.waitForTimeout(120);
for (let i = 0; i < 3; i++) {
  const el = await p.$('.kd-dog-wrap');
  await el.screenshot({ path: `/tmp/frame${i}.png` });
  await p.waitForTimeout(105);
}
console.log(await p.evaluate(() => {
  const el = document.querySelector('.kd-dog-wrap');
  const r = el.getBoundingClientRect();
  return { rect: [r.x, r.y, r.width, r.height], bgPos: getComputedStyle(el.querySelector('.kd-dog')).backgroundPosition };
}));
await b.close();
