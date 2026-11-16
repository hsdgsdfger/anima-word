# -*- coding: utf-8 -*-
"""anima-word :: 内部提示词解耦引擎

本文件由 ComfyUI-AnimaPromptDecoupler 1.2.0 的 decouple.py 并入，
作为 anima-word 的内部模块使用；不注册节点、不提供 UI。

输入：Anima Wardrobe V6「提示词随机生成」节点吐出来的那段正文。
输出：三份不依赖本插件（也不依赖 V6）就能直接用的提示词。

为什么要解耦
------------
V6 的正文是给 Anima 底模吃的 caption 风格 —— 里面混着三类东西：

  1. 标准 danbooru tag      `hu tao, long hair, red eyes`      → 任何模型都认
  2. 整句英文自然语言描述   `she stands in a door frame with …`  → 只有 Anima 系认
  3. 质量词尾巴             `masterpiece, very aesthetic`       → 通用

第 2 类是最要命的：粘到 WebUI / 别的 ComfyUI 工作流里，SD1.5 和 SDXL 基本当噪声，
还会挤占 CLIP 的 77 token 预算。本模块干的事就是把它拆开、压回成 tag，
再按「人数 → 角色 → 外观 → 服装 → 姿态 → 镜头 → 场景 → 光影 → 风格 → 质量」
的固定顺序重排，去重，顺带生成一份英文自然语言版（Flux / SD3 / GPT-image 那类
吃句子的模型用）和一份中文摘要（人看的）。

设计约束
--------
· 纯标准库，import 阶段不依赖 ComfyUI 任何东西 —— 单测可以直接跑。
· 只用规则，不联网、不调模型：结果确定、可复现、可审。
· 绝不改输入字符串（纯函数），调用方拿到的是新对象。
"""

import re

# ---------------------------------------------------------------------------
# 分组定义（顺序即输出顺序）
# ---------------------------------------------------------------------------

GROUP_ORDER = [
    ("quality", "质量"),
    ("count", "人数"),
    ("character", "角色"),
    ("appearance", "外观"),
    ("clothing", "服装"),
    ("pose", "姿态"),
    ("camera", "镜头"),
    ("scene", "场景"),
    ("light", "光影"),
    ("style", "风格"),
    ("other", "其它"),
]

GROUP_CN = dict(GROUP_ORDER)

# ---------------------------------------------------------------------------
# 词典（全部小写；匹配用 word boundary，避免 hat 命中 what）
# ---------------------------------------------------------------------------

QUALITY_WORDS = {
    "masterpiece", "best quality", "amazing quality", "good quality",
    "normal quality", "worst quality", "low quality", "highres", "absurdres",
    "high resolution", "very aesthetic", "aesthetic", "newest", "ultra detailed",
    "extremely detailed", "detailed", "8k", "4k", "sharp focus", "best shadow",
    "very awa", "very aesthetic", "score_9", "score_8_up", "score_7_up",
}

COUNT_WORDS = {
    "solo", "1girl", "2girls", "3girls", "multiple girls", "1boy", "2boys",
    "multiple boys", "male focus", "no humans", "1other", "6+girls",
}

CHARACTER_HINTS = {
    "genshin impact", "honkai: star rail", "honkai impact 3rd", "zenless zone zero",
    "arknights", "azur lane", "blue archive", "fate/grand order", "girls' frontline",
    "kantai collection", "idolmaster", "love live!", "bang dream!", "project sekai",
    "nikke", "reverse: 1999", "wuthering waves", "vocaloid", "touhou",
    "original", "granblue fantasy", "umamusume", "princess connect!",
}

CAMERA_WORDS = {
    "full body", "cowboy shot", "upper body", "lower body", "close-up",
    "portrait", "from side", "from above", "from below", "from behind",
    "front view", "profile", "wide shot", "medium shot", "depth of field",
    "deep focus", "shallow depth of field", "blurry", "vignetting",
    "dutch angle", "fisheye", "pov", "panorama", "landscape", "close up",
    "cowboy shot", "very close-up", "dutch angle", "bokeh",
}

POSE_WORDS = {
    "standing", "sitting", "kneeling", "lying", "on back", "on stomach",
    "on side", "walking", "running", "stretching", "leaning forward",
    "leaning back", "arms up", "arm up", "hand up", "hands on own thighs",
    "hands on hips", "hand on hip", "crossed arms", "head tilt",
    "looking ahead", "looking to the side", "looking away", "looking at viewer",
    "looking back", "looking down", "looking up", "eyes closed", "open mouth",
    "smile", "confused", "blush", "parted lips", "spread legs", "hugging own legs",
    "wariza", "seiza", "fetal position", "arched back", "hands on frame",
    "reaching out", "waving", "holding", "hand on own chest", "self hug",
    "squatting", "crawling", "knees up", "legs together",
    "arms", "arm", "back", "chest forward", "shoulders back", "head down",
    "arms wide", "arms crossed",
    "legs crossed", "knees together", "tiptoes", "on tiptoes",
}

SCENE_WORDS = {
    "on bed", "bed", "window", "doorway", "door", "door frame", "indoors",
    "outdoors", "room", "bedroom", "classroom", "office", "bathroom",
    "kitchen", "couch", "sofa", "chair", "floor", "wall", "background",
    "scenery", "city", "city lights", "cityscape", "skyline", "starry sky",
    "night sky", "sky", "stars", "street", "beach", "forest", "garden",
    "mountain", "ocean", "sea", "snow", "rain", "night", "dusk", "dawn",
    "sunset", "ruins", "temple", "shrine", "library", "cafe", "stage",
    "pool", "onsen", "bath", "balcony", "rooftop", "alley", "cave",
}

