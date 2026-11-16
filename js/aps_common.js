/**
 * Anima Prompt Studio · 公共层
 * 样式 / API / 弹窗 / 目录选择器 / 小工具
 *
 * 所有类名以 `aps-` 开头，避免和 V6 面板的 `av3-` 冲突。
 */
import { api } from "../../scripts/api.js";
import { app } from "../../scripts/app.js";

export const NS = "anima-prompt-studio";

/* ── API ─────────────────────────────────────────────────────────── */
export async function fetchJSON(path, opts = {}) {
  const r = await api.fetchApi(`/${NS}${path}`, {
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });
  let body = null;
  try { body = await r.json(); } catch (_e) { body = null; }
  if (!r.ok) {
    const msg = (body && (body.error || body.message)) || `HTTP ${r.status}`;
    const err = new Error(msg);
    err.status = r.status;
    err.body = body;
    throw err;
  }
  return body;
}

export async function postJSON(path, body) {
  return fetchJSON(path, {
    method: "POST",
    body: JSON.stringify(body || {}),
  });
}

/* ── 节点控件 ────────────────────────────────────────────────────── */
export function widget(node, name) {
  return (node?.widgets || []).find((w) => w.name === name);
}

export function wval(node, name, fallback = "") {
  const w = widget(node, name);
  return w ? w.value : fallback;
}

export function wset(node, name, value) {
  const w = widget(node, name);
  if (!w) return false;
  w.value = value;
  if (w.callback) {
    try { w.callback(value, app.canvas, node, [0, 0], null); } catch (_e) { /* ignore */ }
  }
  app.graph?.setDirtyCanvas(true, true);
  return true;
}

export function hideWidget(node, name) {
  const w = widget(node, name);
  if (!w) return;
  // 只压成零高度，**不改 type**：type 是序列化/绘制契约，改了容易踩坑。
  w.computeSize = () => [0, -4];
}

/* ── 小工具 ──────────────────────────────────────────────────────── */
export function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function debounce(fn, ms = 250) {
  let t = 0;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

export function downloadText(filename, text) {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
}

export async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    toast("已复制到剪贴板");
  } catch (_e) {
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    ta.remove();
    toast("已复制到剪贴板");
  }
}

export function thumbURL(path) {
  if (!path) return "";
  if (/^(https?:|data:)/.test(path)) return path;
  if (path.startsWith("/")) return path;
  return `/${NS}/${path}`;
}

export function toast(msg, type = "info", ms = 2200) {
  ensureStyles();
  let box = document.getElementById("aps-toast");
  if (!box) {
    box = document.createElement("div");
    box.id = "aps-toast";
    document.body.appendChild(box);
  }
  const el = document.createElement("div");
  el.className = `aps-toast-item ${type}`;
  el.textContent = msg;
  box.appendChild(el);
  setTimeout(() => {
    el.classList.add("out");
    setTimeout(() => el.remove(), 350);
  }, ms);
}

export function confirmDialog(text) {
  return new Promise((resolve) => {
    ensureStyles();
    const mask = document.createElement("div");
    mask.className = "aps-mini-mask";
    mask.innerHTML = `
      <div class="aps-mini">
        <div class="aps-mini-title">确认</div>
        <div class="aps-mini-body">${esc(text)}</div>
        <div class="aps-mini-foot">
          <button class="aps-btn ghost" data-x="no">取消</button>
          <button class="aps-btn danger" data-x="yes">确定</button>
        </div>
      </div>`;
    const done = (v) => { mask.remove(); resolve(v); };
    mask.querySelector('[data-x="no"]').onclick = () => done(false);
    mask.querySelector('[data-x="yes"]').onclick = () => done(true);
    mask.onclick = (e) => { if (e.target === mask) done(false); };
    document.body.appendChild(mask);
  });
}

