const json = (obj, status = 200) => new Response(JSON.stringify(obj), {
  status,
  headers: { "Content-Type": "application/json" },
});

const ITEMS = [
  { id: "quality:masterpiece", cat: "quality", en: "masterpiece", zh: "杰作", slot: "quality", level: 0, src: "v6", thumb: "", tags: [] },
  { id: "quality:best-quality", cat: "quality", en: "best quality", zh: "最佳质量", slot: "quality", level: 0, src: "v6", thumb: "", tags: [] },
  { id: "v6:hair:long hair", cat: "v6:hair", en: "long hair", zh: "长发", slot: "hair", level: 0, src: "v6", thumb: "", tags: [] },
  { id: "v6:hair:twintails", cat: "v6:hair", en: "twintails", zh: "双马尾", slot: "hair", level: 0, src: "v6", thumb: "", tags: [] },
  { id: "v6:camera:from above", cat: "v6:camera", en: "from above", zh: "俯视", slot: "camera", level: 0, src: "v6", thumb: "", tags: [] },
  { id: "v6:camera:from below", cat: "v6:camera", en: "from below", zh: "仰视", slot: "camera", level: 0, src: "v6", thumb: "", tags: [] },
  { id: "v6char:hatsune_miku", cat: "v6char", en: "hatsune miku", zh: "初音未来", slot: "character", level: 0, src: "v6", thumb: "hatsune_miku", tags: [] },
  { id: "v6char:kagamine_rin", cat: "v6char", en: "kagamine rin", zh: "镜音铃", slot: "character", level: 0, src: "v6", thumb: "kagamine_rin", tags: [] },
  { id: "artist:test", cat: "artist", en: "@test", zh: "test", slot: "artist", level: 0, src: "tools", thumb: "", tags: [] },
  { id: "v6:cloth_sfw:school uniform", cat: "v6:cloth_sfw", en: "school uniform", zh: "校服", slot: "clothing", level: 0, src: "v6", thumb: "", tags: [] },
  { id: "v6:pose_sfw:standing", cat: "v6:pose_sfw", en: "standing", zh: "站姿", slot: "pose", level: 0, src: "v6", thumb: "", tags: [] },
  { id: "v6:scene:classroom", cat: "v6:scene", en: "classroom", zh: "教室", slot: "scene", level: 0, src: "v6", thumb: "", tags: [] },
];

const META = {
  total: ITEMS.length,
  counts: {
    quality: 2,
    "v6:hair": 2,
    "v6:camera": 2,
    v6char: 2,
    artist: 1,
    "v6:cloth_sfw": 1,
    "v6:pose_sfw": 1,
    "v6:scene": 1,
  },
  groups: [
    { id: "base", title: "基础词库", cats: [
      { key: "quality", label: "✨ 质量与风格", count: 2 },
      { key: "v6:hair", label: "① 头发", count: 2 },
      { key: "v6:camera", label: "⑧ 镜头", count: 2 },
    ] },
    { id: "materials", title: "素材库", cats: [
      { key: "v6char", label: "角色", count: 2 },
      { key: "artist", label: "画师", count: 1 },
    ] },
    { id: "scenes", title: "场景与构图", cats: [
      { key: "v6:scene", label: "场景", count: 1 },
    ] },
  ],
};

export const api = {
  async fetchApi(url, opts = {}) {
    const u = new URL(url, location.href);
    const path = u.pathname;
    const method = (opts.method || "GET").toUpperCase();
    if (path.endsWith("/catalog/meta")) return json(META);
    if (path.endsWith("/catalog/items")) {
      const cat = u.searchParams.get("cat") || "";
      const q = (u.searchParams.get("q") || "").toLowerCase();
      const src = u.searchParams.get("src") || "";
      const page = Number(u.searchParams.get("page") || 1);
      const limit = Number(u.searchParams.get("limit") || 60);
      let rows = ITEMS.filter((it) => (!cat || it.cat === cat) && (!src || it.src === src) && (!q || it.en.includes(q) || it.zh.includes(q)));
      const total = rows.length;
      rows = rows.slice((page - 1) * limit, page * limit);
      return json({ total, page, limit, items: rows });
    }
    if (path.endsWith("/catalog/random")) {
      const cat = u.searchParams.get("cat") || "";
      const src = u.searchParams.get("src") || "";
      const q = (u.searchParams.get("q") || "").toLowerCase();
      const rows = ITEMS.filter((it) => (!cat || it.cat === cat) && (!src || it.src === src) && (!q || it.en.includes(q) || it.zh.includes(q)));
      const item = rows.length ? rows[Math.floor(Math.random() * rows.length)] : null;
      return json({ ok: true, item });
    }
    if (path.endsWith("/catalog/by-ids")) {
      const body = JSON.parse(opts.body || "{}");
      const ids = body.ids || [];
      return json({ ok: true, items: ITEMS.filter((it) => ids.includes(it.id)) });
    }
    if (path.endsWith("/compose")) {
      const body = JSON.parse(opts.body || "{}");
      const st = typeof body.studio_json === "string"
        ? JSON.parse(body.studio_json || "{}")
        : (body.studio_json || {});
      const items = (st.items || []).map((it) => it.en).filter(Boolean);
      const text = [st.quality_prefix, ...items].filter(Boolean).join(", ");
      return json({
        ok: true, text, negative: "lowres, bad anatomy, nsfw, explicit",
        level: "sfw", level_num: 0, level_label: "0 · 全年龄",
        cn_summary: (st.items || []).map((it) => it.zh || it.en).filter(Boolean).join("、"),
        report: "手选模式报告\n标签数 : " + items.length,
        counts: { manual: items.length, total: items.length }, fixes: [],
      });
    }
    if (path.endsWith("/studio/favorites")) return json({ ok: true, ids: ["v6char:hatsune_miku"], items: [] });
    if (path.endsWith("/studio/favorites/toggle")) return json({ ok: true, ids: ["v6char:hatsune_miku"] });
    if (path.endsWith("/studio/my-tags")) return json({ ok: true, items: [{ en: "my tag", zh: "我的", slot: "general" }] });
    if (path.endsWith("/studio/my-tags/save")) return json({ ok: true });
    if (path.endsWith("/loras")) return json({ ok: true, items: [
      { name: "anima-turbo-lora-v0.2.safetensors", size: 148902616, trigger: "", favorite: false },
      { name: "style-a.safetensors", size: 91867112, trigger: "style a", favorite: true },
      { name: "character-b.safetensors", size: 138764376, trigger: "character b", favorite: false },
    ] });
    if (path.endsWith("/loras/stacks")) return json({ ok: true, stacks: {} });
    if (path.endsWith("/loras/stacks/save")) return json({ ok: true });
    if (path.endsWith("/loras/stacks/delete")) return json({ ok: true });
    if (path.endsWith("/loras/meta")) return json({ ok: true });
    if (path.endsWith("/ai/status")) return json({
      enabled: false, default: "null",
      providers: [{ id: "null", label: "未启用（占位）", available: false,
        reason: "AI 功能尚未启用；接口已预留，接入 provider 后自动开放。", capabilities: [] }],
      message: "AI 功能暂缓；接口与 provider 注册表已就绪。",
      contract: { version: 1, request: { task: "enhance | suggest | translate | critique" }, response: { ok: "boolean" } },
    });
    return json({ ok: true });
  },
};