LIGHT_WORDS = {
    "morning", "morning light", "sunlight", "backlight", "backlighting",
    "rim light", "shadow", "shadows", "glow", "neon", "neon lights",
    "moonlight", "candlelight", "god rays", "lens flare", "soft lighting",
    "cinematic lighting", "dramatic lighting", "volumetric lighting",
    "golden hour", "blue hour", "dim lighting", "spotlight",
}

STYLE_WORDS = {
    "illustration", "anime", "anime style", "watercolor", "oil painting",
    "sketch", "lineart", "monochrome", "greyscale", "colorful", "vivid",
    "surreal", "art nouveau", "ukiyo-e", "cinematic", "photorealistic",
    "realistic", "3d", "3d render", "pixel art", "chibi", "flat color",
    "official art", "concept art", "matte painting", "retro", "vaporwave",
}

CLOTHING_WORDS = {
    "dress", "skirt", "shirt", "t-shirt", "blouse", "kimono", "yukata",
    "hanfu", "qipao", "cheongsam", "bikini", "swimsuit", "one-piece swimsuit",
    "jacket", "coat", "parka", "hoodie", "sweater", "knitwear", "cardigan",
    "uniform", "school uniform", "sailor collar", "serafuku", "suit", "tie",
    "hat", "cap", "beret", "top hat", "socks", "thighhighs", "pantyhose",
    "stockings", "tights", "boots", "shoes", "heels", "high heels", "sandals",
    "sneakers", "loafers", "gloves", "ribbon", "bow", "bowtie", "choker",
    "necklace", "earrings", "sunglasses", "glasses", "bracelet", "ring",
    "lingerie", "underwear", "bra", "panties", "pajamas", "robe",
    "nightgown", "sleeping kimono", "apron", "armor", "cape", "scarf",
    "belt", "sash", "obi", "veil", "halo", "hair flower", "hairpin",
    "headband", "hairband", "hair ornament", "hair ribbon", "collar",
    "fur trim", "lace", "frills", "zipper", "buttons", "waist chain",
    "jacket around waist", "off shoulder", "bare shoulders", "cleavage",
    "bare shoulder", "off-shoulder", "shoulder cutout",
    "midriff", "navel", "backless", "see-through", "wet clothes",
}

APPEARANCE_RE = re.compile(
    r"\b(hair|haired|eyes?|pupils?|bangs|skin|complexion|breasts?|bust|"
    r"eyelashes|lips|freckles|mole|nail polish|nails|tall|petite|muscular|"
    r"slender|curvy|tattoo|scar|horns?|animal ears|cat ears|fox ears|"
    r"tail|wings?|halo|twintails?|ponytail|braid|bob cut|hime cut|"
    r"collarbone|clavicle|abs|waist|hips|thighs|"
    r"ahoge|sidelocks|multicolored hair|gradient hair|streaked hair)\b"
)

# 自然语言句 → tag 的规则表：(正则, 输出 tag 列表)
# 顺序有讲究：具体的排在泛化的前面（door frame 先于 door）。
NL_RULES = [
    (r"\bdoor\s*frame|\bdoorframe|\bin a doorway", ["doorway"]),
    (r"\bforearms?\b", ["arms"]),
    (r"\bshoulder blades?\b", ["back"]),
    (r"\bchest leans forward|\bleans forward|\bleaning forward", ["leaning forward"]),
    (r"\bshoulders? (are )?(pulled|pressed) back", ["arched back"]),
    (r"\bcollar slips|\bslips off (her|his|one) shoulder|\boff (her|his|one) shoulder",
     ["off shoulder", "bare shoulder"]),
    (r"\bhands? on (her|his|their) (own )?thighs", ["hands on own thighs"]),
    (r"\bkneel(s|ing)?\b", ["kneeling"]),
    (r"\b(on|upon) the bed\b", ["on bed"]),
    (r"\bstarry sky|\bstar-filled", ["starry sky"]),
    (r"\bcity lights?\b", ["city lights"]),
    (r"\bmorning light|\bmorning sun", ["morning", "sunlight"]),
    (r"\bsunset|\bdusk\b", ["sunset"]),
    (r"\bmoonlight\b", ["moonlight"]),
    (r"\bwindow\b", ["window"]),
    (r"\bsleeping kimono\b", ["sleeping kimono"]),
    (r"\bkimono\b", ["kimono"]),
    (r"\bsunglasses\b", ["sunglasses"]),
    (r"\bknit", ["knitwear"]),
    (r"\bjacket (tied )?around (her|his|the) waist", ["jacket around waist"]),
    (r"\bhand (is )?(up|raised)", ["hand up"]),
    (r"\blooking (to|at) the side", ["looking to the side"]),
    (r"\blooking to one side", ["looking to the side"]),
    (r"\bseen from the side|\bfrom the side", ["from side"]),
    (r"\bfull[- ]body\b", ["full body"]),
    (r"\bcowboy shot\b", ["cowboy shot"]),
    (r"\bstands?\b|\bstanding\b", ["standing"]),
    (r"\bsits?\b|\bsitting\b|\bseated\b", ["sitting"]),
    (r"\bwalk(s|ing)?\b", ["walking"]),
    (r"\blies?\b|\blying\b", ["lying"]),
    (r"\bstretch(es|ing)?\b", ["stretching"]),
    (r"\bsmil(e|es|ing)\b", ["smile"]),
    (r"\bblush(es|ing)?\b", ["blush"]),
    (r"\bconfused\b|\bpuzzled\b", ["confused"]),
    (r"\btentacles?\b", ["tentacles"]),
    (r"\bblack background\b|\bdark background\b", ["dark background"]),
    (r"\bbutterfl(y|ies)\b", ["butterfly"]),
    (r"\bflower pattern\b", ["flower pattern"]),
    (r"\beye pattern\b", ["eye pattern"]),
    (r"\btwo (girls|people|women)\b", ["2girls"]),
    (r"\bone (girl|woman)\b", ["1girl"]),
]

