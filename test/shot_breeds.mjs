// 视觉验收：把 6 个品种依次放到页面上，各截一张 64px 实图（3x DPR），拼成一张对比图
import { chromium, chromeExe } from './pw.mjs';
const breeds = ['dalmatian', 'corgi', 'shiba', 'husky', 'samoyed', 'golden'];
const b = await chromium.launch({
  executablePath: chromeExe(),
  headless: true,
});
const p = await b.newPage({ viewport: { width: 900, height: 700 }, deviceScaleFactor: 3 });
await p.goto('http://127.0.0.1:8123/test/dog_demo.html', { waitUntil: 'load' });
await p.waitForTimeout(1400);
await p.evaluate(() => {
  const K = window.__KD, KD = K.KD;
  KD.paceCharPos = Math.floor(KD.fullText.length * 0.4);
  K.tickPace();
});
for (const br of breeds) {
  await p.evaluate((x) => window.__KD.setDogSprite(x, 'run'), br);
  await p.waitForTimeout(250);
  const el = await p.$('.kd-dog-wrap');
  await el.screenshot({ path: `/tmp/b_${br}.png` });
}
// 跳跃态
await p.evaluate(() => window.__KD.setDogSprite('dalmatian', 'jump'));
await p.waitForTimeout(140);
await (await p.$('.kd-dog-wrap')).screenshot({ path: '/tmp/b_jump.png' });
await b.close();
console.log('done');
