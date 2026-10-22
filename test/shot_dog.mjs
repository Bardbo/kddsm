// 视觉检查：截 dog_demo 页（跟读进行中），存到 /tmp 供人工看
import { chromium, chromeExe } from './pw.mjs';
const browser = await chromium.launch({
  executablePath: chromeExe(),
  headless: true,
  args: ['--force-device-scale-factor=2'],
});
const page = await browser.newPage({ viewport: { width: 900, height: 700 }, deviceScaleFactor: 2 });
page.on('pageerror', (e) => console.log('pageerror:', e.message));
page.on('requestfailed', (r) => console.log('reqfail:', r.url()));
page.on('response', (r) => { if (r.status() >= 400) console.log('HTTP', r.status(), r.url()); });
await page.goto('http://127.0.0.1:8123/test/dog_demo.html', { waitUntil: 'load' });
await page.waitForTimeout(1800);
await page.screenshot({ path: '/tmp/dog1.png' });
await page.waitForTimeout(400);
await page.screenshot({ path: '/tmp/dog2.png' });
const info = await page.evaluate(() => {
  const d = document.querySelector('.kd-dog');
  const w = document.querySelector('.kd-dog-wrap');
  return {
    hasDog: !!d,
    frames: d && d.style.getPropertyValue('--kd-frames'),
    bg: d && d.style.backgroundImage,
    bgSize: d && getComputedStyle(d).backgroundSize,
    animation: d && getComputedStyle(d).animationName,
    wrapTransform: w && w.style.transform,
    eaten: document.querySelectorAll('.kd-eaten').length,
  };
});
console.log(JSON.stringify(info, null, 1));
await browser.close();
