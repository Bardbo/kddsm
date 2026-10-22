// 啃读点书吗？ popup v1.0 — 页面状态实时同步 + 跟读暂停/重读 + AI 校准状态机
'use strict';

const DOGS = [
  { id: 'dalmatian', name: '斑点狗' },
  { id: 'corgi', name: '柯基' },
  { id: 'shiba', name: '柴犬' },
  { id: 'frenchy', name: '法斗' },
  { id: 'bichon', name: '比熊' },
  { id: 'golden', name: '金毛' },
  { id: 'collie', name: '边牧' },
  { id: 'samoyed', name: '萨摩耶' },
  { id: 'husky', name: '哈士奇' },
  { id: 'dachshund', name: '腊肠' },
  { id: 'schnauzer', name: '雪纳瑞' },
  { id: 'rottweiler', name: '罗威纳' },
  { id: 'tibetan', name: '藏獒' },
  { id: 'shepherd', name: '德牧' },
  { id: 'poodle', name: '贵宾' },
];
const PRICE = 100, DAILY_CAP = 60;

// 彩蛋口令：在「Key（可选）」里输入这一串即可解锁全部品种。不写进 UI、不做任何提示。
const UNLOCK_CODE = '体验全开';

let coins = { total: 0, daily: 0, date: '', activeSec: 0, lastSignDate: '' };
let owned = new Set(['dalmatian']);
let selected = 'dalmatian';
let auto = true;
let mode = 'hl';
let devAll = false;              // 体验权限（全部品种开放）：默认关闭，只能靠口令解锁
let initChoiceDone = false;      // 初始选狗引导是否完成（新装未完成 → 任选一只初始狗狗）
let colors = { hex: '#FFB800', a: 0.85 };     // 渐变：最深色 + 最深透明度，其余按分数渐变得来
let llmCfg = { enabled: true, baseUrl: 'https://index-translate.bilibili.com/v1', model: 'Index-Translate-35B-A3B', apiKey: '', skipSensitive: true };
let hideEaten = false;
let wpm = 300;
let dogSig = '';
let polling = false;
// 当前标签页的真实状态（由 content script 的 kd-state 回填；popup 自己不再猜）
let page = { enabled: false, pace: false, finished: false, percent: 0, llm: null, model: null, offline: false };

const $ = (id) => document.getElementById(id);
const setText = (id, v) => { const el = $(id); if (el) el.textContent = v; };
const setVal = (id, v) => { const el = $(id); if (el) el.value = v; };
const setChk = (id, v) => { const el = $(id); if (el) el.checked = !!v; };
// 元素可能不存在（HTML 改版 / 测试页旧结构）→ 统一守卫，绝不让一行 null.addEventListener 掐断后面所有绑定
const on = (id, ev, fn) => { const el = $(id); if (el) el.addEventListener(ev, fn); };

// 本地日期（必须用本地时区：toISOString 是 UTC，国内每天 08:00 前会被算成前一天 → 签到/日上限错乱）
function todayStr() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

// 肖像：AI 生成（thumbs）
const portrait = (id) => chrome.runtime.getURL(`assets/dogs-ai/thumbs/${id}_thumb.png`);

async function getActiveTab() {
  // 旧写法 `const [tab] = await chrome.tabs.query(...)` 在拿不到活动页时 tab 是 undefined，
  // 下游一读 tab.id 就是 "Cannot read properties of undefined (reading 'id')" —— 这里统一兜住
  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    return (Array.isArray(tabs) && tabs.length) ? tabs[0] : null;
  } catch (e) {
    console.error('[啃读] 读取活动标签页失败：', e);
    return null;
  }
}
async function send(tab, msg) {
  // MV3 扩展页面 CSP 禁内联事件处理器——所有交互一律走 addEventListener（勿用 onclick 属性）
  if (!tab || typeof tab.id !== 'number') return null;
  try { return await chrome.tabs.sendMessage(tab.id, msg); } catch (e) { return null; }
}

function flashState(text) {
  const el = $('page-state');
  if (!el) return;
  el.textContent = text;
  el.classList.add('warn');
  clearTimeout(flashState._t);
  flashState._t = setTimeout(() => el.classList.remove('warn'), 2000);
}

