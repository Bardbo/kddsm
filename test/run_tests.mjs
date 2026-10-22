// 用真实 Chromium 跑 test/ 下的回归页，把每页 #results 的结果打出来
import { chromium, chromeExe } from './pw.mjs';

const PAGES = process.argv.slice(2);
const browser = await chromium.launch({
  executablePath: chromeExe(),
  headless: true,
});
for (const p of PAGES) {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  await page.goto(`http://127.0.0.1:8123/test/${p}`, { waitUntil: 'load' });
  try {
    await page.waitForFunction(
      () => { const el = document.getElementById('results'); return el && el.textContent && el.textContent.indexOf('running') < 0; },
      { timeout: 90000 }
    );
  } catch (e) {
    console.log(`\n===== ${p} : TIMEOUT =====`);
  }
  const txt = await page.evaluate(() => (document.getElementById('results') || {}).textContent || '(no #results)');
  console.log(`\n===== ${p} =====\n${txt.trim().slice(0, 6000)}`);
  if (errors.length) console.log('--- 页面错误 ---\n' + errors.slice(0, 20).join('\n'));
  await page.close();
}
await browser.close();