PRONOUN_START = re.compile(r"^(she|he|they|it|the girl|the woman|her|his)\b", re.I)
SENTENCE_END = re.compile(r"[.!?]\s*$")

# 中文词典（tag → 中文）。查不到就原样输出英文，不做机器翻译。
CN_DICT = {
    # 人数
    "1girl": "单人少女", "solo": "独自一人", "2girls": "两名少女",
    "multiple girls": "多名少女", "1boy": "单人男性", "male focus": "男性主体",
    "no humans": "无人物",
    # 外观
    "porcelain skin": "瓷白肤色", "dark skin": "深色皮肤", "brown skin": "棕色皮肤",
    "pale skin": "苍白肤色", "brown hair": "棕色头发", "black hair": "黑色头发",
    "blonde hair": "金发", "silver hair": "银发", "white hair": "白发",
    "red hair": "红发", "pink hair": "粉发", "blue hair": "蓝发",
    "purple hair": "紫发", "green hair": "绿发", "grey hair": "灰发",
    "long hair": "长发", "very long hair": "超长发", "short hair": "短发",
    "medium hair": "中长发", "wavy hair": "波浪卷发", "straight hair": "直发",
    "twin tails": "双马尾", "twintails": "双马尾", "ponytail": "马尾",
    "braid": "辫子", "braided hair": "编发", "parted bangs": "中分刘海",
    "bangs": "刘海", "ahoge": "呆毛", "sidelocks": "侧发",
    "red eyes": "红瞳", "purple eyes": "紫瞳", "blue eyes": "蓝瞳",
    "green eyes": "绿瞳", "golden eyes": "金瞳", "yellow eyes": "黄瞳",
    "flower-shaped pupils": "花朵状瞳孔", "medium breasts": "中等胸围",
    "large breasts": "丰满胸围", "small breasts": "娇小胸围",
    "nail polish": "指甲油", "tattoo": "纹身", "mole under eye": "眼下泪痣",
    "visible collarbone": "可见锁骨", "collarbone": "锁骨",
    # 服装
    "top hat": "高礼帽", "hat": "帽子", "red hair flower": "红色发花",
    "hair flower": "发花", "hairpin": "发夹", "headband": "发带",
    "sleeping kimono": "睡袍和服", "kimono": "和服", "yukata": "浴衣",
    "knitwear": "针织衫", "jacket around waist": "腰间系外套",
    "sunglasses": "墨镜", "glasses": "眼镜", "dress": "连衣裙",
    "skirt": "裙子", "bikini": "比基尼", "swimsuit": "泳装",
    "thighhighs": "过膝袜", "socks": "袜子", "boots": "靴子",
    "high heels": "高跟鞋", "ribbon": "丝带", "choker": "颈链",
    "off shoulder": "露肩", "bare shoulder": "裸露肩部", "bare shoulders": "露肩",
    "cleavage": "乳沟", "fur trim": "毛边装饰", "uniform": "制服",
    "maid": "女仆装", "apron": "围裙", "veil": "头纱",
    # 姿态
    "standing": "站立", "sitting": "坐姿", "kneeling": "跪姿", "lying": "躺卧",
    "stretching": "伸展", "leaning forward": "身体前倾", "arched back": "背部后弓",
    "hands on frame": "双手扶门框", "hands on own thighs": "双手放于大腿",
    "hand up": "单手抬起", "arms wide": "双臂张开", "arms up": "双臂上举",
    "confused": "神情疑惑", "looking ahead": "目视前方",
    "looking to the side": "侧目", "looking at viewer": "看向镜头",
    "looking away": "视线移开", "smile": "微笑", "blush": "脸红",
    "open mouth": "张嘴", "closed eyes": "闭眼", "head tilt": "歪头",
    "hugging own legs": "抱膝", "wariza": "鸭子坐", "seiza": "正坐",
    "arms": "双臂", "arm": "手臂", "back": "背部", "chest forward": "胸口前挺",
    "doorway stretch": "门口伸展", "glow": "光晕",
    # 镜头
    "full body": "全身构图", "cowboy shot": "七分身构图", "upper body": "上半身",
    "close-up": "特写", "portrait": "半身肖像", "from side": "侧面视角",
    "from above": "俯视", "from below": "仰视", "from behind": "背面视角",
    "deep focus": "深景深", "depth of field": "景深虚化", "blurry": "虚化",
    "vignetting": "暗角", "pov": "第一人称视角", "dutch angle": "斜角构图",
    # 场景
    "doorway": "门口", "door frame": "门框", "on bed": "床上", "bed": "床",
    "window": "窗边", "room": "室内", "indoors": "室内", "outdoors": "室外",
    "city lights": "城市灯火", "starry sky": "星空", "night sky": "夜空",
    "cityscape": "城市景观", "skyline": "天际线", "street": "街道",
    "beach": "海滩", "forest": "森林", "garden": "花园", "bath": "浴室",
    "background": "背景", "scenery": "风景",
    # 光影
    "morning": "清晨", "morning light": "晨光", "sunlight": "日光",
    "backlight": "逆光", "rim light": "轮廓光", "shadow": "阴影",
    "moonlight": "月光", "neon": "霓虹", "golden hour": "黄金时刻",
    "cinematic lighting": "电影感布光", "soft lighting": "柔光",
    # 风格 / 质量
    "masterpiece": "杰作", "best quality": "最佳质量", "very aesthetic": "极佳美感",
    "highres": "高分辨率", "absurdres": "超高分辨率", "illustration": "插画",
    "anime": "动画风", "cinematic": "电影感", "colorful": "色彩鲜艳",
    "surreal": "超现实", "tentacles": "触手", "dark background": "深色背景",
    "black background": "纯黑背景", "flower pattern": "花纹", "eye pattern": "眼纹",
    "butterfly": "蝴蝶",
}

