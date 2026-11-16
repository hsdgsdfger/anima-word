/**
 * 可排序 LoRA 编辑器
 *  - 数组顺序 = 应用顺序（后端逐项 load_lora_for_models）
 *  - 拖拽 / 上移 / 下移 / 启用 / 双强度 / 触发词 / 堆栈预设
 */
import { app } from "../../scripts/app.js";
import {
  Modal, NS, confirmDialog, copyText, debounce, downloadText, ensureStyles, esc,
  fetchJSON, postJSON, toast, widget, wset,
} from "./aps_common.js";

function parseEntries(raw) {
  let rows = [];
  try { rows = JSON.parse(raw || "[]"); } catch (_e) { rows = []; }
  if (rows && !Array.isArray(rows) && Array.isArray(rows.entries)) rows = rows.entries;
  if (!Array.isArray(rows)) rows = [];
  return rows.filter((r) => r && typeof r === "object" && r.name).map((r) => ({
    name: String(r.name),
    strength_model: Number.isFinite(+r.strength_model) ? +r.strength_model
      : (Number.isFinite(+r.strength) ? +r.strength : 1),
    strength_clip: Number.isFinite(+r.strength_clip) ? +r.strength_clip
      : (Number.isFinite(+r.strength) ? +r.strength : 1),
    on: r.on !== false,
    trigger: String(r.trigger || ""),
  }));
}

