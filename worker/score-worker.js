// 啃读点书吗？ 打分 Worker v0.5 — tiny Chinese BERT (int8 ONNX) 双信号语义打分
// ① keybert：词嵌入 vs 全文均值嵌入 的余弦（主题代表性）
// ② distinct：词嵌入 vs 左右窗口上下文均值 的余弦距离（contextual distinctiveness ≈ 意外度，信息量核心信号）
'use strict';

importScripts('vendor/ort.min.js');   // 相对 worker 脚本目录

let session = null, vocab = null, cfg = null;
let base = '';
const SPECIAL = { cls: 101, sep: 102, unk: 100, pad: 0 };

async function loadModel() {
  try {
    const [modelBuf, cfgJson, vocabTxt] = await Promise.all([
      fetch(base + 'assets/model/model_int8.onnx').then(r => r.arrayBuffer()),
      fetch(base + 'assets/model/config.json').then(r => r.json()),
      fetch(base + 'assets/model/vocab.txt').then(r => r.text()),
    ]);
    cfg = cfgJson;
    vocab = new Map();
    vocabTxt.split('\n').forEach((w, i) => { if (w.trim() !== '') vocab.set(w.trim(), i); });
    // 特殊 token id 以 vocab 实际值为准
    SPECIAL.cls = vocab.get('[CLS]') ?? 101;
    SPECIAL.sep = vocab.get('[SEP]') ?? 102;
    SPECIAL.unk = vocab.get('[UNK]') ?? 100;
    // wasm 路径 = 本 worker 目录 + vendor/
    const dir = self.location.href.slice(0, self.location.href.lastIndexOf('/')) + '/vendor/';
    ort.env.wasm.wasmPaths = dir;
    ort.env.wasm.numThreads = 1;
    session = await ort.InferenceSession.create(modelBuf, {
      executionProviders: ['wasm'],
      graphOptimizationLevel: 'all',
    });
    return true;
  } catch (e) {
    self.postMessage({ type: 'log', msg: 'model load fail: ' + e.message });
    return false;
  }
}

// ---------------- BERT 中文分词（单字为主，ASCII 整词尝试；带字符偏移） ----------------
function tokenize(text) {
  const ids = [], starts = [], ends = [];
  let i = 0;
  const isAscii = c => /[A-Za-z0-9]/.test(c);
  while (i < text.length) {
    const ch = text[i];
    if (isAscii(ch)) {
      let j = i;
      while (j < text.length && isAscii(text[j])) j++;
      const run = text.slice(i, j);
      let k = run.length, wid = -1;
      while (k > 0 && wid < 0) { wid = vocab.get(run.slice(0, k)) ?? -1; if (wid < 0) k--; }
      if (wid < 0) { ids.push(SPECIAL.unk); starts.push(i); ends.push(i + 1); i++; }
      else { ids.push(wid); starts.push(i); ends.push(i + k); i += k; }
    } else {
      ids.push(vocab.get(ch) ?? SPECIAL.unk);
      starts.push(i); ends.push(i + 1); i++;
    }
  }
  if (ids.length > 510) { ids.length = 510; starts.length = 510; ends.length = 510; }
  return {
    ids: [SPECIAL.cls, ...ids, SPECIAL.sep],
    starts: [0, ...starts, text.length],
    ends: [0, ...ends, text.length],
    n: ids.length + 2,
  };
}

// ---------------- 推理 + 双信号打分 ----------------
const CTX_WIN = 12;   // 上下文窗口（左右各 N 个词）
async function score(text, tokens) {
  if (!session) return { scores: null, distinct: null, note: 'no-model' };
  const t = tokenize(text);
  const n = t.n;
  const input_ids = new BigInt64Array(n);
  const attention_mask = new BigInt64Array(n).fill(1n);
  const token_type_ids = new BigInt64Array(n);
  for (let i = 0; i < n; i++) input_ids[i] = BigInt(t.ids[i]);
  const feeds = {
    input_ids: new ort.Tensor('int64', input_ids, [1, n]),
    attention_mask: new ort.Tensor('int64', attention_mask, [1, n]),
    token_type_ids: new ort.Tensor('int64', token_type_ids, [1, n]),
  };
  const res = await session.run(feeds);
  const H = res.last_hidden_state;                       // [1, n, D]
  const D = H.dims[2];
  const data = H.data;
  // 全文均值嵌入（排除 [CLS]/[SEP] 两端）
  const doc = new Float64Array(D);
  const nCore = Math.max(1, n - 2);
  for (let i = 1; i < n - 1; i++) for (let d = 0; d < D; d++) doc[d] += data[i * D + d];
  for (let d = 0; d < D; d++) doc[d] /= nCore;
  const docNorm = Math.sqrt(doc.reduce((s, v) => s + v * v, 0)) || 1;
  const subKey = new Float64Array(n);
  const subDist = new Float64Array(n);
  // 每个子词的上下文均值嵌入（窗口内排除自身）
  const ctxCache = new Map();
  for (let i = 1; i < n - 1; i++) {
    let dot = 0, norm = 0;
    for (let d = 0; d < D; d++) { dot += data[i * D + d] * doc[d]; norm += data[i * D + d] ** 2; }
    subKey[i] = dot / (docNorm * (Math.sqrt(norm) || 1));
    // 上下文窗口均值
    const a = Math.max(1, i - CTX_WIN), b = Math.min(n - 1, i + CTX_WIN + 1);
    const key = a * 100000 + b;
    let ctx = ctxCache.get(key);
    if (!ctx) {
      ctx = new Float64Array(D);
      for (let j = a; j < b; j++) { if (j === i) continue; for (let d = 0; d < D; d++) ctx[d] += data[j * D + d]; }
      const cnt = Math.max(1, (b - a) - 1);
      for (let d = 0; d < D; d++) ctx[d] /= cnt;
      ctxCache.set(key, ctx);
    }
    let cdot = 0, cnorm = 0, enorm = 0;
    for (let d = 0; d < D; d++) { cdot += data[i * D + d] * ctx[d]; cnorm += ctx[d] ** 2; enorm += data[i * D + d] ** 2; }
    const cos = cdot / ((Math.sqrt(cnorm) || 1) * (Math.sqrt(enorm) || 1));
    subDist[i] = 1 - cos;                                  // 特异性：与上下文越不像 → 信息量越高
  }
  // 按我们的 token 范围聚合（子词 → 词：取 max）
  const agg = (arr) => tokens.map(tok => {
    let best = 0;
    for (let i = 1; i < n - 1; i++) {
      if (t.starts[i] >= tok.start && t.ends[i] <= tok.end) best = Math.max(best, arr[i]);
    }
    return best;
  });
  return { scores: agg(subKey), distinct: agg(subDist), note: 'bert' };
}

self.addEventListener('message', async (e) => {
  const msg = e.data;
  if (msg.type === 'init') {
    base = msg.base || '';
    const ok = await loadModel();
    self.postMessage({ type: 'ready', ok, mode: ok ? 'bert' : 'static-only' });
  } else if (msg.type === 'score') {
    try {
      const r = await score(msg.text, msg.tokens);
      self.postMessage({ type: 'scored', scores: r.scores, distinct: r.distinct, note: r.note, tokenCount: msg.tokens.length });
    } catch (err) {
      self.postMessage({ type: 'scored', scores: null, distinct: null, note: 'error: ' + err.message });
    }
  } else if (msg.type === 'ping') {
    self.postMessage({ type: 'pong', ready: !!session, mode: session ? 'bert' : 'static-only' });
  }
});