# 默认负向（通用、任何 SD 系模型都能吃）
# 作品名 / 常见角色名的中文（查不到就保留英文 —— 不硬翻，翻错比不翻更糟）
WORK_CN = {
    "genshin impact": "原神", "honkai: star rail": "崩坏：星穹铁道",
    "honkai impact 3rd": "崩坏3", "zenless zone zero": "绝区零",
    "arknights": "明日方舟", "azur lane": "碧蓝航线", "blue archive": "蔚蓝档案",
    "fate/grand order": "FGO", "girls' frontline": "少女前线",
    "kantai collection": "舰队Collection", "nikke": "胜利女神", "touhou": "东方",
    "vocaloid": "VOCALOID", "wuthering waves": "鸣潮", "original": "原创",
    "umamusume": "赛马娘", "reverse: 1999": "重返未来1999",
}

NAME_CN = {
    "hu tao": "胡桃", "firefly": "流萤", "raiden shogun": "雷电将军",
    "ganyu": "甘雨", "keqing": "刻晴", "hutao": "胡桃", "fischl": "菲谢尔",
    "march 7th": "三月七", "kafka": "卡芙卡", "seele": "希儿", "bronya": "布洛妮娅",
    "silver wolf": "银狼", "jingliu": "镜流", "acheron": "黄泉", "sparkle": "花火",
    "asuka": "明日香", "rei ayanami": "绫波丽", "miku hatsune": "初音未来",
    "rem": "雷姆", "ram": "拉姆", "emilia": "爱蜜莉雅", "saber": "Saber",
    "artoria pendragon": "阿尔托莉雅", "mash kyrielight": "玛修",
}

# ---------------------------------------------------------------------------
# 年龄分级判定（五档，与 V6 的 nsfw_level 逐档对齐）
# ---------------------------------------------------------------------------

RATING_ORDER = ["l0", "l1", "l2", "l3", "l4"]

RATING_LABELS = {
    "l0": ("全年龄", "s"),
    "l1": ("暗示", "q"),
    "l2": ("露骨", "e"),
    "l3": ("硬核", "e"),
    "l4": ("极端", "e"),
}

# V6 档位 key → 本地五档。`any` 不设上限，按最严处理。
LEVEL_TO_RATING = {
    "sfw": "l0", "suggestive": "l1", "explicit": "l2",
    "hardcore": "l3", "extreme": "l4", "any": "l4", "不限": "l4",
    # V6 的 `level` 输出是**显示标签**（`0 · 全年龄` 这种），不是 key —— 两种都要认
    "全年龄": "l0", "擦边": "l1", "暗示": "l1", "露骨": "l2",
    "硬核": "l3", "极端": "l4", "0": "l0", "1": "l1", "2": "l2",
    "3": "l3", "4": "l4",
}


def level_to_rating(level):
    """把 V6 的 level 输出转成本地五档。认 key（sfw）、认标签（0 · 全年龄）、认裸数字。"""
    s = str(level or "").strip().lower()
    if not s:
        return ""
    m = re.match(r"^([0-4])\b", s) or re.match(r"^([0-4])$", s)
    if m:
        return "l" + m.group(1)
    if s in LEVEL_TO_RATING:
        return LEVEL_TO_RATING[s]
    for key, val in LEVEL_TO_RATING.items():
        if key and key in s:
            return val
    return ""

# 判定词表：从高往低，命中即定档。全部小写，按整词匹配。
RATING_RULES = [
    ("l4", [
        r"\bguro\b", r"\bgore\b", r"\bblood\b", r"\bbloody\b", r"\bamputat\w*\b",
        r"\bcorpse\b", r"\bmutilat\w*\b", r"\bdecapitat\w*\b", r"\bdisembowel\w*\b",
        r"\bbody horror\b", r"\btorture\b", r"\bdismember\w*\b", r"\bscat\b",
        r"\binternal cum\b", r"\bprolapse\b", r"\bguro\b",
    ]),
    ("l3", [
        r"\bsex\b", r"\bvaginal\b", r"\banal\b", r"\bpenetrat\w*\b", r"\bfellatio\b",
        r"\bpaizuri\b", r"\bcum\b", r"\bejaculat\w*\b", r"\bbondage\b", r"\bbdsm\b",
        r"\bshibari\b", r"\bgangbang\b", r"\borgasm\b", r"\bahegao\b",
        r"\bsex toy\b", r"\bvibrator\b", r"\bdildo\b", r"\bmasturbat\w*\b",
        r"\bcunnilingus\b", r"\bnsfw\b", r"\bhentai\b", r"\bintercourse\b",
        r"\btentacles?\b", r"\bspread legs\b", r"\bmissionary\b", r"\bdoggystyle\b",
    ]),
    ("l2", [
        r"\bnude\b", r"\bnudity\b", r"\bnipples?\b", r"\bareola\b", r"\btopless\b",
        r"\bbottomless\b", r"\bcompletely nude\b", r"\bclothes removed\b",
        r"\bpubic hair\b", r"\bpussy\b", r"\bpenis\b", r"\bbreasts out\b",
        r"\bundressing\b", r"\bexposed breasts\b", r"\bnaked\b",
    ]),
    ("l1", [
        r"\bbikini\b", r"\bswimsuit\b", r"\bone-piece swimsuit\b", r"\bunderwear\b",
        r"\bpanties\b", r"\bbra\b", r"\blingerie\b", r"\bcleavage\b", r"\bcameltoe\b",
        r"\bcrop top\b", r"\bshort shorts\b", r"\bwet clothes\b", r"\bsee-through\b",
        r"\bmidriff\b", r"\bnavel\b", r"\boff shoulder\b", r"\bbare shoulders?\b",
        r"\bhigh slit\b", r"\bnightgown\b", r"\bsleeping kimono\b", r"\bsuggestive\b",
        r"\bsarashi\b", r"\bbandages?\b", r"\bbare thighs?\b", r"\bleotard\b",
    ]),
]