/* ── 通用弹窗 ────────────────────────────────────────────────────── */
export class Modal {
  constructor({ title = "", width = "min(1480px, 96vw)", height = "min(92vh, 980px)" } = {}) {
    ensureStyles();
    this.mask = document.createElement("div");
    this.mask.className = "aps-mask";
    this.mask.innerHTML = `
      <div class="aps-panel" style="width:${width};height:${height}">
        <div class="aps-head">
          <div class="aps-brand">
            <span class="aps-logo">APS</span>
            <span class="aps-title"></span>
          </div>
          <div class="aps-head-actions"></div>
          <button class="aps-close" title="关闭">✕</button>
        </div>
        <div class="aps-body"></div>
        <div class="aps-foot"></div>
      </div>`;
    this.panel = this.mask.querySelector(".aps-panel");
    this.head = this.mask.querySelector(".aps-head");
    this.titleEl = this.mask.querySelector(".aps-title");
    this.headActions = this.mask.querySelector(".aps-head-actions");
    this.body = this.mask.querySelector(".aps-body");
    this.foot = this.mask.querySelector(".aps-foot");
    this.setTitle(title);
    this.mask.querySelector(".aps-close").onclick = () => this.close();
    this.mask.onclick = (e) => { if (e.target === this.mask) this.close(); };
    this._onKey = (e) => { if (e.key === "Escape") this.close(); };
    document.addEventListener("keydown", this._onKey);
    document.body.appendChild(this.mask);
  }

  setTitle(t) { this.titleEl.textContent = t || ""; }

  show() { this.mask.style.display = "flex"; }

  close() {
    document.removeEventListener("keydown", this._onKey);
    this.mask.remove();
    this.onClose?.();
  }
}

