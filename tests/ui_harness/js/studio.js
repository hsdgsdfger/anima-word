/**
 * Anima Prompt Studio · 主界面
 *
 * 四区结构：
 *   左：分类（V6 词库 / 角色 / 画师 / 服装 / 场景 / 社区 / 我的）
 *   中：卡片目录（搜索 / 档位过滤 / 分页）
 *   右：手选托盘（拖拽排序 / 权重 / 开关 / 预览 / 负面词）
 *   上：模式（手选 / 混合 / 随机）+ 档位
 *
 * 状态唯一真源是节点的 `studio_json` 控件；面板只读写它。
 */
import { app } from "../../scripts/app.js";
import {
  Modal, NS, copyText, debounce, downloadText, ensureStyles, esc, fetchJSON,
  hideWidget, openCatalogPicker, postJSON, thumbURL, toast, wset, wval, widget,
} from "./aps_common.js";
import { LoraEditor } from "./lora_panel.js";

const PRESET_KEY = "aps.presets.v1";
const HISTORY_KEY = "aps.history.v1";
const RECENT_KEY = "aps.recent.v1";

const SLOT_ORDER = {
  quality: -1, artist: 0, character: 1, appearance: 2, clothing: 3,
  pose: 4, camera: 5, scene: 6, lighting: 7, other: 8,
};
const SLOT_LABEL = {
  quality: "质量", artist: "画师", character: "角色", appearance: "外貌",
  clothing: "服装", pose: "姿势", camera: "镜头", scene: "场景",
  lighting: "光影", other: "其他",
};
const MODE_LABEL = { manual: "手选", hybrid: "混合", random: "随机" };
const SCENE_CATS = new Set([
  "v6:scene", "background", "scene_sfw", "scene_nsfw",
  "scene_pose", "scene_art", "scene_weapon", "scene_near", "v6:canon",
]);

/* ── 样式 ────────────────────────────────────────────────────────── */
let _studioStyled = false;
function ensureStudioStyles() {
  if (_studioStyled || document.getElementById("aps-studio-style")) { _studioStyled = true; return; }
  _studioStyled = true;
  const style = document.createElement("style");
  style.id = "aps-studio-style";
  style.textContent = `
.aps-studio-body { padding: 0 !important; overflow: hidden; }
.aps-studio { flex: 1; display: flex; min-height: 0; width: 100%; }
.aps-side { width: 216px; flex: 0 0 auto; border-right: 1px solid var(--aps-line);
  display: flex; flex-direction: column; min-height: 0; background: #14171d; }
.aps-side-search { padding: 8px 10px; border-bottom: 1px solid var(--aps-line); }
.aps-side-search input { width: 100%; }
.aps-side-list { flex: 1; overflow: auto; padding: 6px; }
.aps-side-group { margin-bottom: 8px; }
.aps-side-title { font-size: 10px; color: #778196; letter-spacing: .6px;
  padding: 6px 8px 4px; text-transform: uppercase; }
.aps-side-item { display: flex; align-items: center; gap: 6px; padding: 6px 9px;
  border-radius: 7px; color: var(--aps-dim); cursor: pointer; font-size: 12px; }
.aps-side-item:hover { background: #202530; color: var(--aps-text); }
.aps-side-item.on { background: #2a2417; color: var(--aps-amber2);
  box-shadow: inset 2px 0 0 var(--aps-amber); }
.aps-side-item .c { margin-left: auto; font-size: 10px; color: #6c7688; }
.aps-main { flex: 1; min-width: 0; display: flex; flex-direction: column; min-height: 0; }
.aps-subtabs { display: flex; gap: 4px; padding: 6px 10px 0; border-bottom: 1px solid var(--aps-line);
  background: #15181f; flex: 0 0 auto; }
.aps-subtab { border: 1px solid transparent; border-bottom: 0; background: transparent;
  color: var(--aps-dim); padding: 7px 14px; border-radius: 8px 8px 0 0; cursor: pointer;
  font-size: 12px; font-family: inherit; }
.aps-subtab:hover { color: var(--aps-text); background: #1d222b; }
.aps-subtab.on { color: var(--aps-amber2); background: var(--aps-bg);
  border-color: var(--aps-line); box-shadow: inset 0 2px 0 var(--aps-amber); }
.aps-views { flex: 1; min-height: 0; display: flex; }
.aps-view { flex: 1; min-width: 0; display: flex; flex-direction: column; min-height: 0; }
.aps-view[hidden] { display: none; }
.aps-cat-head { display: flex; align-items: center; gap: 8px; padding: 8px 12px;
  border-bottom: 1px solid var(--aps-line); flex: 0 0 auto; flex-wrap: wrap; }
.aps-cat-title { font-weight: 700; font-size: 13px; }
.aps-cat-title .n { color: var(--aps-dim); font-weight: 400; font-size: 11px; margin-left: 6px; }
.aps-cat-head .grow { flex: 1; }
.aps-grid { flex: 1; overflow: auto; padding: 10px 12px; display: grid; gap: 8px;
  grid-template-columns: repeat(auto-fill, minmax(238px, 1fr)); align-content: start; }
.aps-grid-more { padding: 8px 12px 12px; text-align: center; flex: 0 0 auto; }
.aps-tray { width: 372px; flex: 0 0 auto; border-left: 1px solid var(--aps-line);
  display: flex; flex-direction: column; min-height: 0; background: #14171d; }
.aps-tray-head { display: flex; align-items: center; gap: 6px; padding: 8px 10px;
  border-bottom: 1px solid var(--aps-line); flex: 0 0 auto; }
.aps-tray-head .t { font-weight: 700; font-size: 13px; }
.aps-tray-head .n { color: var(--aps-dim); font-size: 11px; }
.aps-tray-tools { display: flex; gap: 4px; margin-left: auto; }
.aps-tray-list { flex: 1; overflow: auto; padding: 8px; display: flex; flex-direction: column; gap: 5px; min-height: 120px; }
.aps-sel { display: flex; gap: 5px; align-items: center; padding: 6px 7px; border-radius: 8px;
  border: 1px solid #2b3341; background: #1c212b; cursor: grab; }
.aps-sel.dragging { opacity: .4; }
.aps-sel.off { opacity: .55; }
.aps-sel .grip { color: #6f7a8e; font-size: 11px; cursor: grab; }
.aps-sel .idx { width: 20px; height: 20px; border-radius: 5px; background: #2a313d;
  color: var(--aps-amber); display: inline-flex; align-items: center; justify-content: center;
  font-size: 10px; font-weight: 700; flex: 0 0 auto; }
.aps-sel .body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.aps-sel .zh { font-size: 11px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.aps-sel .en { font-size: 10px; color: var(--aps-dim); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.aps-sel .ctl { display: flex; align-items: center; gap: 3px; }
.aps-sel input[type="number"] { width: 52px; padding: 3px 4px; font-size: 10px; }
.aps-sel .acts { display: flex; gap: 1px; flex-direction: column; }
.aps-sel .acts button { padding: 1px 4px; font-size: 10px; border-radius: 4px; }
.aps-tray-empty { color: var(--aps-dim); text-align: center; padding: 30px 12px; font-size: 12px; line-height: 1.8; }
.aps-tray-foot { flex: 0 0 auto; border-top: 1px solid var(--aps-line); padding: 8px 10px;
  display: flex; flex-direction: column; gap: 6px; background: #15181f; }
.aps-tray-row { display: flex; gap: 6px; align-items: center; }
.aps-tray-row .k { color: var(--aps-dim); font-size: 11px; width: 58px; flex: 0 0 auto; }
.aps-tray-row .aps-input, .aps-tray-row .aps-select { flex: 1; }
.aps-tray textarea.aps-input { resize: vertical; min-height: 38px; max-height: 160px; }
.aps-preview { margin: 0 10px 8px; border: 1px dashed #37404f; border-radius: 8px;
  padding: 8px; max-height: 210px; overflow: auto; background: #0f1218; }
.aps-preview .label { color: var(--aps-dim); font-size: 10px; letter-spacing: .4px; margin-bottom: 4px; }
.aps-preview .pos { color: #e8ebf2; font-size: 11px; line-height: 1.6; word-break: break-word; }
.aps-preview .neg { color: #d79a9a; font-size: 11px; line-height: 1.55; margin-top: 6px; word-break: break-word; }
.aps-preview .meta { color: var(--aps-dim); font-size: 10px; margin-top: 6px; }
.aps-mode { display: inline-flex; border: 1px solid var(--aps-line); border-radius: 9px; overflow: hidden; }
.aps-mode button { border: 0; background: #1a1f27; color: var(--aps-dim); padding: 6px 11px;
  font-size: 12px; cursor: pointer; font-family: inherit; }
.aps-mode button + button { border-left: 1px solid var(--aps-line); }
.aps-mode button.on { background: #3a2e19; color: var(--aps-amber2); font-weight: 700; }
.aps-my-head { display: flex; gap: 6px; padding: 10px 12px; border-bottom: 1px solid var(--aps-line); flex-wrap: wrap; }
.aps-my-list { flex: 1; overflow: auto; padding: 10px 12px; display: flex; flex-direction: column; gap: 5px; }
.aps-my-row { display: flex; gap: 6px; align-items: center; padding: 7px 8px; border-radius: 7px;
  background: #1c212b; border: 1px solid #2b3341; }
.aps-my-row .en { flex: 1; min-width: 0; font-size: 11px; }
.aps-my-row .zh { color: var(--aps-dim); font-size: 11px; }
.aps-ai { padding: 14px 18px; overflow: auto; display: flex; flex-direction: column; gap: 10px; }
.aps-ai-card { border: 1px solid var(--aps-line); border-radius: 10px; padding: 12px;
  background: #1a1f27; }
.aps-ai-card h4 { margin: 0 0 8px; font-size: 13px; }
.aps-ai-off { color: var(--aps-amber2); }
.aps-ai-provider { display: flex; gap: 8px; align-items: center; padding: 5px 0; font-size: 12px; }
.aps-ai-provider .dot { width: 8px; height: 8px; border-radius: 50%; background: #7a4a4a; }
.aps-ai-provider .dot.on { background: var(--aps-ok); }
.aps-hint { color: var(--aps-dim); font-size: 11px; line-height: 1.7; }
.aps-code { background: #0e1116; border: 1px solid var(--aps-line); border-radius: 8px;
  padding: 8px; font-family: Consolas, monospace; font-size: 10px; color: #b9c4d6;
  white-space: pre-wrap; max-height: 260px; overflow: auto; }
.aps-preset-list { flex: 1; overflow: auto; padding: 10px 12px; display: flex; flex-direction: column; gap: 5px; }
.aps-preset-row { display: flex; gap: 8px; align-items: center; padding: 7px 9px;
  border-radius: 7px; background: #1c212b; border: 1px solid #2b3341; }
.aps-preset-row .nm { flex: 1; font-size: 12px; }
.aps-preset-row .dt { color: var(--aps-dim); font-size: 10px; }
@media (max-width: 1100px) {
  .aps-side { width: 150px; }
  .aps-tray { width: 280px; }
  .aps-subtabs { overflow-x: auto; flex-wrap: nowrap; }
  .aps-subtab { white-space: nowrap; flex: 0 0 auto; padding: 6px 7px; font-size: 10px; }
  .aps-tray-row .k { width: 46px; font-size: 10px; }
  .aps-tray { font-size: 11px; }
  .aps-grid { grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); padding: 8px; }
}
`;
  document.head.appendChild(style);
}