_RATING_RE = [(lvl, [re.compile(p) for p in pats]) for lvl, pats in RATING_RULES]


def rate_prompt(text, generator_level=""):
    """按内容词表判档；再和 V6 生成档位取更严的那个。

    返回 dict：rating / cn / danbooru / hits / generator_level
    """
    raw = " , ".join(split_tags(text)).lower()
    hits = {}
    rating = "l0"

    for level, patterns in _RATING_RE:
        for pat in patterns:
            m = pat.search(raw)
            if not m:
                continue
            hits.setdefault(level, []).append(m.group(0).strip())
            if RATING_ORDER.index(level) > RATING_ORDER.index(rating):
                rating = level

    gen = str(generator_level or "").strip().lower()
    gen_rating = level_to_rating(gen)
    # 判定口径：**内容优先**。正文判出档位就以正文为准（哪怕生成时写的是 extreme）；
    # 只有在正文一个证据都没命中（判 l0）时，才采信生成档位兜底 ——
    # 因为词表会漏（`nude` 写成别的说法就抓不到），而生成档位至少是个下限。
    # `any` / `不限` 表示"不设上限"，属于无信息，不参与兜底。
    if rating == "l0" and gen_rating and gen not in ("any", "不限"):
        rating = gen_rating

    cn, danbooru = RATING_LABELS[rating]
    return {
        "rating": rating,
        "cn": cn,
        "danbooru": danbooru,
        "hits": {k: sorted(set(v)) for k, v in hits.items()},
        "generator_level": gen,
    }


DEFAULT_NEGATIVE = (
    "worst quality, low quality, lowres, normal quality, jpeg artifacts, "
    "blurry, bad anatomy, bad hands, extra digits, fewer digits, "
    "extra limbs, missing limbs, deformed, disfigured, watermark, signature, "
    "text, username, artist name, chromatic aberration, cropped"
)

# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------

_SPLIT_CHARS = ",，、;；\n"
_OPEN = "([{"
_CLOSE = ")]}"


def split_tags(text):
    """按逗号切分，但括号内的逗号不切（`liuying (honkai: star rail)` 要整块保留）。"""
    if not text:
        return []
    out, cur, depth = [], [], 0
    for ch in str(text):
        if ch in _OPEN:
            depth += 1
        elif ch in _CLOSE:
            depth = max(0, depth - 1)
        if ch in _SPLIT_CHARS and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    out.append("".join(cur))
    return [t.strip() for t in out if t and t.strip()]


def norm_key(tag):
    """去重用的归一化键：小写、压缩空白、下划线视同空格、去首尾标点。"""
    t = str(tag).strip().lower().replace("_", " ")
    t = re.sub(r"\s+", " ", t)
    t = t.strip(" .,;:，。；：")
    return t


def is_sentence(token):
    """判定是不是整句自然语言（而不是 tag）。"""
    t = str(token).strip()
    if not t:
        return False
    if " " not in t:
        return False
    if SENTENCE_END.search(t):
        return True
    if PRONOUN_START.match(t):
        return True
    words = t.split()
    # 长且没有 tag 的典型形态（tag 很少超过 8 词）
    if len(words) >= 10:
        return True
    return False


def _word_in(token, words):
    """整词/词组匹配（前后不能紧邻字母数字）。"""
    t = " " + norm_key(token) + " "
    for w in words:
        wl = w.lower()
        if (" " + wl + " ") in t:
            return w
        # 允许 tag 以该词结尾（`brown hair` 命中 `hair`）
        if t.endswith(" " + wl + " ") and len(wl) > 3:
            return w
    return None


def _has_suffix_word(token, suffixes):
    t = norm_key(token)
    for s in suffixes:
        if t.endswith(" " + s) or t == s:
            return s
    return None


def classify(tag):
    """把一个 tag 归到一个分组。顺序敏感：先具体后泛化。"""
    t = norm_key(tag)
    if not t:
        return "other"
    if t in QUALITY_WORDS:
        return "quality"
    if t in COUNT_WORDS:
        return "count"
    if t in CHARACTER_HINTS:
        return "character"
    if t in LIGHT_WORDS:
        return "light"
    if t in CAMERA_WORDS:
        return "camera"
    if t in POSE_WORDS:
        return "pose"
    if t in SCENE_WORDS:
        return "scene"
    if t in CLOTHING_WORDS:
        return "clothing"
    if t in STYLE_WORDS:
        return "style"

    # 外观：靠词根
    if APPEARANCE_RE.search(t):
        return "appearance"
    # 服装：词根兜底
    if re.search(r"\b(dress|skirt|shirt|jacket|coat|hat|socks?|boots?|shoes?|"
                 r"gloves?|ribbon|choker|necklace|glasses|kimono|bikini|swimsuit|"
                 r"uniform|armor|cape|scarf|belt|sash|veil|halo|trim|collar)\b", t):
        return "clothing"
    # 场景：词根兜底
    if re.search(r"\b(bed|room|window|door|sky|city|street|forest|garden|"
                 r"beach|ocean|sea|mountain|stage|floor|wall|couch|sofa|chair)\b", t):
        return "scene"
    # 姿态：词根兜底
    if re.search(r"\b(stand|sit|kneel|lying|walk|run|stretch|lean|hug|hold|"
                 r"looking|gaze|eyes|smile|blush|mouth)\w*\b", t):
        return "pose"
    return "other"


