// 解析 playwright-core（本机可能只装在别的项目里，或全局装了）——避免在每个测试脚本里写死绝对路径
import fs from 'node:fs';

const CANDIDATES = [
  process.env.PW_CORE,                                            // 显式指定
  'playwright-core',                                              // 常规 npm 安装
  'file:///C:/Users/Administrator/Desktop/%E6%8E%92%E7%89%88%E5%B7%A5/node_modules/playwright-core/index.mjs',
];

let mod = null, lastErr = null;
for (const c of CANDIDATES) {
  if (!c) continue;
  try { mod = await import(c); break; } catch (e) { lastErr = e; }
}
if (!mod) throw new Error('找不到 playwright-core，请先 npm i playwright-core 或用 PW_CORE=<路径> 指定：' + (lastErr && lastErr.message));

export const chromium = mod.chromium || (mod.default && mod.default.chromium);

// Chromium 可执行文件：优先环境变量，其次 ms-playwright 里的最新版本
export function chromeExe() {
  if (process.env.CHROME_EXE) return process.env.CHROME_EXE;
  const root = (process.env.HOME || process.env.USERPROFILE || '') + '/AppData/Local/ms-playwright';
  try {
    const dirs = fs.readdirSync(root).filter((d) => d.startsWith('chromium-')).sort();
    for (const d of dirs.reverse()) {
      const p = `${root}/${d}/chrome-win64/chrome.exe`;
      if (fs.existsSync(p)) return p;
    }
  } catch (e) {}
  return 'C:/Program Files/Google/Chrome/Application/chrome.exe';
}