/* ── 状态 ────────────────────────────────────────────────────────── */
function parseStudio(node) {
  let raw = {};
  try { raw = JSON.parse(wval(node, "studio_json", "{}") || "{}"); } catch (_e) { raw = {}; }
  if (!raw || typeof raw !== "object") raw = {};
  return {
    version: 1,
    mode: raw.mode || (wval(node, "mode", "manual") || "manual"),
    items: Array.isArray(raw.items) ? raw.items.filter((x) => x && x.en) : [],
    order: raw.order || "slot",
    quality_prefix: raw.quality_prefix || "",
    extra_text: raw.extra_text || "",
    negative_preset: raw.negative_preset || "standard",
    negative_extra: raw.negative_extra || "",
    lora: Array.isArray(raw.lora) ? raw.lora : [],
    ui: raw.ui && typeof raw.ui === "object" ? raw.ui : {},
  };
}

function saveStudio(node, st) {
  wset(node, "studio_json", JSON.stringify(st));
  wset(node, "mode", st.mode);
}

function widgetsOf(node) {
  const names = [
    "nsfw_level", "seed", "tag_cap", "base_prob", "disabled_sections",
    "lock_fields", "force_role", "weights_json", "extra_body",
    "appearance_follow", "selected_roles", "big_breasts", "role_works",
    "breast_size", "outfit_style", "role_fav_only", "hair_follow",
    "hair_len_pick", "hair_tie_pick", "hair_curl_pick", "hair_acc_pick",
    "role_pick", "scene_pick", "dry_skin_filter", "dry_skin_groups",
    "dry_skin_tags", "duo_role_fill", "pick_pool_mode", "pick_pool_ids",
  ];
  const out = {};
  for (const n of names) {
    const w = widget(node, n);
    if (w) out[n] = w.value;
  }
  return out;
}

function recentIDs() {
  try { return JSON.parse(localStorage.getItem(RECENT_KEY) || "[]"); } catch (_e) { return []; }
}
function pushRecent(id) {
  const rows = recentIDs().filter((x) => x !== id);
  rows.unshift(id);
  localStorage.setItem(RECENT_KEY, JSON.stringify(rows.slice(0, 60)));
}

function loadPresets() {
  try { return JSON.parse(localStorage.getItem(PRESET_KEY) || "{}"); } catch (_e) { return {}; }
}
function savePresets(rows) {
  localStorage.setItem(PRESET_KEY, JSON.stringify(rows));
}