async function load() {
  try {
    const data = await chrome.storage.local.get(['kdCoins', 'kdDogs', 'kdAuto', 'kdDog', 'kdMode', 'kdColors', 'kdLlmCfg', 'kdPrefs', 'kdEaten', 'kdTrial']);
    if (data.kdCoins) coins = { ...coins, ...data.kdCoins };
    // 体验权限只看独立开关 kdTrial：老版本把 devAll 存进 kdDogs，这里不再采信 → 存量用户也回到正常的解锁流程
    devAll = !!(data.kdTrial && data.kdTrial.unlocked);
    if (data.kdDogs && Array.isArray(data.kdDogs.owned)) {
      owned = new Set(data.kdDogs.owned);
      initChoiceDone = owned.size > 0;
    }
    if (data.kdDog && DOGS.some(d => d.id === data.kdDog)) selected = data.kdDog;
    if (data.kdAuto !== undefined) auto = data.kdAuto;
    if (data.kdMode === 'pace') mode = 'pace';
    if (data.kdColors) {
      if (data.kdColors.hex) colors = { hex: data.kdColors.hex, a: data.kdColors.a ?? 0.85 };
      else if (data.kdColors.t1) colors = { hex: data.kdColors.t1.hex || '#FFB800', a: data.kdColors.t1.a || 0.85 };  // 旧三档配置兼容
    }
    if (data.kdLlmCfg) llmCfg = { ...llmCfg, ...data.kdLlmCfg };
    if (data.kdPrefs && data.kdPrefs.speedCps) wpm = Math.round(data.kdPrefs.speedCps * 60);
    hideEaten = !!(data.kdEaten && data.kdEaten.hide);

    setVal('c-t1', colors.hex);
    setVal('a-t1', colors.a);
    setChk('kd-eaten', hideEaten);
    setChk('llm-enable', llmCfg.enabled);
    setVal('llm-url', llmCfg.baseUrl || '');
    setVal('llm-model', llmCfg.model || '');
    setVal('llm-key', llmCfg.apiKey || '');
    setChk('llm-safe', llmCfg.skipSensitive !== false);
    setVal('speed', wpm);
    setText('wpm-val', wpm);
    const brand = $('brand-dog');
    if (brand) brand.src = portrait(selected);
    setChk('kd-auto', auto);
    // 版本号：一眼看出"跑的是不是新代码"（老版本不重载扩展就会看不到这个号）
    try {
      const mf = chrome.runtime.getManifest && chrome.runtime.getManifest();
      setText('ver', mf && mf.version ? 'v' + mf.version : '');
    } catch (e) { setText('ver', ''); }
    updateChip();
    render();
    await refreshState();     // 打开即同步本页真实状态（原来永远显示"未启用"）
    setInterval(refreshState, 1500);   // 跟读进度 / 校准状态 / 币数实时刷新
  } catch (e) {
    // 原来这里静默吞掉异常（狗舍整块消失都没人知道）→ 至少留痕，方便定位
    console.error('[啃读] popup 初始化失败：', e);
    try { flashState('面板加载异常（详见控制台）'); } catch (_) {}
  }
}

async function refreshState() {
  if (polling) return;        // 上一轮还没回来（页面卡住/慢）→ 不叠加，避免消息堆积
  polling = true;
  try {
    const tab = await getActiveTab();
    const res = await send(tab, { type: 'kd-state' });
    if (res) {
      page = res;
      if (res.coins) coins = { ...coins, ...res.coins };
      if (res.pace) mode = 'pace';
    } else {
      // 页面没注入 content script（chrome:// / 商店页 / 刚装未刷新）→ 至少把币显示对
      page = { enabled: false, pace: false, finished: false, percent: 0, llm: null, model: null, offline: true };
      try { const d = await chrome.storage.local.get('kdCoins'); if (d.kdCoins) coins = { ...coins, ...d.kdCoins }; } catch (e) {}
    }
    render();
  } finally {
    polling = false;
  }
}

// '#RRGGBB' → 'r, g, b'（非法值回退琥珀，别让 NaN 写进样式）
function rgbOf(hex) {
  const h = String(hex || '');
  const m = /^#?([0-9a-f]{6})$/i.exec(h.trim());
  if (!m) return '255, 176, 0';
  const n = parseInt(m[1], 16);
  return `${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}`;
}
function updateChip() {
  const c = $('chip-grad');
  if (c) c.style.background = `rgba(${rgbOf(colors.hex)}, ${colors.a})`;
}