/* ── 目录选择器（小弹窗，可给多框 / 选择器节点复用）────────────────── */
export function openCatalogPicker({ items = null, category = "", title = "从目录选择",
                                   multi = true, onPick } = {}) {
  const modal = new Modal({ title, width: "min(1080px, 94vw)",
                           height: "min(82vh, 760px)" });
  modal.body.classList.add("aps-picker-body");
  modal.body.innerHTML = `
    <div class="aps-picker-bar">
      <input class="aps-input aps-picker-q" placeholder="搜索英文 / 中文标签…">
      <select class="aps-input aps-picker-cat"></select>
      <label class="aps-check"><input type="checkbox" class="aps-picker-level"> 只显示 SFW</label>
    </div>
    <div class="aps-picker-info"></div>
    <div class="aps-picker-grid"></div>
    <div class="aps-picker-more"><button class="aps-btn ghost">加载更多</button></div>`;
  const qEl = modal.body.querySelector(".aps-picker-q");
  const catEl = modal.body.querySelector(".aps-picker-cat");
  const lvEl = modal.body.querySelector(".aps-picker-level");
  const infoEl = modal.body.querySelector(".aps-picker-info");
  const grid = modal.body.querySelector(".aps-picker-grid");
  const moreBtn = modal.body.querySelector(".aps-picker-more button");

  let meta = null;
  let page = 1;
  let total = 0;
  let list = [];
  const picked = new Map();

  const renderCats = () => {
    if (!meta) return;
    const opts = [];
    for (const g of meta.groups || []) {
      for (const c of g.cats || []) {
        opts.push(`<option value="${esc(c.key)}">${esc(c.label)}（${c.count}）</option>`);
      }
    }
    catEl.innerHTML = `<option value="">全部（${meta.total}）</option>` + opts.join("");
    if (category) catEl.value = category;
  };

  let render = () => {
    infoEl.textContent = `显示 ${list.length} / ${total} 条` +
      (picked.size ? ` · 已选 ${picked.size} 条` : "");
    grid.innerHTML = list.map((it) => {
      const on = picked.has(it.id);
      const thumb = thumbURL(it.thumb);
      return `<div class="aps-card ${on ? "on" : ""}" data-id="${esc(it.id)}">
        ${thumb ? `<div class="aps-card-thumb"><img loading="lazy" src="${esc(thumb)}"></div>` : ""}
        <div class="aps-card-main">
          <div class="aps-card-zh">${esc(it.zh)}</div>
          <div class="aps-card-en">${esc(it.en)}</div>
          <div class="aps-card-tags">
            <span class="aps-badge">${esc(it.slot)}</span>
            ${it.level ? `<span class="aps-badge lv${it.level}">L${it.level}</span>` : ""}
            <span class="aps-badge src">${esc(it.src)}</span>
          </div>
        </div>
        <div class="aps-card-side">${on ? "✓" : "+"}</div>
      </div>`;
    }).join("") || `<div class="aps-empty">没有匹配的标签</div>`;
    grid.querySelectorAll(".aps-card").forEach((el) => {
      el.onclick = () => {
        const id = el.dataset.id;
        const it = list.find((x) => x.id === id);
        if (!it) return;
        if (picked.has(id)) picked.delete(id);
        else {
          if (!multi && picked.size >= 1) picked.clear();
          picked.set(id, it);
        }
        render();
      };
    });
  };

  const load = async (reset = false) => {
    if (reset) { page = 1; list = []; }
    const params = new URLSearchParams({
      cat: catEl.value || "", q: qEl.value || "", page: String(page),
      limit: "60", src: "",
    });
    if (lvEl.checked) params.set("level_max", "0");
    const res = await fetchJSON(`/catalog/items?${params}`);
    total = res.total;
    list = reset ? res.items : list.concat(res.items);
    page += 1;
    moreBtn.parentElement.style.display = list.length < total ? "" : "none";
    render();
  };

  fetchJSON("/catalog/meta").then((m) => { meta = m; renderCats(); load(true); });
  qEl.oninput = debounce(() => load(true), 350);
  catEl.onchange = () => load(true);
  lvEl.onchange = () => load(true);
  moreBtn.onclick = () => load(false);

  modal.foot.innerHTML = `
    <div class="aps-foot-left aps-picker-sel"></div>
    <div class="aps-foot-right">
      <button class="aps-btn ghost" data-x="cancel">取消</button>
      <button class="aps-btn primary" data-x="ok">加入</button>
    </div>`;
  const selEl = modal.foot.querySelector(".aps-picker-sel");
  const refreshSel = () => {
    selEl.textContent = picked.size ? `已选 ${picked.size} 条` : "尚未选择";
  };
  const _render = render;
  render = () => { _render(); refreshSel(); };
  modal.foot.querySelector('[data-x="cancel"]').onclick = () => modal.close();
  modal.foot.querySelector('[data-x="ok"]').onclick = () => {
    const rows = Array.from(picked.values());
    try { onPick?.(rows); } catch (e) { console.error(e); }
    modal.close();
  };
  if (items) {
    rowsFromItems(items);
    function rowsFromItems(rows) {
      if (!Array.isArray(rows)) return;
      for (const r of rows) picked.set(r.id, r);
      refreshSel();
    }
  }
  modal.show();
  return modal;
}