function pushHistory(text) {
  if (!text) return;
  try {
    const rows = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
    rows.unshift({ text, at: Date.now() });
    localStorage.setItem(HISTORY_KEY, JSON.stringify(rows.slice(0, 40)));
  } catch (_e) { /* ignore */ }
}

/* ── 主面板 ────────────────────────────────────────────────────── */
export function openStudio(node) {
  ensureStylesStudio();
  const st = parseStudio(node);
  const modal = new Modal({
    title: "Anima 提示词工坊 · 自由选择",
    width: "min(1560px, 97vw)", height: "min(94vh, 1020px)",
  });
  modal.body.classList.add("aps-studio-body");

  const root = document.createElement("div");
  root.className = "aps-studio";
  root.innerHTML = `
    <aside class="aps-side">
      <div class="aps-side-search"><input class="aps-input aps-q" placeholder="搜索标签…"></div>
      <div class="aps-side-list"></div>
    </aside>
    <main class="aps-main">
      <div class="aps-subtabs">
        <button class="aps-subtab on" data-tab="catalog">🧩 自由选择</button>
        <button class="aps-subtab" data-tab="lora">🔗 LoRA</button>
        <button class="aps-subtab" data-tab="my">⭐ 我的 Tag</button>
        <button class="aps-subtab" data-tab="preset">💾 预设 / 历史</button>
        <button class="aps-subtab" data-tab="ai">🤖 AI（预留）</button>
      </div>
      <div class="aps-views">
        <section class="aps-view" data-view="catalog">
          <div class="aps-cat-head">
            <div class="aps-cat-title"><span class="nm">全部</span><span class="n"></span></div>
            <span class="grow"></span>
            <label class="aps-check"><input type="checkbox" class="aps-only-sfw"> 只显示 SFW</label>
            <select class="aps-select aps-src">
              <option value="">全部来源</option>
              <option value="v6">V6 词库</option>
              <option value="tools">Anima-Tools</option>
              <option value="builtin">内置质量词</option>
              <option value="my">我的 Tag</option>
            </select>
            <button class="aps-btn small ghost aps-random" title="从当前分类随机抽取一条">🎲 随机一条</button>
          </div>
          <div class="aps-grid"></div>
          <div class="aps-grid-more"><button class="aps-btn ghost">加载更多</button></div>
        </section>
        <section class="aps-view" data-view="lora" hidden>
          <div style="flex:1;min-height:0;padding:10px 12px;display:flex" class="aps-lora-mount"></div>
          <div class="aps-hint" style="padding:0 12px 10px">
            这里的顺序会写进节点第 6 个输出 <b>lora_json</b>；把「Anima 多 LoRA 加载器（可排序）」的
            <b>lora_list_json</b> 右键转成输入后连上即可。数组顺序 = 实际加载顺序。
          </div>
        </section>
        <section class="aps-view" data-view="my" hidden>
          <div class="aps-my-head">
            <input class="aps-input aps-my-en" placeholder="英文 tag（逗号分隔）" style="flex:1;min-width:200px">
            <input class="aps-input aps-my-zh" placeholder="中文名" style="width:130px">
            <select class="aps-select aps-my-slot">
              ${Object.keys(SLOT_LABEL).map((k) => `<option value="${k}">${SLOT_LABEL[k]}</option>`).join("")}
            </select>
            <button class="aps-btn primary aps-my-add">＋ 添加</button>
            <button class="aps-btn ghost aps-my-from-sel">把当前手选存为我的 Tag</button>
          </div>
          <div class="aps-my-list"></div>
        </section>
        <section class="aps-view" data-view="preset" hidden>
          <div class="aps-my-head">
            <button class="aps-btn primary aps-preset-save">保存当前手选为预设</button>
            <button class="aps-btn ghost aps-preset-export">导出 JSON</button>
            <button class="aps-btn ghost aps-preset-import">导入 JSON</button>
            <span class="grow"></span>
            <span class="aps-hint">预设存在浏览器 localStorage，不跟工作流走</span>
          </div>
          <div class="aps-preset-list"></div>
        </section>
        <section class="aps-view" data-view="ai" hidden>
          <div class="aps-ai"></div>
        </section>
      </div>
    </main>
    <aside class="aps-tray">
      <div class="aps-tray-head">
        <span class="t">手选托盘</span><span class="n aps-tray-n"></span>
        <span class="aps-tray-tools">
          <button class="aps-btn small ghost aps-tray-clear" title="清空">清空</button>
        </span>
      </div>
      <div class="aps-tray-list"></div>
      <div class="aps-preview" style="display:none">
        <div class="label">正向</div><div class="pos"></div>
        <div class="label" style="margin-top:6px">负面</div><div class="neg"></div>
        <div class="meta"></div>
        <div class="aps-row" style="margin-top:6px">
          <button class="aps-btn small ghost aps-copy-pos">复制正向</button>
          <button class="aps-btn small ghost aps-copy-neg">复制负面</button>
        </div>
      </div>
      <div class="aps-tray-foot">
        <div class="aps-tray-row"><span class="k">模式</span>
          <div class="aps-mode">
            <button data-mode="manual">手选</button>
            <button data-mode="hybrid">混合</button>
            <button data-mode="random">随机</button>
          </div>
        </div>
        <div class="aps-tray-row"><span class="k">档位</span>
          <select class="aps-select aps-level">
            <option value="sfw">0 · 全年龄</option>
            <option value="suggestive">1 · 擦边</option>
            <option value="explicit">2 · 成人</option>
            <option value="hardcore">3 · 过激</option>
            <option value="extreme">4 · 极端</option>
            <option value="any">不限</option>
          </select>
        </div>
        <div class="aps-tray-row"><span class="k">排序</span>
          <select class="aps-select aps-order">
            <option value="slot">按槽位（与随机引擎观感一致）</option>
            <option value="custom">按手选顺序</option>
          </select>
        </div>
        <div class="aps-tray-row"><span class="k">质量前缀</span>
          <input class="aps-input aps-qprefix" placeholder="可留空，例：masterpiece, best quality">
        </div>
        <div class="aps-tray-row"><span class="k">额外补充</span>
          <input class="aps-input aps-extra" placeholder="手写 tag，逗号分隔">
        </div>
        <div class="aps-tray-row"><span class="k">负面词</span>
          <select class="aps-select aps-negpreset">
            <option value="standard">标准</option>
            <option value="full">全量</option>
            <option value="none">不生成</option>
          </select>
        </div>
        <div class="aps-tray-row"><span class="k">负面补充</span>
          <input class="aps-input aps-negextra" placeholder="额外负面词，逗号分隔">
        </div>
        <div class="aps-row">
          <button class="aps-btn primary aps-preview-btn" style="flex:1">预览出词</button>
          <button class="aps-btn aps-apply-btn">写回节点</button>
        </div>
      </div>
    </aside>`;
  modal.body.appendChild(root);

  const sideList = root.querySelector(".aps-side-list");
  const grid = root.querySelector(".aps-grid");
  const gridMore = root.querySelector(".aps-grid-more button");
  const catTitle = root.querySelector(".aps-cat-title .nm");
  const catN = root.querySelector(".aps-cat-title .n");
  const trayList = root.querySelector(".aps-tray-list");
  const trayN = root.querySelector(".aps-tray-n");
  const previewEl = root.querySelector(".aps-preview");
  const qEl = root.querySelector(".aps-q");
  const onlySfw = root.querySelector(".aps-only-sfw");
  const srcEl = root.querySelector(".aps-src");
  const loraMount = root.querySelector(".aps-lora-mount");
  const aiEl = root.querySelector(".aps-ai");
  const myList = root.querySelector(".aps-my-list");
  const presetList = root.querySelector(".aps-preset-list");

  const ui = {
    cat: st.ui.cat || "__all__",
    q: "",
    page: 1,
    total: 0,
    items: [],
    list: [],
    loading: false,
    dragFrom: -1,
    preview: null,
    meta: null,
    my: [],
    loraEditor: null,
  };

  const randomBtn = root.querySelector(".aps-random");
  function syncRandomBtn() {
    const scene = SCENE_CATS.has(ui.cat);
    randomBtn.textContent = scene ? "🎲 随机场景" : "🎲 随机一条";
    randomBtn.title = scene
      ? "从当前场景分类随机抽取一条（不受首屏 60 条限制）"
      : "从当前分类随机抽取一条（不受首屏 60 条限制）";
  }
  randomBtn.onclick = () => randomPick();

  /* 模式 / 档位 / 排序回填 */
  const syncMode = () => {
    root.querySelectorAll(".aps-mode button").forEach((b) => {
      b.classList.toggle("on", b.dataset.mode === st.mode);
    });
    modal.setTitle(`Anima 提示词工坊 · ${MODE_LABEL[st.mode] || st.mode}`);
  };
  syncMode();
  root.querySelectorAll(".aps-mode button").forEach((b) => {
    b.onclick = () => {
      st.mode = b.dataset.mode;
      syncMode(); persist();
    };
  });
  root.querySelector(".aps-level").value = wval(node, "nsfw_level", "sfw");
  root.querySelector(".aps-level").onchange = (e) => {
    wset(node, "nsfw_level", e.target.value);
    persist();
  };
  root.querySelector(".aps-order").value = st.order;
  root.querySelector(".aps-order").onchange = (e) => {
    st.order = e.target.value; persist(); renderTray();
  };
  root.querySelector(".aps-qprefix").value = st.quality_prefix;
  root.querySelector(".aps-qprefix").onchange = (e) => {
    st.quality_prefix = e.target.value; persist();
  };
  root.querySelector(".aps-extra").value = st.extra_text;
  root.querySelector(".aps-extra").onchange = (e) => {
    st.extra_text = e.target.value; persist();
  };
  root.querySelector(".aps-negpreset").value = st.negative_preset;
  root.querySelector(".aps-negpreset").onchange = (e) => {
    st.negative_preset = e.target.value; persist();
  };
  root.querySelector(".aps-negextra").value = st.negative_extra;
  root.querySelector(".aps-negextra").onchange = (e) => {
    st.negative_extra = e.target.value; persist();
  };

  const persist = debounce(() => saveStudio(node, st), 300);

  /* ── 分类 ── */
  const pseudo = [
    { key: "__all__", label: "📚 全部目录", count: 0 },
    { key: "__fav__", label: "⭐ 我的收藏", count: 0 },
    { key: "__recent__", label: "🕘 最近使用", count: 0 },
  ];
  const renderSide = () => {
    const meta = ui.meta;
    if (!meta) return;
    const parts = [];
    const one = (key, label, count) => `
      <div class="aps-side-item ${ui.cat === key ? "on" : ""}" data-cat="${esc(key)}">
        <span>${esc(label)}</span><span class="c">${count ?? ""}</span></div>`;
    parts.push(`<div class="aps-side-group">${pseudo.map((p) => one(p.key, p.label,
      p.key === "__all__" ? meta.total : "")).join("")}</div>`);
    for (const g of meta.groups || []) {
      parts.push(`<div class="aps-side-group"><div class="aps-side-title">${esc(g.title)}</div>${
        g.cats.map((c) => one(c.key, c.label, c.count)).join("")}</div>`);
    }
    sideList.innerHTML = parts.join("");
    sideList.querySelectorAll(".aps-side-item").forEach((el) => {
      el.onclick = () => {
        ui.cat = el.dataset.cat;
        st.ui.cat = ui.cat;
        persist();
        renderSide();
        loadCatalog(true);
      };
    });
  };

  fetchJSON("/catalog/meta").then((meta) => {
    ui.meta = meta;
    renderSide();
    loadCatalog(true);
  }).catch((e) => toast(`目录加载失败：${e.message}`, "err", 4000));

  /* ── 目录加载 ── */
  const catLabel = (key) => {
    if (!ui.meta) return key;
    for (const p of pseudo) if (p.key === key) return p.label;
    for (const g of ui.meta.groups || []) {
      for (const c of g.cats || []) if (c.key === key) return c.label;
    }
    return key;
  };

  async function loadCatalog(reset = false) {
    if (ui.loading) return;
    ui.loading = true;
    if (reset) { ui.page = 1; ui.list = []; }
    catTitle.textContent = catLabel(ui.cat);
    syncRandomBtn();
    try {
      if (ui.cat === "__fav__") {
        const res = await fetchJSON("/studio/favorites");
        ui.list = res.items || [];
        ui.total = ui.list.length;
        renderGrid();
        catN.textContent = `${ui.total} 条`;
        ui.loading = false;
        gridMore.parentElement.style.display = "none";
        return;
      }
      if (ui.cat === "__recent__") {
        const ids = recentIDs();
        const res = await postJSON("/catalog/by-ids", { ids: ids.slice(0, 200) });
        ui.list = res.items || [];
        ui.total = ui.list.length;
        renderGrid();
        catN.textContent = `${ui.total} 条`;
        ui.loading = false;
        gridMore.parentElement.style.display = "none";
        return;
      }
      const params = new URLSearchParams({
        cat: ui.cat === "__all__" ? "" : ui.cat,
        q: ui.q, page: String(ui.page), limit: "60",
        src: srcEl.value || "",
      });
      if (onlySfw.checked) params.set("level_max", "0");
      const res = await fetchJSON(`/catalog/items?${params}`);
      ui.total = res.total;
      ui.page += 1;
      ui.list = reset ? res.items : ui.list.concat(res.items);
      renderGrid();
      catN.textContent = `${ui.total} 条`;
      gridMore.parentElement.style.display = ui.list.length < ui.total ? "" : "none";
    } catch (e) {
      toast(`目录读取失败：${e.message}`, "err", 3500);
    } finally {
      ui.loading = false;
      gridMore.disabled = false;
    }
  }

  async function randomPick() {
    if (ui.loading || randomBtn.disabled) return;
    randomBtn.disabled = true;
    const prev = randomBtn.textContent;
    randomBtn.textContent = "抽取中…";
    try {
      let item = null;
      if (ui.cat === "__fav__" || ui.cat === "__recent__") {
        if (!ui.list.length) throw new Error("当前列表为空");
        item = ui.list[Math.floor(Math.random() * ui.list.length)];
      } else {
        const params = new URLSearchParams({
          cat: ui.cat === "__all__" ? "" : ui.cat,
          q: ui.q, src: srcEl.value || "",
        });
        if (onlySfw.checked) params.set("level_max", "0");
        const res = await fetchJSON(`/catalog/random?${params}`);
        item = res.item;
      }
      if (!item) throw new Error("当前分类没有可抽取的标签");
      if (!ui.list.some((x) => x.id === item.id)) ui.list.unshift(item);
      addItem(item);
      toast(`随机选中：${item.zh || item.en}`, "ok");
    } catch (e) {
      toast(`随机失败：${e.message}`, "err", 3500);
    } finally {
      randomBtn.disabled = false;
      randomBtn.textContent = prev;
      syncRandomBtn();
    }
  }

  qEl.oninput = debounce(() => { ui.q = qEl.value.trim(); loadCatalog(true); }, 350);
  onlySfw.onchange = () => loadCatalog(true);
  srcEl.onchange = () => loadCatalog(true);
  gridMore.onclick = () => { gridMore.disabled = true; loadCatalog(false); };

  const favorites = new Set();
  fetchJSON("/studio/favorites").then((res) => {
    for (const it of res.items || []) favorites.add(it.id);
    renderGrid();
  }).catch(() => { /* ignore */ });

  function isSelected(id) {
    return st.items.some((x) => x.id === id);
  }

  function addItem(it) {
    if (!it || !it.en) return;
    const old = st.items.find((x) => x.id === it.id);
    if (old) {
      old.on = old.on !== false;
    } else {
      st.items.push({
        id: it.id, cat: it.cat, en: it.en, zh: it.zh, slot: it.slot || "other",
        src: it.src || "", w: 1, on: true,
      });
      pushRecent(it.id);
    }
    persist(); renderTray(); renderGrid();
  }

  function toggleItem(it) {
    const idx = st.items.findIndex((x) => x.id === it.id);
    if (idx >= 0) st.items.splice(idx, 1);
    else addItem(it);
    persist(); renderTray(); renderGrid();
  }

  function renderGrid() {
    if (!ui.list.length) {
      grid.innerHTML = `<div class="aps-empty">没有匹配的标签<br>换个分类或清空搜索试试</div>`;
      return;
    }
    grid.innerHTML = ui.list.map((it) => {
      const on = isSelected(it.id);
      const fav = favorites.has(it.id);
      const thumb = thumbURL(it.thumb);
      return `<div class="aps-card ${on ? "on" : ""}" data-id="${esc(it.id)}">
        ${thumb ? `<div class="aps-card-thumb"><img loading="lazy" src="${esc(thumb)}" onerror="this.parentElement.style.display='none'"></div>` : ""}
        <div class="aps-card-main">
          <div class="aps-card-zh">${esc(it.zh)}</div>
          <div class="aps-card-en">${esc(it.en)}</div>
          <div class="aps-card-tags">
            <span class="aps-badge">${esc(SLOT_LABEL[it.slot] || it.slot)}</span>
            ${it.level ? `<span class="aps-badge lv${it.level}">L${it.level}</span>` : ""}
            <span class="aps-badge src">${esc(it.src)}</span>
          </div>
        </div>
        <button class="aps-card-star" data-star="1" title="收藏">${fav ? "★" : "☆"}</button>
        <div class="aps-card-side">${on ? "✓" : "＋"}</div>
      </div>`;
    }).join("");
    grid.querySelectorAll(".aps-card").forEach((el) => {
      const it = ui.list.find((x) => x.id === el.dataset.id);
      el.onclick = (e) => {
        if (e.target.dataset.star) {
          e.stopPropagation();
          toggleFav(it, el.querySelector(".aps-card-star"));
          return;
        }
        toggleItem(it);
      };
    });
  }

  async function toggleFav(it, starEl) {
    if (!it) return;
    try {
      const res = await postJSON("/studio/favorites/toggle", { id: it.id });
      if (res.on) favorites.add(it.id); else favorites.delete(it.id);
      if (starEl) starEl.textContent = res.on ? "★" : "☆";
    } catch (e) { toast(`收藏失败：${e.message}`, "err"); }
  }

  /* ── 托盘 ── */
  function sortedItems() {
    if (st.order === "custom") return st.items;
    return [...st.items].sort((a, b) =>
      (SLOT_ORDER[a.slot] ?? 99) - (SLOT_ORDER[b.slot] ?? 99));
  }

  // 托盘一旦手动排序，就切到“手选顺序”；否则槽位排序会立刻把视觉顺序排回去，
  // 用户看到的是“点了上下移动但没反应”。
  function useCustomOrder(rows) {
    if (st.order === "custom") return;
    st.items = rows;
    st.order = "custom";
    const el = root.querySelector(".aps-order");
    if (el) el.value = "custom";
  }

  function renderTray() {
    const onN = st.items.filter((x) => x.on !== false).length;
    trayN.textContent = `${st.items.length} 条 · 启用 ${onN}`;
    const rows = sortedItems();
    if (!rows.length) {
      trayList.innerHTML = `<div class="aps-tray-empty">还没有手选标签<br>点中间卡片右上角的「＋」加入</div>`;
      return;
    }
    trayList.innerHTML = rows.map((it, i) => `
      <div class="aps-sel ${it.on === false ? "off" : ""}" draggable="true" data-id="${esc(it.id)}" data-i="${i}">
        <span class="grip">⋮⋮</span>
        <span class="idx">${i + 1}</span>
        <div class="body">
          <div class="zh" title="${esc(it.zh)}">${esc(it.zh)}</div>
          <div class="en" title="${esc(it.en)}">${esc(it.en)}</div>
        </div>
        <div class="ctl">
          <input type="checkbox" data-k="on" ${it.on === false ? "" : "checked"} title="启用">
          <input type="number" class="aps-input" data-k="w" min="0.1" max="3" step="0.05" value="${it.w ?? 1}" title="权重">
        </div>
        <div class="acts">
          <button class="aps-btn small ghost" data-act="up">↑</button>
          <button class="aps-btn small ghost" data-act="down">↓</button>
          <button class="aps-btn small danger" data-act="del">✕</button>
        </div>
      </div>`).join("");
    trayList.querySelectorAll(".aps-sel").forEach((el) => {
      const id = el.dataset.id;
      const i = +el.dataset.i;
      const it = st.items.find((x) => x.id === id);
      el.querySelectorAll("[data-k]").forEach((inp) => {
        inp.onchange = () => {
          if (inp.dataset.k === "on") it.on = inp.checked;
          if (inp.dataset.k === "w") it.w = Math.max(0.1, Math.min(3, +inp.value || 1));
          persist(); renderTray(); renderGrid();
        };
      });
      el.querySelector('[data-act="up"]').onclick = () => moveCustom(id, -1);
      el.querySelector('[data-act="down"]').onclick = () => moveCustom(id, 1);
      el.querySelector('[data-act="del"]').onclick = () => {
        st.items.splice(st.items.findIndex((x) => x.id === id), 1);
        persist(); renderTray(); renderGrid();
      };
      el.ondragstart = (ev) => {
        ui.dragId = id;
        ui.dragFrom = st.items.findIndex((x) => x.id === id);
        el.classList.add("dragging");
        try { ev.dataTransfer.setData("text/plain", id); } catch (_e) { /* ignore */ }
      };
      el.ondragend = () => { el.classList.remove("dragging"); ui.dragId = ""; ui.dragFrom = -1; };
      el.ondragover = (ev) => { ev.preventDefault(); ev.dataTransfer.dropEffect = "move"; };
      el.ondrop = (ev) => {
        ev.preventDefault();
        const rows = sortedItems();
        const from = rows.findIndex((x) => x.id === ui.dragId);
        const to = rows.findIndex((x) => x.id === id);
        if (from < 0 || to < 0 || from === to) return;
        useCustomOrder(rows);
        const item = st.items.splice(from, 1)[0];
        st.items.splice(to, 0, item);
        persist(); renderTray(); renderGrid();
      };
    });
  }

  function moveCustom(id, delta) {
    const rows = sortedItems();
    const from = rows.findIndex((x) => x.id === id);
    const to = from + delta;
    if (from < 0 || to < 0 || to >= rows.length) return;
    useCustomOrder(rows);
    const item = st.items.splice(from, 1)[0];
    st.items.splice(to, 0, item);
    persist(); renderTray(); renderGrid();
  }

  root.querySelector(".aps-tray-clear").onclick = () => {
    if (!st.items.length) return;
    st.items = [];
    persist(); renderTray(); renderGrid();
    toast("手选托盘已清空");
  };

  /* ── 预览 / 写回 ── */
  async function preview() {
    const btn = root.querySelector(".aps-preview-btn");
    btn.disabled = true;
    btn.textContent = "出词中…";
    try {
      const res = await postJSON("/compose", {
        studio_json: JSON.stringify(st), widgets: widgetsOf(node),
      });
      ui.preview = res;
      previewEl.style.display = "";
      previewEl.querySelector(".pos").textContent = res.text || "（空）";
      previewEl.querySelector(".neg").textContent = res.negative || "（无）";
      previewEl.querySelector(".meta").textContent =
        `${res.level_label} · ${res.counts ? JSON.stringify(res.counts) : ""}`;
      pushHistory(res.text || "");
    } catch (e) {
      toast(`出词失败：${e.message}`, "err", 4000);
    } finally {
      btn.disabled = false;
      btn.textContent = "预览出词";
    }
  }

  root.querySelector(".aps-preview-btn").onclick = preview;
  root.querySelector(".aps-apply-btn").onclick = () => {
    saveStudio(node, st);
    app.graph?.setDirtyCanvas(true, true);
    toast("已写回节点：手选顺序 / 模式 / 负面词设置", "ok");
  };
  root.querySelector(".aps-copy-pos").onclick = () =>
    copyText(ui.preview?.text || previewEl.querySelector(".pos").textContent || "");
  root.querySelector(".aps-copy-neg").onclick = () =>
    copyText(ui.preview?.negative || previewEl.querySelector(".neg").textContent || "");

  /* ── 子页签 ── */
  const views = {
    catalog: root.querySelector('[data-view="catalog"]'),
    lora: root.querySelector('[data-view="lora"]'),
    my: root.querySelector('[data-view="my"]'),
    preset: root.querySelector('[data-view="preset"]'),
    ai: root.querySelector('[data-view="ai"]'),
  };
  let loraLoaded = false;
  root.querySelectorAll(".aps-subtab").forEach((b) => {
    b.onclick = () => {
      root.querySelectorAll(".aps-subtab").forEach((x) => x.classList.toggle("on", x === b));
      for (const [k, v] of Object.entries(views)) v.hidden = k !== b.dataset.tab;
      if (b.dataset.tab === "lora" && !loraLoaded) {
        loraLoaded = true;
        ui.loraEditor = new LoraEditor({
          mount: loraMount, entries: st.lora || [],
          onChange: (json, entries) => { st.lora = entries; persist(); },
        });
      }
      if (b.dataset.tab === "my") loadMy();
      if (b.dataset.tab === "preset") renderPresets();
      if (b.dataset.tab === "ai") loadAI();
    };
  });

  /* ── 我的 Tag ── */
  async function loadMy() {
    try {
      const res = await fetchJSON("/studio/my-tags");
      ui.my = res.entries || [];
      renderMy();
    } catch (e) { toast(`我的 Tag 读取失败：${e.message}`, "err"); }
  }
  function renderMy() {
    myList.innerHTML = ui.my.map((e, i) => `
      <div class="aps-my-row">
        <div class="en">${esc(e.en)}</div>
        <div class="zh">${esc(e.zh || "")}</div>
        <span class="aps-badge">${esc(e.slot || "other")}</span>
        <button class="aps-btn small ghost" data-i="${i}">移除</button>
      </div>`).join("") || `<div class="aps-empty">还没有自定义 Tag</div>`;
    myList.querySelectorAll("button[data-i]").forEach((b) => {
      b.onclick = () => { ui.my.splice(+b.dataset.i, 1); renderMy(); };
    });
  }
  async function saveMy() {
    try {
      const res = await postJSON("/studio/my-tags/save", { entries: ui.my });
      ui.my = res.entries || [];
      renderMy();
      toast(`已保存 ${ui.my.length} 条我的 Tag`, "ok");
    } catch (e) { toast(`保存失败：${e.message}`, "err"); }
  }
  root.querySelector(".aps-my-add").onclick = () => {
    const en = root.querySelector(".aps-my-en").value.trim();
    if (!en) { toast("先填英文 tag", "err"); return; }
    ui.my.unshift({
      id: `my:${en}:${Date.now()}`, cat: "我的分类", en,
      zh: root.querySelector(".aps-my-zh").value.trim() || en,
      slot: root.querySelector(".aps-my-slot").value, level: 0,
    });
    root.querySelector(".aps-my-en").value = "";
    root.querySelector(".aps-my-zh").value = "";
    renderMy(); saveMy();
  };
  root.querySelector(".aps-my-from-sel").onclick = () => {
    for (const it of st.items) {
      if (!it.on) continue;
      ui.my.unshift({
        id: `my:${it.en}:${Date.now()}:${Math.random().toString(36).slice(2, 6)}`,
        cat: "手选收藏", en: it.en, zh: it.zh, slot: it.slot, level: 0,
      });
    }
    renderMy(); saveMy();
    toast(`已加入 ${st.items.length} 条`, "ok");
  };

  /* ── 预设 / 历史 ── */
  function renderPresets() {
    const rows = loadPresets();
    const names = Object.keys(rows).sort((a, b) => (rows[b].at || 0) - (rows[a].at || 0));
    let history = [];
    try { history = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]"); } catch (_e) { /* ignore */ }
    presetList.innerHTML = `
      <div class="aps-side-title">手选预设</div>
      ${names.map((n) => `<div class="aps-preset-row">
        <div class="nm">${esc(n)}</div>
        <div class="dt">${rows[n].items?.length || 0} 条</div>
        <button class="aps-btn small ghost" data-load="${esc(n)}">载入</button>
        <button class="aps-btn small danger" data-del="${esc(n)}">删除</button>
      </div>`).join("") || `<div class="aps-empty">还没有预设</div>`}
      <div class="aps-side-title" style="margin-top:10px">最近预览（${history.length}）</div>
      ${history.map((h, i) => `<div class="aps-preset-row">
        <div class="nm" style="font-size:11px;color:var(--aps-dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(h.text)}</div>
        <button class="aps-btn small ghost" data-hist="${i}">复制</button>
      </div>`).join("") || `<div class="aps-empty">还没有历史</div>`}`;
    presetList.querySelectorAll("[data-load]").forEach((b) => {
      b.onclick = () => {
        const rec = loadPresets()[b.dataset.load];
        if (!rec) return;
        st.mode = rec.mode || st.mode;
        st.items = rec.items || [];
        st.order = rec.order || "slot";
        st.quality_prefix = rec.quality_prefix || "";
        st.extra_text = rec.extra_text || "";
        st.negative_preset = rec.negative_preset || "standard";
        st.negative_extra = rec.negative_extra || "";
        st.lora = rec.lora || [];
        syncMode();
        root.querySelector(".aps-order").value = st.order;
        root.querySelector(".aps-qprefix").value = st.quality_prefix;
        root.querySelector(".aps-extra").value = st.extra_text;
        root.querySelector(".aps-negpreset").value = st.negative_preset;
        root.querySelector(".aps-negextra").value = st.negative_extra;
        persist(); renderTray(); renderGrid();
        toast(`已载入「${b.dataset.load}」`, "ok");
      };
    });
    presetList.querySelectorAll("[data-del]").forEach((b) => {
      b.onclick = () => {
        const rows2 = loadPresets();
        delete rows2[b.dataset.del];
        savePresets(rows2); renderPresets();
      };
    });
    presetList.querySelectorAll("[data-hist]").forEach((b) => {
      b.onclick = () => copyText(history[+b.dataset.hist]?.text || "");
    });
  }
  root.querySelector(".aps-preset-save").onclick = () => {
    const name = prompt("预设名：", `手选 ${new Date().toLocaleString()}`);
    if (!name) return;
    const rows = loadPresets();
    rows[name] = { ...st, at: Date.now() };
    savePresets(rows);
    renderPresets();
    toast(`预设「${name}」已保存`, "ok");
  };
  root.querySelector(".aps-preset-export").onclick = () =>
    downloadText("anima-prompt-preset.json", JSON.stringify(st, null, 2));
  root.querySelector(".aps-preset-import").onclick = () => {
    const input = document.createElement("input");
    input.type = "file"; input.accept = ".json,application/json";
    input.onchange = () => {
      const f = input.files?.[0];
      if (!f) return;
      const reader = new FileReader();
      reader.onload = () => {
        try {
          const data = JSON.parse(String(reader.result || ""));
          Object.assign(st, data);
          syncMode(); persist(); renderTray(); renderGrid();
          toast("已导入", "ok");
        } catch (e) { toast(`导入失败：${e.message}`, "err"); }
      };
      reader.readAsText(f, "utf-8");
    };
    input.click();
  };

  /* ── AI ── */
  async function loadAI() {
    aiEl.innerHTML = `<div class="aps-hint">读取中…</div>`;
    try {
      const stAI = await fetchJSON("/ai/status");
      const providers = (stAI.providers || []).map((p) => `
        <div class="aps-ai-provider">
          <span class="dot ${p.available ? "on" : ""}"></span>
          <b>${esc(p.label)}</b>
          <span class="aps-hint">${esc(p.id)} · ${esc(p.reason || "")}</span>
        </div>`).join("");
      aiEl.innerHTML = `
        <div class="aps-ai-card">
          <h4>AI 功能：${stAI.enabled ? '<span style="color:var(--aps-ok)">已启用</span>'
            : '<span class="aps-ai-off">暂缓 / 未启用</span>'}</h4>
          <div class="aps-hint">${esc(stAI.message || "")}</div>
          <div style="margin-top:10px">${providers || '<div class="aps-hint">没有注册 provider</div>'}</div>
        </div>
        <div class="aps-ai-card">
          <h4>接口契约（已预留，随时可接）</h4>
          <div class="aps-code">${esc(JSON.stringify(stAI.contract || {}, null, 2))}</div>
          <div class="aps-hint" style="margin-top:8px">
            未来接入方式：实现 <b>ai_bridge.AIProvider</b> 子类 → 注册 provider →
            在 <b>ComfyUI/user/anima_prompt_studio/ai_providers.json</b> 里打开 enabled。
            本版本不会发起任何 AI 网络请求。
          </div>
        </div>
        <div class="aps-ai-card">
          <h4>需求描述（占位输入）</h4>
          <textarea class="aps-input" style="width:100%;min-height:80px"
            placeholder="例如：把当前手选扩写成更自然的英文提示词，保留角色特征…"></textarea>
          <div class="aps-row" style="margin-top:8px">
            <button class="aps-btn" disabled>AI 增强（未启用）</button>
            <button class="aps-btn" disabled>AI 推荐标签（未启用）</button>
            <span class="aps-hint">按钮故意禁用：等 provider 接好再开</span>
          </div>
        </div>`;
    } catch (e) {
      aiEl.innerHTML = `<div class="aps-hint">AI 状态读取失败：${esc(e.message)}</div>`;
    }
  }

  renderTray();
  // 关闭面板时立即落盘，避免 300ms debounce 与“关闭后马上排队”的竞态
  modal.onClose = () => saveStudio(node, st);
  modal.show();
  return modal;
}