function llmText() {
  const l = page.llm;
  if (!l) return { text: page.offline ? '本页未连接扩展（刷新页面试试）' : '—', cls: 'off' };
  if (!l.enabled) return { text: '已关闭（只用本地打分）', cls: 'off' };
  if (l.state === 'running') return { text: '校准中… 等模型返回（最长约 40 秒）', cls: 'busy' };
  if (l.state === 'ok' && l.stats) {
    return { text: `✅ ${l.stats.phrases} 个信息点 · 命中 ${l.stats.tokens} 词${l.stats.cached ? '（本地缓存）' : ''}`, cls: 'ok' };
  }
  if (l.state === 'skip') return { text: '⏭ ' + (l.error || '已跳过'), cls: 'off' };
  if (l.state === 'fail') return { text: '⚠ ' + (l.error || '校准失败'), cls: 'fail' };
  if (!page.enabled) return { text: '本页未启用', cls: 'off' };
  return { text: '⏳ 等待模型就绪…', cls: 'busy' };
}

function render() {
  // 所有元素都做空值保护：以前一个 span 被 textContent 抹掉 → 下一行 null 抛错 → 整个面板空白
  const toggleHidden = (id, hidden) => { const el = $(id); if (el) el.classList.toggle('hidden', hidden); };

  setText('coin-balance', coins.total);

  // 本页状态：区分"已高亮 / 跟读中 / 已读完 / 未连接"
  let stateText;
  if (page.offline) stateText = '本页无法注入（刷新或换个网页）';
  else if (!page.enabled) stateText = '本页未启用';
  else if (page.pace) stateText = `跟读中 · ${page.percent || 0}%`;
  else if (page.finished) stateText = '已读完';
  else stateText = '本页已高亮';
  const ps = $('page-state');
  if (ps && !ps.classList.contains('warn')) ps.textContent = stateText;
  const stateDot = $('state-dot');
  if (stateDot) {
    stateDot.className = 'dot' + (page.offline ? ' off' : page.enabled ? (page.pace ? ' live' : ' on') : ' off');
  }

  const btn = $('toggle');
  if (btn) {
    btn.textContent = page.enabled ? '关闭高亮' : '开启高亮';
    btn.classList.toggle('off', !page.enabled);
  }

  document.querySelectorAll('.seg-btn').forEach(b => b.classList.toggle('active', b.dataset.mode === mode));
  toggleHidden('speed-wrap', mode !== 'pace');
  toggleHidden('pace-controls', mode !== 'pace');
  toggleHidden('pace-bar', mode !== 'pace');
  const pct = page.enabled ? (page.percent || 0) : 0;
  const fill = $('pace-fill');
  if (fill) fill.style.width = pct + '%';
  const pbtn = $('pace-btn');
  if (pbtn) {
    if (!page.enabled) pbtn.textContent = '开始跟读';
    else if (page.pace) pbtn.textContent = '暂停';
    else if (page.finished) pbtn.textContent = '重新开始';
    else pbtn.textContent = '继续';
  }
  setText('pace-text', page.enabled
    ? (page.pace ? `${pct}% · 读 ${page.pos || 0}/${page.total || 0} 字` : page.finished ? '读完啦' : `已停在 ${pct}%`)
    : '—');

  // 签到状态
  const today = todayStr();
  const signed = coins.lastSignDate === today;
  const signBtn = $('sign-btn');
  if (signBtn) {
    signBtn.disabled = signed;
    signBtn.textContent = signed ? '今日已签到 ✓' : '签到领 🦴5';
  }
  setText('sign-state', signed ? `今日已读 ${coins.daily || 0}/${DAILY_CAP} 分钟` : (coins.daily ? `今日已阅读 ${coins.daily}/${DAILY_CAP} 分钟` : ''));

  const lt = llmText();
  const st = $('llm-status');
  if (st) { st.textContent = lt.text; st.className = 'llm-st ' + lt.cls; }
  const fs = $('llm-fold-state');       // 折叠标题上带一眼可辨的开关状态
  // 页面没注入 content script（page.llm 为空）时退回本地配置，别让徽标空着
  if (fs) fs.textContent = ((page.llm ? page.llm.enabled : llmCfg.enabled) ? '开' : '关');

  try { renderDogs(); } catch (e) { console.error('[啃读] 狗舍渲染失败：', e); }
}

