// 诊断：打开页面，打印 console / 异常 / KD 状态
import { chromium, chromeExe } from './pw.mjs';
const b = await chromium.launch({
  executablePath: chromeExe(),
  headless: true,
});
const p = await b.newPage();
p.on('console', (m) => console.log('[c]', m.type(), m.text()));
p.on('pageerror', (e) => console.log('[err]', e.message));
p.on('response', (r) => { if (r.status() >= 400) console.log('HTTP', r.status(), r.url()); });
await p.goto('http://127.0.0.1:8123/test/dog_demo.html', { waitUntil: 'load' });
await p.waitForTimeout(2500);
console.log(await p.evaluate(() => ({
  ready: window.__DOG_READY,
  hasKD: !!window.__KD,
  st: window.__KD && window.__KD.KD.state,
  toks: window.__KD && window.__KD.KD.tokens.length,
  txt: window.__KD && window.__KD.KD.fullText.length,
  llmErr: window.__KD && window.__KD.KD.llmError,
  dogs: document.querySelectorAll('.kd-dog-wrap').length,
})));
await b.close();