# 这些泛化名词在整句扫描时会被更具体的 tag 顶掉（`bed` → `on bed`，`city` → `city lights`）
GENERIC_SCENE_NOUNS = {
    "bed", "door", "door frame", "window", "city", "sky", "background",
    "room", "floor", "wall", "stars", "night", "morning",
}

NL_SCAN_WORDS = (SCENE_WORDS | LIGHT_WORDS) - GENERIC_SCENE_NOUNS


def drop_subsumed(tags):
    """去掉被更长 tag 吞掉的短 tag：`kimono` 被 `sleeping kimono` 吃掉，`arms` 被 `arms wide` 吃掉。"""
    out = []
    keys = [norm_key(t) for t in tags]
    for i, t in enumerate(tags):
        k = keys[i]
        eaten = False
        for j, other in enumerate(keys):
            if i == j or other == k:
                continue
            if (" " + k + " ") in (" " + other + " ") and len(other.split()) > len(k.split()):
                eaten = True
                break
        if not eaten:
            out.append(t)
    return out


def nl_to_tags(sentence):
    """整句 → tag 列表。规则表优先，词根扫描兜底，最后做一次子串吞并。"""
    s = " " + str(sentence).strip().lower() + " "
    found = []
    for pattern, tags in NL_RULES:
        if re.search(pattern, s):
            for t in tags:
                if t not in found:
                    found.append(t)
    # 词根兜底：句子里出现的场景 / 光影关键词也捞回来（泛化名词已排除）
    for w in NL_SCAN_WORDS:
        if " " + w + " " in s and w not in found:
            found.append(w)
    return drop_subsumed(found)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def _clean_tag(tag):
    """清理单条 tag：去尾部标点、压缩空白、去掉句末的句号残留。"""
    t = re.sub(r"\s+", " ", str(tag)).strip()
    t = t.strip(" .,;:，。；：")
    return t


def _dedupe_keep_order(items):
    seen, out = set(), []
    for it in items:
        k = norm_key(it)
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(it)
    return out


def decouple(text, tag_style="space", keep_quality=True, keep_nl=True,
             extra_positive="", negative_extra="", drop_blurry_conflict=True):
    """把 V6 正文解耦成通用提示词。

    参数
    ----
    text            : V6「text」输出的正文（也可直接喂任意混合提示词）
    tag_style       : "space"（默认，Anima/ComfyUI 写法）| "underscore"（WebUI/NAI）
    keep_quality    : 是否保留 masterpiece / very aesthetic 这类质量词
    keep_nl         : 是否把整句自然语言也压成 tag（关掉 = 直接丢弃整句）
    extra_positive  : 手写追加，会并到正向末尾
    negative_extra  : 手写负向追加
    drop_blurry_conflict : 正向里已经有 blurry 时，从默认负向里剔掉 blurry（默认开）

    返回 dict：
      prompt / prompt_nl / negative / cn / report / groups / stats
    """
    raw = split_tags(text)
    groups = {k: [] for k, _ in GROUP_ORDER}
    sentences, dropped = [], []
    pending = []          # [(group, tag)]，保持原始顺序，留给角色补判
    stats = {"tokens": len(raw), "sentences": 0, "nl_tags": 0, "dropped_dup": 0}

    for tok in raw:
        tok = _clean_tag(tok)
        if not tok:
            continue
        if is_sentence(tok):
            sentences.append(tok)
            stats["sentences"] += 1
            if keep_nl:
                for t in nl_to_tags(tok):
                    pending.append((classify(t), t))
                    stats["nl_tags"] += 1
            continue
        g = classify(tok)
        if g == "quality" and not keep_quality:
            dropped.append(tok)
            continue
        pending.append((g, tok))

    # 角色名补判：V6 的出题顺序是「角色名, 作品名」，紧挨在作品名前面、
    # 自己又没被判成角色的那个 tag，就是角色名。判错了最多是多个角色 tag，不影响出图。
    for i in range(len(pending) - 1):
        g, _t = pending[i]
        g2, t2 = pending[i + 1]
        if g == "other" and g2 == "character" and norm_key(t2) in CHARACTER_HINTS:
            pending[i] = ("character", _t)

    for g, tok in pending:
        groups[g].append(tok)

    # 每条分组内部先去重，避免「站立」出现三遍
    for k in groups:
        before = len(groups[k])
        groups[k] = _dedupe_keep_order(groups[k])
        stats["dropped_dup"] += before - len(groups[k])

    # 全局去重（跨组：`bare shoulder` 和 `bare shoulders` 这类归一后同键）
    seen = set()
    for k, _ in GROUP_ORDER:
        keep = []
        for t in groups[k]:
            key = norm_key(t)
            if key in seen:
                stats["dropped_dup"] += 1
                continue
            seen.add(key)
            keep.append(t)
        groups[k] = keep

    # 额外追加
    for tok in split_tags(extra_positive):
        tok = _clean_tag(tok)
        if tok:
            groups[classify(tok)].append(tok)

    # 组装正向
    ordered = []
    for k, _ in GROUP_ORDER:
        ordered.extend(groups[k])
    ordered = _dedupe_keep_order(ordered)

    prompt = ", ".join(_apply_style(t, tag_style) for t in ordered)

    # 负向：默认串 + 追加，剔除与正向冲突的项
    neg_items = split_tags(DEFAULT_NEGATIVE) + split_tags(negative_extra)
    pos_keys = {norm_key(t) for t in ordered}
    if drop_blurry_conflict and "blurry" in pos_keys:
        neg_items = [n for n in neg_items if norm_key(n) != "blurry"]
    negative = ", ".join(_apply_style(t, tag_style) for t in _dedupe_keep_order(neg_items))

    prompt_nl = build_nl(groups) if keep_nl else _sentence_join(sentences)
    cn = build_cn(groups, sentences)
    report = build_report(groups, stats, sentences)

    return {
        "prompt": prompt,
        "prompt_nl": prompt_nl,
        "negative": negative,
        "cn": cn,
        "report": report,
        "groups": groups,
        "sentences": sentences,
        "stats": stats,
    }