function renderDogs() {
  const initing = !initChoiceDone;
  const sig = [initing, devAll, selected, [...owned].sort().join(',')].join('|');
  // 标题里还有"已拥有数"这个 span：#dog-shop-title 不能直接写 textContent（会把 span 一起抹掉，
  // 下一行 getElementById('dog-count') 就取到 null 并抛错 → 狗舍整块卡片建不出来）
  const ttl = $('dog-shop-label');
  const hint = $('dog-shop-hint');
  if (ttl) ttl.textContent = initing ? '选一只你的初始狗狗' : '狗舍';
  if (hint) {
    hint.textContent = initing ? '点任意一只，它就是你的初始陪伴犬（免费）'
      : devAll ? '全部品种已开放' : '';
  }
  let count = 0;
  for (const d of DOGS) if (devAll || owned.has(d.id)) count++;
  const cntEl = $('dog-count');
  if (cntEl) cntEl.textContent = initing ? '15 选 1' : `${count}/${DOGS.length}`;
  if (sig === dogSig) return;      // 状态没变就不重建（原实现每 5 秒重建整张图，图片会闪）
  dogSig = sig;

  const list = $('dog-list');
  if (!list) return;
  list.innerHTML = '';
  for (const d of DOGS) {
    const isOwned = devAll || owned.has(d.id);
    const card = document.createElement('div');
    // 初始选择阶段 15 只都是免费可选 → 不能显示成上锁灰态（新装一打开像全被锁住）
    card.className = 'dog-card' + ((!initing && !isOwned) ? ' locked' : '') + (d.id === selected ? ' selected' : '');
    card.setAttribute('role', 'button');
    card.setAttribute('tabindex', '0');
    card.title = d.name + (isOwned || initing ? '' : ` · ${PRICE} 🦴 解锁`);
    card.innerHTML = `<span class="img"><img src="${portrait(d.id)}" alt="${d.name}" loading="lazy"></span>` +
      `<span class="name">${d.name}</span>` +
      (isOwned || initing ? '' : `<span class="price">🦴${PRICE}</span>`) +
      (isOwned || initing ? '' : '<span class="lock">🔒</span>');
    const pick = safe('选狗', async () => {
      if (initing) {
        // 初始选择：免费获得该狗并设为当前
        owned = new Set([d.id]);
        selected = d.id;
        initChoiceDone = true;
        await chrome.storage.local.set({ kdDog: selected, kdDogs: { owned: [...owned] } });
        if ($('brand-dog')) $('brand-dog').src = portrait(selected);
        const tab = await getActiveTab();
        await send(tab, { type: 'kd-set-dog', breed: selected });
        render();
        return;
      }
      if (!isOwned) {
        if (coins.total >= PRICE) {
          coins.total -= PRICE;
          owned.add(d.id);
          selected = d.id;
          await chrome.storage.local.set({ kdCoins: coins, kdDog: selected, kdDogs: { owned: [...owned] } });
          if ($('brand-dog')) $('brand-dog').src = portrait(selected);
          const tab = await getActiveTab();
          await send(tab, { type: 'kd-set-dog', breed: selected });
          render();
        } else {
          card.classList.add('deny');
          setTimeout(() => card.classList.remove('deny'), 600);
        }
        return;
      }
      selected = d.id;
      await chrome.storage.local.set({ kdDog: selected });
      if ($('brand-dog')) $('brand-dog').src = portrait(selected);
      const tab = await getActiveTab();
      await send(tab, { type: 'kd-set-dog', breed: selected });
      render();
    });
    card.addEventListener('click', pick);
    card.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick(); } });
    list.appendChild(card);
  }
}

// 注意：不要把 <input type=checkbox> 放进 <summary> 里再用 preventDefault 阻止折叠——
// preventDefault 会连勾选框自己的"默认动作"一起取消，结果是开关点不动（旧实现就这么坏的）。
// 结构上把开关移出 summary，勾选和折叠互不干扰。