function ensureStylesStudio() {
  ensureStyles();
  ensureStudioStyles();
}

/* ── 选择器节点面板 ───────────────────────────────────────────── */
export function openSelector(node) {
  let existing = [];
  try { existing = JSON.parse(wval(node, "picked_json", "[]") || "[]"); } catch (_e) { existing = []; }
  if (!Array.isArray(existing)) existing = [];
  openCatalogPicker({
    title: "选择标签（可多选）",
    category: wval(node, "category", ""),
    multi: true,
    items: existing,
    onPick: (rows) => {
      wset(node, "picked_json", JSON.stringify(rows.map((r) => ({
        id: r.id, cat: r.cat, en: r.en, zh: r.zh, slot: r.slot,
      }))));
      app.graph?.setDirtyCanvas(true, true);
      toast(`已选择 ${rows.length} 条标签`, "ok");
    },
  });
}

/* ── 多提示词框面板 ───────────────────────────────────────────── */
export function openBoxes(node) {
  let boxes = [];
  try { boxes = JSON.parse(wval(node, "boxes_json", "[]") || "[]"); } catch (_e) { boxes = []; }
  if (!Array.isArray(boxes)) boxes = [];
  const modal = new Modal({
    title: "多提示词框 · 每框可独立开关 / 排序",
    width: "min(1080px, 94vw)", height: "min(82vh, 760px)",
  });
  modal.body.style.padding = "12px 14px";
  modal.body.innerHTML = `
    <div class="aps-row" style="margin-bottom:8px">
      <button class="aps-btn primary aps-box-add">＋ 新增框</button>
      <button class="aps-btn ghost aps-box-pick">从目录选词（加入当前框）</button>
      <span class="aps-hint">框内支持逗号分隔；拖动排序 = 输出顺序</span>
    </div>
    <div class="aps-box-list" style="flex:1;overflow:auto;display:flex;flex-direction:column;gap:6px"></div>`;
  const list = modal.body.querySelector(".aps-box-list");
  let active = 0;
  let dragFrom = -1;

  function render() {
    const rows = boxes.length ? boxes : [{ text: "", on: true, title: "框 1" }];
    if (!boxes.length) boxes = rows;
    list.innerHTML = rows.map((b, i) => `
      <div class="aps-sel" draggable="true" data-i="${i}" style="align-items:flex-start">
        <span class="grip">⋮⋮</span>
        <span class="idx">${i + 1}</span>
        <div class="body">
          <div class="aps-row">
            <input class="aps-input aps-box-title" data-k="title" value="${esc(b.title || `框 ${i + 1}`)}" style="width:120px">
            <label class="aps-check"><input type="checkbox" data-k="on" ${b.on === false ? "" : "checked"}>启用</label>
            <button class="aps-btn small ghost" data-act="del">✕</button>
          </div>
          <textarea class="aps-input aps-box-text" data-k="text" style="width:100%;min-height:42px"
            placeholder="这一框的提示词…">${esc(b.text || "")}</textarea>
        </div>
      </div>`).join("");
    list.querySelectorAll(".aps-sel").forEach((el) => {
      const i = +el.dataset.i;
      el.onclick = () => { active = i; };
      el.querySelectorAll("[data-k]").forEach((inp) => {
        inp.onchange = () => {
          const k = inp.dataset.k;
          if (k === "on") boxes[i].on = inp.checked;
          else boxes[i][k] = inp.value;
        };
      });
      el.querySelector('[data-act="del"]').onclick = () => { boxes.splice(i, 1); render(); };
      el.ondragstart = (ev) => { dragFrom = i; try { ev.dataTransfer.setData("text/plain", String(i)); } catch (_e) { /* ignore */ } };
      el.ondragover = (ev) => ev.preventDefault();
      el.ondrop = (ev) => {
        ev.preventDefault();
        if (dragFrom < 0 || dragFrom === i) return;
        const item = boxes.splice(dragFrom, 1)[0];
        boxes.splice(i, 0, item);
        render();
      };
    });
  }

  modal.body.querySelector(".aps-box-add").onclick = () => {
    boxes.push({ text: "", on: true, title: `框 ${boxes.length + 1}` });
    render();
  };
  modal.body.querySelector(".aps-box-pick").onclick = () => {
    openCatalogPicker({
      title: "把标签加入当前框", multi: true,
      onPick: (rows) => {
        const txt = rows.map((r) => r.en).join(", ");
        const cur = boxes[active] || boxes[0];
        if (!cur) return;
        cur.text = cur.text ? `${cur.text}, ${txt}` : txt;
        render();
      },
    });
  };
  modal.foot.innerHTML = `
    <div class="aps-foot-left">输出时只拼启用框，按上面的顺序。</div>
    <div class="aps-foot-right">
      <button class="aps-btn ghost" data-x="cancel">取消</button>
      <button class="aps-btn primary" data-x="ok">保存到节点</button>
    </div>`;
  modal.foot.querySelector('[data-x="cancel"]').onclick = () => modal.close();
  modal.foot.querySelector('[data-x="ok"]').onclick = () => {
    wset(node, "boxes_json", JSON.stringify(boxes));
    app.graph?.setDirtyCanvas(true, true);
    toast("多框内容已写入节点", "ok");
    modal.close();
  };
  modal.show();
  render();
  return modal;
}

