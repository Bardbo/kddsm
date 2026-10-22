// 啃读点书吗？ 后台 Service Worker v1 — 代理 LLM 校准请求（避开页面 CORS）
// 页面 fetch 会被 CORS 预检挡住（B站接口 OPTIONS 412），后台带 host_permissions 直连。
'use strict';

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type !== 'kd-llm') return;
  (async () => {
    try {
      const controller = new AbortController();          // 25s 超时：B站挂起时 SW 不能无限等待
      const timer = setTimeout(() => controller.abort(), 25000);
      const headers = { 'Content-Type': 'application/json' };
      if (msg.key) headers['Authorization'] = 'Bearer ' + msg.key;
      const res = await fetch(msg.url, {
        method: 'POST',
        headers,
        body: JSON.stringify(msg.body),
        signal: controller.signal,
      });
      clearTimeout(timer);
      const text = await res.text();
      sendResponse({ ok: res.ok, status: res.status, text });
    } catch (e) {
      sendResponse({ ok: false, error: e && e.message ? e.message : String(e) });
    }
  })();
  return true;   // 异步 sendResponse
});