// 统一兜底：任何异步错误都不许变成控制台里一句看不懂的 "Uncaught (in promise) Error: ..."，
// 一律变成面板上可见的一行提示 + 可定位的日志。
function safe(tag, fn) {
  return async (...args) => {
    try {
      return await fn(...args);
    } catch (e) {
      console.error('[啃读] popup ' + tag + ' 出错：', e);
      try { flashState('操作失败：' + ((e && e.message) || e)); } catch (_) {}
    }
  };
}
window.addEventListener('unhandledrejection', (e) => {
  console.error('[啃读] popup 未处理的异步错误：', e.reason);
  try { flashState('操作失败：' + ((e.reason && e.reason.message) || e.reason || '未知错误')); } catch (_) {}
});
window.addEventListener('error', (e) => console.error('[啃读] popup 脚本错误：', e.error || e.message));

// 签到：每日一次 +5 🦴
on('sign-btn', 'click', safe('签到', async () => {
  const today = todayStr();
  if (coins.lastSignDate === today) return;
  coins.total += 5;
  coins.lastSignDate = today;
  await chrome.storage.local.set({ kdCoins: coins });
  render();
}));

// 恢复默认颜色（琥珀 + 0.85）并即时应用到当前页
on('color-reset', 'click', safe('恢复默认颜色', () => {
  colors = { hex: '#FFB800', a: 0.85 };
  setVal('c-t1', colors.hex);
  setVal('a-t1', colors.a);
  chrome.storage.local.set({ kdColors: colors });
  updateChip();
  return getActiveTab().then(t => send(t, { type: 'kd-colors', colors: { grad: colors } }));
}));

// 高亮颜色：一个颜色 + 一个透明度 → 保存并即时应用（所有词按分值映射 0 → 该颜色）
function colorChanged() {
  const hex = ($('c-t1') && $('c-t1').value) || colors.hex;
  const rawA = $('a-t1') ? Number($('a-t1').value) : colors.a;
  const a = Number.isFinite(rawA) ? Math.min(1, Math.max(0, rawA)) : 0.85;
  colors = { hex, a };
  chrome.storage.local.set({ kdColors: colors });
  updateChip();
  getActiveTab().then(t => send(t, { type: 'kd-colors', colors: { grad: colors } }));
}
['c-t1', 'a-t1'].forEach(id => on(id, 'input', colorChanged));

// 已读样式：淡出（默认）↔ 完全隐藏
on('kd-eaten', 'change', safe('已读样式', (e) => {
  hideEaten = e.target.checked;
  chrome.storage.local.set({ kdEaten: { hide: hideEaten } });
  return getActiveTab().then(t => send(t, { type: 'kd-eaten', hide: hideEaten }));
}));

// AI 校准开关：即时生效（开→当前页补加成；关→回退到本地 BERT+静态基线）
on('llm-enable', 'change', safe('AI 校准开关', async () => {
  llmCfg.enabled = $('llm-enable').checked;
  await chrome.storage.local.set({ kdLlmCfg: llmCfg });
  const tab = await getActiveTab();
  await send(tab, { type: 'kd-llm-toggle', enabled: llmCfg.enabled });
  await refreshState();
}));

// 彩蛋：在 Key 里输入口令解锁全部品种（不保存为 Key、不改其它配置、不弹任何说明）
async function tryUnlockByCode() {
  const el = $('llm-key');
  const raw = el ? el.value.trim() : '';
  if (raw !== UNLOCK_CODE) return false;
  if (el) el.value = llmCfg.apiKey || '';       // 口令绝不能当成 Key 存下去
  if (!devAll) {
    devAll = true;
    await chrome.storage.local.set({ kdTrial: { unlocked: true, at: Date.now() } });
    dogSig = '';                                 // 强制重建一次狗舍
    render();
    flashState('🐾 全部品种已开放');
  } else {
    flashState('🐾 全部品种已开放');
  }
  return true;
}