/* ── 节点按钮 / 隐藏控件 ─────────────────────────────────────── */
export function installNodeHooks(nodeType, nodeData) {
  const name = nodeData.name;
  const isStudio = name === "AnimaPromptStudio";
  const isSelector = name === "AnimaPromptStudioSelector";
  const isBoxes = name === "AnimaPromptStudioBoxes" || name === "AnimaPromptStudioBoxesEncode";
  const isLora = name === "AnimaLoraStack";
  if (!isStudio && !isSelector && !isBoxes && !isLora) return;

  const onCreated = nodeType.prototype.onNodeCreated;
  nodeType.prototype.onNodeCreated = function () {
    const r = onCreated ? onCreated.apply(this, arguments) : undefined;
    if (isStudio) {
      hideWidget(this, "studio_json");
      // 手选状态由面板维护；节点上只保留模式与手写补充
      const mk = (text, tip, fn) => {
        const b = this.addWidget("button", text, null, fn);
        b.serialize = false; b.tooltip = tip;
      };
      mk("🎨 打开提示词工坊", "自由选择 / 混合 / 预览 / LoRA 顺序", () => openStudio(this));
      mk("📋 复制上次预览", "把最近一次预览的正向词复制到剪贴板", () => {
        let rows = [];
        try { rows = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]"); } catch (_e) { /* ignore */ }
        copyText(rows[0]?.text || "");
      });
    }
    if (isSelector) {
      hideWidget(this, "picked_json");
      const b = this.addWidget("button", "🎯 打开标签选择器", "从目录多选，写回 picked_json", () => openSelector(this));
      b.serialize = false;
    }
    if (isBoxes) {
      hideWidget(this, "boxes_json");
      const b = this.addWidget("button", "🧩 编辑多提示词框", "新增 / 排序 / 开关", () => openBoxes(this));
      b.serialize = false;
    }
    if (isLora) {
      hideWidget(this, "lora_list_json");
      const b = this.addWidget("button", "🔗 打开 LoRA 排序面板", "拖拽调整实际加载顺序", () => {
        import("./lora_panel.js").then((m) => m.openLoraModal(this));
      });
      b.serialize = false;
    }
    return r;
  };
}