def _apply_style(tag, style):
    if style == "underscore":
        # 括号内的内容保持原样，只把空格换成下划线
        return tag.replace(" ", "_")
    return tag


def _sentence_join(sentences):
    return " ".join(s.strip() for s in sentences if s.strip())


def build_nl(groups):
    """拼一段英文自然语言（Flux / SD3 / 云端模型用）。"""
    def j(key, limit=8):
        return ", ".join(groups.get(key, [])[:limit])

    char_name = ""
    for t in groups.get("character", []):
        if norm_key(t) not in CHARACTER_HINTS:
            char_name = t
            break
    work = next((t for t in groups.get("character", [])
                 if norm_key(t) in CHARACTER_HINTS), "")

    parts = []
    if char_name:
        head = f"An anime illustration of {char_name}"
        if work:
            head += f" from {work}"
        parts.append(head + ".")
    else:
        head = "An anime illustration"
        if "solo" in [norm_key(x) for x in groups.get("count", [])]:
            head += " of a solitary figure"
        elif groups.get("count"):
            head += " of " + j("count", 2)
        parts.append(head + ".")
    if groups["appearance"]:
        parts.append("She has " + j("appearance", 8) + ".")
    if groups["clothing"]:
        parts.append("She is wearing " + j("clothing", 8) + ".")
    if groups["pose"]:
        parts.append("Her pose: " + j("pose", 8) + ".")
    if groups["scene"]:
        parts.append("The setting is " + j("scene", 8) + ".")
    if groups["light"]:
        parts.append("Lighting: " + j("light", 6) + ".")
    if groups["camera"]:
        parts.append("Framed as " + j("camera", 6) + ".")
    if groups["style"]:
        parts.append("Style: " + j("style", 4) + ".")
    if groups["quality"]:
        parts.append("Rendered at " + j("quality", 4) + ".")
    return " ".join(parts)


def _cn_of(tag):
    k = norm_key(tag)
    if k in WORK_CN:
        return WORK_CN[k]
    if k in NAME_CN:
        return NAME_CN[k]
    if k in CN_DICT:
        return CN_DICT[k]
    # 复合词兜底：逐段翻
    if " " in k:
        pieces = [WORK_CN.get(p) or NAME_CN.get(p) or CN_DICT.get(p) for p in k.split()]
        if all(pieces):
            return "".join(pieces)
    return tag


def build_cn(groups, sentences=None):
    """拼一段中文描述（给人看的）。"""
    lines = []
    for key, cn in GROUP_ORDER:
        items = groups.get(key) or []
        if not items:
            continue
        lines.append(f"{cn}：" + "、".join(_cn_of(t) for t in items[:12]))
    body = "；".join(lines) if lines else "（无内容）"
    if sentences:
        gloss = _cn_sentence(sentences[0])
        # 只保留翻译得比较干净的那句；半中半英的残句不如不给
        if gloss and len(re.findall(r"[A-Za-z']{2,}", gloss)) <= 3:
            body += "。原句意译：" + gloss
    return body


def _cn_sentence(sentence):
    """把原句里的关键短语替换成中文，剩下的原样留英文（不硬翻）。"""
    s = str(sentence).strip()
    repl = [
        (r"\bstands? in a door ?frame\b", "站在门框里"),
        (r"\bboth forearms pressed against the frame\b", "两条前臂压在门框上"),
        (r"\bher chest leans forward between her arms\b", "胸口在两臂之间往前送"),
        (r"\bshoulder blades pull together\b", "肩胛骨向中间收紧"),
        (r"\bkneels on the bed\b", "跪坐在床上"),
        (r"\bhands on her thighs\b", "双手放在大腿上"),
        (r"\bmorning light comes across the sheet\b", "晨光扫过床单"),
        (r"\bcollar slips off one shoulder\b", "领口从一侧肩膀滑落"),
        (r"\bseen from the side\b", "侧面视角"),
        (r"\bcity lights glow beyond the window\b", "窗外城市灯火"),
    ]
    for pat, zh in repl:
        s = re.sub(pat, zh, s, flags=re.I)
    return s