// 配置项（地址/模型/Key/隐私）：保存并即时下发到当前页（不用刷新页面）
['llm-url', 'llm-model', 'llm-key'].forEach(id =>
  on(id, 'change', safe('AI 配置', async () => {
    if (id === 'llm-key' && await tryUnlockByCode()) return;
    llmCfg = {
      ...llmCfg,
      enabled: $('llm-enable') ? $('llm-enable').checked : llmCfg.enabled,
      baseUrl: ($('llm-url') ? $('llm-url').value : '').trim().replace(/\/+$/, ''),
      model: ($('llm-model') ? $('llm-model').value : '').trim(),
      apiKey: ($('llm-key') ? $('llm-key').value : '').trim(),
      skipSensitive: $('llm-safe') ? $('llm-safe').checked : llmCfg.skipSensitive,
    };
    await chrome.storage.local.set({ kdLlmCfg: llmCfg });
    const tab = await getActiveTab();
    await send(tab, { type: 'kd-llm-cfg', cfg: llmCfg });
  })));

on('llm-safe', 'change', safe('隐私开关', async (e) => {
  llmCfg.skipSensitive = e.target.checked;
  await chrome.storage.local.set({ kdLlmCfg: llmCfg });
  const tab = await getActiveTab();
  await send(tab, { type: 'kd-llm-cfg', cfg: llmCfg });
}));

// 立即校准当前页：页面没开就先开；状态由轮询回显（不再"点了没反应"）
on('llm-now', 'click', safe('立即校准', async () => {
  const btn = $('llm-now');
  if (btn) btn.disabled = true;
  try {
    const tab = await getActiveTab();
    const res = await send(tab, { type: 'kd-llm-now' });
    if (!res) { flashState('本页不支持（扩展未注入）'); return; }
    if (!res.ok) flashState(res.reason || '启动失败');
    await refreshState();
  } finally { if (btn) btn.disabled = false; }
}));

on('toggle', 'click', safe('开关高亮', async () => {
  const tab = await getActiveTab();
  const res = await send(tab, { type: 'kd-toggle', enabled: !page.enabled });
  if (!res) { flashState('本页不支持（换个普通网页试试）'); return; }
  await refreshState();
}));

on('kd-auto', 'change', safe('自动高亮开关', async (e) => {
  auto = e.target.checked;
  await chrome.storage.local.set({ kdAuto: auto });
}));

document.querySelectorAll('.seg-btn').forEach(b => b.addEventListener('click', safe('切换模式', async () => {
  mode = b.dataset.mode;
  await chrome.storage.local.set({ kdMode: mode });
  render();
  const tab = await getActiveTab();
  if (mode === 'pace') {
    const res = await send(tab, { type: 'kd-pace', action: 'start', speedCps: wpm / 60 });
    if (!res) flashState('本页不支持（扩展未注入，或这里没有正文）');
  } else {
    const res = await send(tab, { type: 'kd-pace', action: 'pause' });
    if (!res) flashState('本页不支持（扩展未注入）');
  }
  setTimeout(refreshState, 250);
})));

// 跟读主控：开始/暂停/继续/重新开始 一键切换（原来只能靠切换模式来停）
on('pace-btn', 'click', safe('跟读控制', async () => {
  const action = !page.enabled ? 'start' : page.pace ? 'pause' : page.finished ? 'restart' : 'start';
  const tab = await getActiveTab();
  const res = await send(tab, { type: 'kd-pace', action, speedCps: wpm / 60 });
  if (!res) flashState('本页不支持（扩展未注入，或这里没有正文）');
  await refreshState();
}));
on('restart-btn', 'click', safe('重读', async () => {
  const tab = await getActiveTab();
  const res = await send(tab, { type: 'kd-pace', action: 'restart', speedCps: wpm / 60 });
  if (!res) flashState('本页不支持（扩展未注入，或这里没有正文）');
  await refreshState();
}));

// 调速：拖动时 UI 立即跟手，写入/下发做 120ms 防抖（原来每移动 1px 就写一次 storage + 发一次消息）
let speedTimer = null;
on('speed', 'input', (e) => {
  wpm = +e.target.value;
  setText('wpm-val', wpm);
  const cps = wpm / 60;
  clearTimeout(speedTimer);
  speedTimer = setTimeout(() => {
    chrome.storage.local.set({ kdPrefs: { speedCps: cps } });
    getActiveTab().then(t => send(t, { type: 'kd-speed', speedCps: cps }));
  }, 120);
});

load();