function fmtSize(n) {
  n = Number(n || 0);
  if (n > 1024 * 1024 * 1024) return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`;
  if (n > 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`;
  if (n > 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${n} B`;
}

let _loraStyled = false;
function ensureLoraStyles() {
  if (_loraStyled || document.getElementById("aps-lora-style")) { _loraStyled = true; return; }
  _loraStyled = true;
  const style = document.createElement("style");
  style.id = "aps-lora-style";
  style.textContent = `
.aps-lora-wrap { display: flex; gap: 10px; height: 100%; min-height: 0; }
.aps-lora-left { width: 300px; flex: 0 0 auto; display: flex; flex-direction: column;
  border: 1px solid var(--aps-line); border-radius: 10px; overflow: hidden; background: var(--aps-panel); }
.aps-lora-right { flex: 1; display: flex; flex-direction: column; min-width: 0;
  border: 1px solid var(--aps-line); border-radius: 10px; overflow: hidden; background: var(--aps-panel); }
.aps-lora-head { display: flex; align-items: center; gap: 8px; padding: 8px 10px;
  border-bottom: 1px solid var(--aps-line); font-weight: 700; font-size: 12px;
  background: #1b2029; flex: 0 0 auto; }
.aps-lora-head .sub { color: var(--aps-dim); font-weight: 400; font-size: 11px; }
.aps-lora-list { flex: 1; overflow: auto; padding: 6px; display: flex; flex-direction: column; gap: 4px; }
.aps-lora-row { display: flex; align-items: center; gap: 6px; padding: 6px 7px; border-radius: 7px;
  border: 1px solid transparent; cursor: pointer; }
.aps-lora-row:hover { background: #232833; border-color: #333b49; }
.aps-lora-row .nm { flex: 1; min-width: 0; font-size: 11px; white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis; }
.aps-lora-row .sz { color: var(--aps-dim); font-size: 10px; }
.aps-lora-stack { flex: 1; overflow: auto; padding: 8px; display: flex; flex-direction: column; gap: 6px; }
.aps-lora-item { display: flex; align-items: center; gap: 6px; padding: 7px 8px; border-radius: 9px;
  background: #1e232d; border: 1px solid #2c3442; cursor: grab; }
.aps-lora-item.dragging { opacity: .45; }
.aps-lora-item.off { opacity: .5; }
.aps-lora-item .idx { width: 24px; height: 24px; border-radius: 6px; background: #2c333f;
  display: inline-flex; align-items: center; justify-content: center; font-weight: 700;
  font-size: 11px; color: var(--aps-amber); flex: 0 0 auto; }
.aps-lora-item .body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.aps-lora-item .nm { font-size: 12px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.aps-lora-item .ctl { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.aps-lora-item .num { width: 62px; padding: 4px 6px; font-size: 11px; }
.aps-lora-item .trig { flex: 1; min-width: 120px; padding: 4px 6px; font-size: 11px; }
.aps-lora-item .acts { display: flex; gap: 2px; flex: 0 0 auto; }
.aps-lora-empty { color: var(--aps-dim); text-align: center; padding: 40px 10px; font-size: 12px; line-height: 1.8; }
.aps-lora-foot { display: flex; gap: 6px; align-items: center; padding: 7px 8px;
  border-top: 1px solid var(--aps-line); background: #171b23; flex: 0 0 auto; flex-wrap: wrap; }
.aps-lora-foot .aps-input { padding: 5px 7px; font-size: 11px; }
.aps-lora-order-note { color: var(--aps-dim); font-size: 11px; padding: 0 10px 6px; }
@media (max-width: 1100px) {
  .aps-lora-wrap { flex-direction: column; }
  .aps-lora-left { width: 100%; flex: 0 0 38%; min-height: 0; }
  .aps-lora-right { flex: 1; min-height: 0; }
  .aps-lora-list, .aps-lora-stack { min-height: 0; }
}
`;
  document.head.appendChild(style);
}

export class LoraEditor {
  constructor({ mount, entries = [], onChange = null, compact = false } = {}) {
    ensureStyles();
    ensureLoraStyles();
    this.mount = mount;
    this.entries = parseEntries(JSON.stringify(entries));
    this.onChange = onChange;
    this.compact = compact;
    this.loras = [];
    this.stacks = {};
    this.query = "";
    this.dragFrom = -1;
    this._build();
    this.refreshList();
    this.refreshStacks();
    this.renderStack();
  }

  _build() {
    this.mount.innerHTML = `
      <div class="aps-lora-wrap">
        <div class="aps-lora-left">
          <div class="aps-lora-head">本地 LoRA <span class="sub aps-lora-count"></span></div>
          <div style="padding:6px 8px;border-bottom:1px solid var(--aps-line)">
            <input class="aps-input aps-lora-search" placeholder="搜索 LoRA 文件名…" style="width:100%">
          </div>
          <div class="aps-lora-list aps-lora-local"></div>
        </div>
        <div class="aps-lora-right">
          <div class="aps-lora-head">应用顺序 <span class="sub">从上到下依次加载</span>
            <span style="margin-left:auto;color:var(--aps-dim);font-size:11px" class="aps-lora-n"></span>
          </div>
          <div class="aps-lora-order-note">拖拽排序 · 数字就是实际加载顺序 · 关掉的项不会加载</div>
          <div class="aps-lora-stack aps-lora-stacklist"></div>
          <div class="aps-lora-foot">
            <input class="aps-input aps-stack-name" placeholder="堆栈名" style="width:120px">
            <button class="aps-btn small aps-stack-save">保存堆栈</button>
            <select class="aps-select aps-stack-select" style="width:130px"><option value="">加载堆栈…</option></select>
            <button class="aps-btn small ghost aps-stack-del">删除</button>
            <span style="flex:1"></span>
            <button class="aps-btn small ghost aps-lora-export">导出</button>
            <button class="aps-btn small ghost aps-lora-import">导入</button>
          </div>
        </div>
      </div>`;
    this.searchEl = this.mount.querySelector(".aps-lora-search");
    this.localEl = this.mount.querySelector(".aps-lora-local");
    this.stackEl = this.mount.querySelector(".aps-lora-stacklist");
    this.countEl = this.mount.querySelector(".aps-lora-count");
    this.nEl = this.mount.querySelector(".aps-lora-n");
    this.nameEl = this.mount.querySelector(".aps-stack-name");
    this.selectEl = this.mount.querySelector(".aps-stack-select");

    this.searchEl.oninput = debounce(() => {
      this.query = this.searchEl.value.trim().toLowerCase();
      this.renderLocal();
    }, 200);
    this.mount.querySelector(".aps-stack-save").onclick = () => this.saveStack();
    this.mount.querySelector(".aps-stack-del").onclick = () => this.deleteStack();
    this.mount.querySelector(".aps-lora-export").onclick = () => this.exportJSON();
    this.mount.querySelector(".aps-lora-import").onclick = () => this.importJSON();
    this.selectEl.onchange = () => {
      const name = this.selectEl.value;
      if (name && this.stacks[name]) {
        this.entries = parseEntries(JSON.stringify(this.stacks[name].entries || []));
        this.renderStack();
        this.emit();
        toast(`已加载堆栈「${name}」`);
      }
    };
  }

  async refreshList() {
    try {
      const res = await fetchJSON("/loras");
      this.loras = res.items || [];
    } catch (e) {
      this.loras = [];
      toast(`LoRA 列表读取失败：${e.message}`, "err", 3500);
    }
    this.countEl.textContent = `(${this.loras.length})`;
    this.renderLocal();
  }

  async refreshStacks() {
    try {
      const res = await fetchJSON("/loras/stacks");
      this.stacks = res.stacks || {};
    } catch (_e) { this.stacks = {}; }
    const opts = ['<option value="">加载堆栈…</option>'];
    for (const k of Object.keys(this.stacks).sort()) {
      opts.push(`<option value="${esc(k)}">${esc(k)}</option>`);
    }
    this.selectEl.innerHTML = opts.join("");
  }

  renderLocal() {
    const q = this.query;
    const rows = this.loras.filter((r) => !q || r.name.toLowerCase().includes(q)).slice(0, 300);
    this.localEl.innerHTML = rows.map((r) => `
      <div class="aps-lora-row" data-name="${esc(r.name)}">
        <div class="nm" title="${esc(r.name)}">${r.favorite ? "⭐ " : ""}${esc(r.name)}</div>
        <div class="sz">${fmtSize(r.size)}</div>
        <button class="aps-btn small primary" data-add="1">＋</button>
      </div>`).join("") || `<div class="aps-lora-empty">没有匹配的 LoRA<br>把 .safetensors 放进 ComfyUI/models/loras</div>`;
    this.localEl.querySelectorAll(".aps-lora-row").forEach((row) => {
      const name = row.dataset.name;
      const add = () => {
        const meta = this.loras.find((x) => x.name === name) || {};
        this.entries.push({
          name, strength_model: 1, strength_clip: 1, on: true,
          trigger: String(meta.trigger || ""),
        });
        this.renderStack();
        this.emit();
      };
      row.onclick = (e) => { if (e.target.dataset.add) add(); };
      row.ondblclick = add;
    });
  }

  renderStack() {
    this.nEl.textContent = `${this.entries.filter((e) => e.on).length} / ${this.entries.length} 启用`;
    this.stackEl.innerHTML = this.entries.map((e, i) => `
      <div class="aps-lora-item ${e.on ? "" : "off"}" draggable="true" data-i="${i}">
        <div class="idx">${i + 1}</div>
        <div class="body">
          <div class="nm" title="${esc(e.name)}">${esc(e.name)}</div>
          <div class="ctl">
            <label class="aps-check"><input type="checkbox" data-k="on" ${e.on ? "checked" : ""}>启用</label>
            <span style="color:var(--aps-dim);font-size:10px">model</span>
            <input type="number" class="aps-input num" data-k="strength_model" step="0.05" value="${e.strength_model}">
            <span style="color:var(--aps-dim);font-size:10px">clip</span>
            <input type="number" class="aps-input num" data-k="strength_clip" step="0.05" value="${e.strength_clip}">
            <input class="aps-input trig" data-k="trigger" placeholder="触发词（可选，逗号分隔）" value="${esc(e.trigger)}">
          </div>
        </div>
        <div class="acts">
          <button class="aps-btn small ghost" data-act="up" title="上移">↑</button>
          <button class="aps-btn small ghost" data-act="down" title="下移">↓</button>
          <button class="aps-btn small ghost" data-act="dup" title="复制">⧉</button>
          <button class="aps-btn small danger" data-act="del" title="移除">✕</button>
        </div>
      </div>`).join("") || `<div class="aps-lora-empty">还没有 LoRA<br>从左侧点「＋」加入，或加载一个堆栈</div>`;

    this.stackEl.querySelectorAll(".aps-lora-item").forEach((el) => {
      const i = +el.dataset.i;
      el.querySelectorAll("[data-k]").forEach((input) => {
        input.onchange = () => {
          const k = input.dataset.k;
          if (k === "on") this.entries[i].on = input.checked;
          else if (k === "trigger") this.entries[i].trigger = input.value;
          else this.entries[i][k] = +input.value;
          if (k === "trigger") this._saveTrigger(i);
          if (k === "on") this.renderStack();
          this.emit();
        };
      });
      el.querySelector('[data-act="up"]').onclick = () => this.move(i, i - 1);
      el.querySelector('[data-act="down"]').onclick = () => this.move(i, i + 1);
      el.querySelector('[data-act="dup"]').onclick = () => {
        this.entries.splice(i + 1, 0, { ...this.entries[i] });
        this.renderStack(); this.emit();
      };
      el.querySelector('[data-act="del"]').onclick = () => {
        this.entries.splice(i, 1);
        this.renderStack(); this.emit();
      };
      el.ondragstart = (ev) => {
        this.dragFrom = i;
        el.classList.add("dragging");
        ev.dataTransfer.effectAllowed = "move";
        try { ev.dataTransfer.setData("text/plain", String(i)); } catch (_e) { /* ignore */ }
      };
      el.ondragend = () => { el.classList.remove("dragging"); this.dragFrom = -1; };
      el.ondragover = (ev) => { ev.preventDefault(); ev.dataTransfer.dropEffect = "move"; };
      el.ondrop = (ev) => {
        ev.preventDefault();
        const from = this.dragFrom;
        if (from < 0 || from === i) return;
        const item = this.entries.splice(from, 1)[0];
        this.entries.splice(i, 0, item);
        this.renderStack(); this.emit();
      };
    });
  }

  move(from, to) {
    if (to < 0 || to >= this.entries.length || from === to) return;
    const item = this.entries.splice(from, 1)[0];
    this.entries.splice(to, 0, item);
    this.renderStack(); this.emit();
  }

  async _saveTrigger(i) {
    const e = this.entries[i];
    if (!e) return;
    try {
      await postJSON("/loras/meta", { name: e.name, patch: { trigger: e.trigger } });
    } catch (_e) { /* 静默 */ }
  }

  async saveStack() {
    const name = this.nameEl.value.trim();
    if (!name) { toast("先填一个堆栈名", "err"); return; }
    try {
      await postJSON("/loras/stacks/save", { name, entries: this.entries });
      await this.refreshStacks();
      this.selectEl.value = name;
      toast(`堆栈「${name}」已保存`, "ok");
    } catch (e) { toast(`保存失败：${e.message}`, "err"); }
  }

  async deleteStack() {
    const name = this.selectEl.value;
    if (!name) { toast("先在下拉里选一个堆栈", "err"); return; }
    if (!(await confirmDialog(`删除堆栈「${name}」？`))) return;
    try {
      await postJSON("/loras/stacks/delete", { name });
      await this.refreshStacks();
      toast("已删除", "ok");
    } catch (e) { toast(`删除失败：${e.message}`, "err"); }
  }

  exportJSON() {
    downloadText("anima-lora-stack.json",
      JSON.stringify({ entries: this.entries }, null, 2));
  }

  importJSON() {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json,application/json";
    input.onchange = () => {
      const f = input.files?.[0];
      if (!f) return;
      const reader = new FileReader();
      reader.onload = () => {
        try {
          const data = JSON.parse(String(reader.result || ""));
          this.entries = parseEntries(JSON.stringify(data.entries || data));
          this.renderStack(); this.emit();
          toast("已导入", "ok");
        } catch (e) { toast(`导入失败：${e.message}`, "err"); }
      };
      reader.readAsText(f, "utf-8");
    };
    input.click();
  }

  emit() {
    const json = JSON.stringify(this.entries);
    this.onChange?.(json, this.entries);
  }

  getJSON() { return JSON.stringify(this.entries); }
}

export function openLoraModal(node, onChange) {
  ensureLoraStyles();
  const modal = new Modal({
    title: "LoRA 应用顺序 · 拖拽排序",
    width: "min(1180px, 94vw)", height: "min(78vh, 760px)",
  });
  const mount = document.createElement("div");
  mount.style.cssText = "flex:1;min-height:0;padding:10px 14px;display:flex;";
  modal.body.appendChild(mount);
  let current = parseEntries(widget(node, "lora_list_json")?.value || "[]");
  const editor = new LoraEditor({
    mount, entries: current,
    onChange: (json) => { current = parseEntries(json); },
  });
  modal.foot.innerHTML = `
    <div class="aps-foot-left">应用顺序 = 数组顺序；保存到节点后，后端按此顺序逐项加载。</div>
    <div class="aps-foot-right">
      <button class="aps-btn ghost" data-x="cancel">取消</button>
      <button class="aps-btn primary" data-x="ok">保存到节点</button>
    </div>`;
  modal.foot.querySelector('[data-x="cancel"]').onclick = () => modal.close();
  modal.foot.querySelector('[data-x="ok"]').onclick = () => {
    const json = editor.getJSON();
    wset(node, "lora_list_json", json);
    onChange?.(json, editor.entries);
    app.graph?.setDirtyCanvas(true, true);
    toast("LoRA 顺序已写入节点", "ok");
    modal.close();
  };
  modal.show();
  return modal;
}