def build_report(groups, stats, sentences):
    total = sum(len(v) for v in groups.values())
    lines = ["[解耦报告]",
             f"输入 token {stats['tokens']} 个 → 输出 {total} 条",
             f"识别整句 {stats['sentences']} 条 → 压出 {stats['nl_tags']} 个 tag",
             f"去重丢弃 {stats['dropped_dup']} 条"]
    for key, cn in GROUP_ORDER:
        n = len(groups.get(key) or [])
        if n:
            lines.append(f"  {cn} {n:>3} 条")
    if sentences:
        lines.append("  原句保留：" + " / ".join(sentences)[:120] + ("…" if len(" ".join(sentences)) > 120 else ""))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# PNG 元数据读取（不依赖 PIL）
# ---------------------------------------------------------------------------

def read_png_text(path):
    """读出 PNG 里所有 tEXt 块，返回 dict。读不到返回 {}。"""
    import struct
    with open(path, "rb") as f:
        data = f.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return {}
    out, i, n = {}, 8, len(data)
    while i + 8 <= n:
        ln = struct.unpack(">I", data[i:i + 4])[0]
        typ = data[i + 4:i + 8].decode("latin1")
        chunk = data[i + 8:i + 8 + ln]
        if typ == "tEXt":
            k, _, v = chunk.partition(b"\x00")
            out[k.decode("latin1")] = v.decode("utf-8", "ignore")
        elif typ == "IEND":
            break
        i += 12 + ln
    return out


def extract_from_meta(meta):
    """从元数据字典里挖出最靠谱的一份正向正文 + 来源标注。"""
    import json
    for key in ("anima_v4_prompt", "anima_v3_prompt"):
        blob = meta.get(key)
        if not blob:
            continue
        try:
            j = json.loads(blob)
        except Exception:
            continue
        pos = (j.get("positive") or "").strip()
        if pos:
            return pos, f"{key}.positive", j

    # 退回 workflow：找最长的那个字符串 widget（通常是正文）
    blob = meta.get("workflow")
    if blob:
        try:
            wf = json.loads(blob)
        except Exception:
            wf = None
        if wf:
            best = ""
            for node in wf.get("nodes", []) or []:
                vals = node.get("widgets_values")
                if isinstance(vals, list):
                    for v in vals:
                        if isinstance(v, str) and len(v) > len(best) and "," in v:
                            best = v
                elif isinstance(vals, dict):
                    for v in vals.values():
                        if isinstance(v, str) and len(v) > len(best) and "," in v:
                            best = v
            if best:
                return best, "workflow.longest_text", {}

    # 再退：API prompt JSON
    blob = meta.get("prompt")
    if blob:
        try:
            api = json.loads(blob)
        except Exception:
            api = None
        if isinstance(api, dict):
            best = ""
            for node in api.values():
                ins = (node or {}).get("inputs") or {}
                for v in ins.values():
                    if isinstance(v, str) and len(v) > len(best) and "," in v:
                        best = v
            if best:
                return best, "prompt.longest_text", {}
    return "", "", {}


# ---------------------------------------------------------------------------
# 分级标签写回（extra_pnginfo → SaveImage → PNG tEXt）
# ---------------------------------------------------------------------------

META_SCHEMA_RATING = "anima-decoupler/rating@1"

# 写进 workflow 时认哪些节点：只填「本来就是空的」文本位，绝不覆盖已有字面量
TEXT_NODE_TYPES = {"CLIPTextEncode", "CR Text", "StringConcatenate", "DanbooruText",
                   "PrimitiveString", "PrimitiveStringMultiline", "String"}


def build_rating_meta(text, generator_level="", tag_style="space",
                      negative_extra="", keep_quality=True):
    """组装一份可 JSON 序列化的分级元数据。"""
    d = decouple(text, tag_style=tag_style, keep_quality=keep_quality,
                 negative_extra=negative_extra)
    r = rate_prompt(d["prompt"], generator_level)
    return {
        "schema": META_SCHEMA_RATING,
        "plugin": "ComfyUI-AnimaPromptDecoupler",
        "rating": r["rating"],
        "rating_cn": r["cn"],
        "danbooru": r["danbooru"],
        "generator_level": r["generator_level"],
        "hits": r["hits"],
        "tags": d["prompt"],
        "negative": d["negative"],
    }


def _fill_empty_text(wf, text):
    """把 workflow 里空着的正向文本框填上 —— 让看图工具能读到真提示词。

    只动空位（`""` 或缺失），有字面量的一律不碰。`CLIPTextEncode` 里
    负向通常写着质量词，属于字面量，不会被覆盖。
    """
    n = 0
    for node in (wf.get("nodes") or []):
        if not isinstance(node, dict):
            continue
        if node.get("type") not in TEXT_NODE_TYPES:
            continue
        vals = node.get("widgets_values")
        if isinstance(vals, list):
            if not vals:
                vals.append(text)
                n += 1
            elif isinstance(vals[0], str) and not vals[0].strip():
                vals[0] = text
                n += 1
        elif isinstance(vals, dict):
            for k, v in list(vals.items()):
                if isinstance(v, str) and not v.strip():
                    vals[k] = text
                    n += 1
                    break
    return n


def inject_rating(extra_pnginfo, meta, key="anima_rating", fill_text=""):
    """把分级元数据塞进 extra_pnginfo。

    返回 {"key": bool, "workflow": int}，workflow 是填了几个文本框。
    永不抛异常 —— 写得进去是加分项，写不进去不能让出图挂掉。
    """
    st = {"key": False, "workflow": 0}
    if not isinstance(extra_pnginfo, dict):
        return st
    try:
        extra_pnginfo[key] = meta
        st["key"] = True
    except Exception:
        pass
    if fill_text:
        try:
            wf = extra_pnginfo.get("workflow")
            if isinstance(wf, dict):
                st["workflow"] = _fill_empty_text(wf, fill_text)
        except Exception:
            pass
    return st