/* ── 样式 ────────────────────────────────────────────────────────── */
let _styled = false;
export function ensureStyles() {
  if (_styled || document.getElementById("aps-style")) { _styled = true; return; }
  _styled = true;
  const css = `
:root {
  --aps-bg: #121419;
  --aps-panel: #171a21;
  --aps-panel2: #1d2129;
  --aps-line: #2b3140;
  --aps-text: #e8ebf2;
  --aps-dim: #9aa3b5;
  --aps-amber: #f0b45c;
  --aps-amber2: #ffd28a;
  --aps-cyan: #6fd3d8;
  --aps-danger: #e36969;
  --aps-ok: #76c893;
}
.aps-mask { position: fixed; inset: 0; z-index: 9000; display: flex;
  align-items: center; justify-content: center; padding: 2vh 2vw;
  background: rgba(5, 7, 11, .72); backdrop-filter: blur(6px); }
.aps-panel { display: flex; flex-direction: column; min-width: 720px;
  min-height: 520px; background: var(--aps-bg); color: var(--aps-text);
  border: 1px solid var(--aps-line); border-radius: 14px; overflow: hidden;
  box-shadow: 0 24px 80px rgba(0,0,0,.55); font-family: "Microsoft YaHei", system-ui, sans-serif;
  font-size: 13px; }
.aps-head { display: flex; align-items: center; gap: 12px; padding: 12px 16px;
  background: linear-gradient(180deg, #1b2029, #15181f);
  border-bottom: 1px solid var(--aps-line); flex: 0 0 auto; }
.aps-brand { display: flex; align-items: center; gap: 10px; min-width: 0; }
.aps-logo { display: inline-flex; align-items: center; justify-content: center;
  width: 34px; height: 26px; border-radius: 7px; font-weight: 800;
  letter-spacing: .5px; font-size: 11px; color: #20160a;
  background: linear-gradient(135deg, var(--aps-amber2), var(--aps-amber)); }
.aps-title { font-size: 16px; font-weight: 700; white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis; }
.aps-head-actions { display: flex; align-items: center; gap: 8px; margin-left: auto; }
.aps-close { width: 30px; height: 30px; border-radius: 8px; border: 1px solid var(--aps-line);
  background: transparent; color: var(--aps-dim); cursor: pointer; font-size: 15px; }
.aps-close:hover { color: #fff; background: #2a2f3a; }
.aps-body { flex: 1 1 auto; min-height: 0; display: flex; overflow: hidden; }
.aps-foot { flex: 0 0 auto; display: flex; align-items: center; gap: 10px;
  padding: 10px 16px; border-top: 1px solid var(--aps-line); background: #15181f; min-height: 46px; }
.aps-foot-left { color: var(--aps-dim); font-size: 12px; }
.aps-foot-right { margin-left: auto; display: flex; gap: 8px; }
.aps-btn { border: 1px solid var(--aps-line); background: #232833; color: var(--aps-text);
  padding: 7px 12px; border-radius: 8px; cursor: pointer; font-size: 12px;
  font-family: inherit; white-space: nowrap; }
.aps-btn:hover { background: #2c3340; border-color: #3a4354; }
.aps-btn.primary { background: linear-gradient(135deg, var(--aps-amber2), var(--aps-amber));
  color: #241708; border-color: transparent; font-weight: 700; }
.aps-btn.primary:hover { filter: brightness(1.06); }
.aps-btn.ghost { background: transparent; }
.aps-btn.danger { color: var(--aps-danger); border-color: #5b2c2c; }
.aps-btn.small { padding: 4px 8px; font-size: 11px; border-radius: 6px; }
.aps-btn:disabled { opacity: .45; cursor: not-allowed; }
.aps-input { background: #0e1116; color: var(--aps-text); border: 1px solid var(--aps-line);
  border-radius: 8px; padding: 7px 10px; font-family: inherit; font-size: 12px; outline: none; min-width: 0; }
.aps-input:focus { border-color: var(--aps-amber); box-shadow: 0 0 0 2px rgba(240,180,92,.12); }
.aps-select { background: #0e1116; color: var(--aps-text); border: 1px solid var(--aps-line);
  border-radius: 8px; padding: 6px 8px; font-family: inherit; font-size: 12px; outline: none; }
.aps-check { display: inline-flex; align-items: center; gap: 6px; color: var(--aps-dim); font-size: 12px; cursor: pointer; }
.aps-check input { accent-color: var(--aps-amber); }
.aps-badge { display: inline-flex; align-items: center; height: 18px; padding: 0 6px;
  border-radius: 5px; background: #262c38; color: var(--aps-dim); font-size: 10px; letter-spacing: .2px; }
.aps-badge.lv1 { background: #3b3020; color: #f3c37a; }
.aps-badge.lv2 { background: #3d2424; color: #f08b8b; }
.aps-badge.lv3 { background: #45202c; color: #f08ab0; }
.aps-badge.lv4 { background: #3b1c3f; color: #dba0f0; }
.aps-badge.src { background: #1e3036; color: #89d9de; }
.aps-empty { color: var(--aps-dim); text-align: center; padding: 40px 0; font-size: 13px; }
.aps-row { display: flex; align-items: center; gap: 8px; }
.aps-col { display: flex; flex-direction: column; gap: 8px; }
.aps-scroll { overflow: auto; min-height: 0; }
.aps-scroll::-webkit-scrollbar, .aps-panel *::-webkit-scrollbar { width: 8px; height: 8px; }
.aps-scroll::-webkit-scrollbar-thumb, .aps-panel *::-webkit-scrollbar-thumb { background: #3a4150; border-radius: 8px; }
.aps-toast-item { padding: 8px 14px; margin-top: 8px; border-radius: 8px; background: #232833;
  border: 1px solid var(--aps-line); color: var(--aps-text); font-size: 12px;
  box-shadow: 0 8px 24px rgba(0,0,0,.4); transition: opacity .3s, transform .3s; }
.aps-toast-item.ok { border-color: #2c5638; color: #a9e3bb; }
.aps-toast-item.err { border-color: #613333; color: #f2aaaa; }
.aps-toast-item.out { opacity: 0; transform: translateY(-6px); }
#aps-toast { position: fixed; top: 18px; left: 50%; transform: translateX(-50%);
  z-index: 10000; display: flex; flex-direction: column; align-items: center; pointer-events: none; }
.aps-mini-mask { position: fixed; inset: 0; z-index: 9500; display: flex; align-items: center;
  justify-content: center; background: rgba(5,7,11,.6); }
.aps-mini { width: min(420px, 90vw); background: var(--aps-panel); border: 1px solid var(--aps-line);
  border-radius: 12px; padding: 16px; color: var(--aps-text); box-shadow: 0 18px 50px rgba(0,0,0,.5); }
.aps-mini-title { font-weight: 700; margin-bottom: 8px; }
.aps-mini-body { color: var(--aps-dim); font-size: 12px; line-height: 1.7; }
.aps-mini-foot { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
/* 目录选择器 */
.aps-picker-body { display: flex; flex-direction: column; gap: 8px; padding: 12px 16px; overflow: hidden; }
.aps-picker-bar { display: flex; gap: 8px; align-items: center; }
.aps-picker-q { flex: 1; }
.aps-picker-cat { width: 260px; }
.aps-picker-info { color: var(--aps-dim); font-size: 11px; }
.aps-picker-grid { flex: 1; overflow: auto; display: grid; gap: 8px;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); align-content: start; padding-right: 4px; }
.aps-picker-more { text-align: center; }
.aps-picker-sel { font-size: 12px; }
.aps-card { position: relative; display: flex; gap: 8px; padding: 8px; border-radius: 9px;
  border: 1px solid var(--aps-line); background: var(--aps-panel2); cursor: pointer;
  transition: border-color .15s, background .15s; min-height: 54px; }
.aps-card:hover { border-color: #4a5365; background: #242a35; }
.aps-card.on { border-color: var(--aps-amber); box-shadow: 0 0 0 1px rgba(240,180,92,.25) inset; }
.aps-card-thumb { width: 46px; height: 46px; border-radius: 6px; overflow: hidden; flex: 0 0 auto; background: #0e1116; }
.aps-card-thumb img { width: 100%; height: 100%; object-fit: cover; }
.aps-card-main { min-width: 0; flex: 1; display: flex; flex-direction: column; gap: 3px; }
.aps-card-zh { font-size: 12px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.aps-card-en { font-size: 11px; color: var(--aps-dim); line-height: 1.35;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.aps-card-tags { display: flex; gap: 4px; flex-wrap: wrap; margin-top: 2px; }
.aps-card-side { align-self: center; color: var(--aps-amber); font-weight: 700; font-size: 15px; }
`;
  const style = document.createElement("style");
  style.id = "aps-style";
  style.textContent = css;
  document.head.appendChild(style);
}
