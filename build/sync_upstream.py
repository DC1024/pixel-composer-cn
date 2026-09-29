# -*- coding: utf-8 -*-
"""维护者侧：定期同步上游官方语言包 → 补翻 → 更新 zh/ 与 manifest.json →（可选）直推 GitHub。

为什么要有这个脚本
------------------
用户机器上跑翻译引擎有几个问题：结果不稳定、质量取决于客户端旧版本的工具、
每个用户各翻一套。改成「维护者定期同步上游 → 推 GitHub → 客户端只下载成品」后，
用户拿到的是一份经过统一处理（并可持续人工校对）的包，客户端也不必再带翻译逻辑。

上游 = 游戏自带的 `pack/locale.zip`（官方 `en` 基准）+ `Locale/version`。
只要游戏更新，`Locale/version` 会变，本脚本就能感知到"上游有新东西"。

⚠️ 上游能自动同步的范围（2026-09-29 实测）
------------------------------------------
`pack/locale.zip` 的 `en/` 里**只有 7 个文件**：`words.json`、`nodes.json`、
`junctions.json`、`config.json`、`notes/*.md`。**没有 `en/UI.json`** ——
UI 面板与对话框词条不在官方语言包里（历史做法是另外从 `data.win` 提取到
`ref/UI_en_*.json` 再生成）。所以 **UI.json 无法自动跟随上游同步**，
需要单独维护词条并手动更新 `zh/UI.json`。本脚本不会碰它。

版本号规则（跟 game_version）
----------------------------
manifest 里同时记录 `version`（汉化包版本）与 `game_version`（对应上游 Locale/version）。
只要**上游 game_version 前进了**，或者**本轮内容有实际更新**，就自动 patch +1（1.2.0 → 1.2.1）。
`--version` 可以强制指定。**注意：汉化包版本 ≠ 工具版本**（patch_tool.py 的 VERSION）。

待办 / 待复核清单（不把 TODO 写进汉化包）
----------------------------------------
翻不了 / 拿不准的条目**不会**把字面 "TODO:" 写进 `zh/`，而是让该条保持英文回退
（游戏缺 key 或值等于英文时会显示英文原文，是最体面的兜底），同时把条目写进
`build/todo_report.md` 供人工补录。清单里每行都带 key、英文原文、当前中文和建议动作：
    * 要永久修某个词 → 加到 `translate_core.LOCALE_OVERRIDE`（推荐，后续同步会自动继承）
    * 官方改了英文原文导致旧译文可能过时 → 清单里标注"待复核"，人工确认或重翻
判断依据：本脚本把「上次同步时的 en 快照」存在 `build/cache/en_prev/`，
靠它才能发现"key 没改名、但英文原文被官方改了"这种情况（首次运行没有快照，
那一轮只检测新增，之后才具备该项能力）。

用法
----
    python build/sync_upstream.py                    # 同步并写入 zh/（不推送）
    python build/sync_upstream.py --dry-run          # 只报告差异，不写 zh/ 与清单（仍会写待办清单）
    python build/sync_upstream.py --push             # 同步后 git commit & push 到 main
    python build/sync_upstream.py --version 1.0.4    # 指定汉化包版本（默认 patch +1）
    python build/sync_upstream.py --install "D:\\SteamLibrary\\steamapps\\common\\Pixel Composer"

返回码：0 = 成功（有更新已写入，或本来就无更新）；1 = 出错。
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile

BUILD = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BUILD)
sys.path.insert(0, ROOT)

import zhsync                                   # noqa: E402
from translate_core import translate, apply_locale_extras   # noqa: E402

ZH = os.path.join(ROOT, "zh")
CACHE = os.path.join(BUILD, "cache")
PREV = os.path.join(CACHE, "en_prev")
TODO = os.path.join(BUILD, "todo_report.md")
WELCOME_SOURCE_SHA = os.path.join(CACHE, "welcome_source.sha256")

LATIN = re.compile(r"[A-Za-z]{2,}")
CJK = re.compile(r"[\u4e00-\u9fff]")

#: 上游是品牌名 / 格式名 / 单位，按约定保留英文（不参与"残留补翻"）
KEEP_KEYS = {
    "2d", "3d", "aseprite", "bluesky", "fps", "gamemaker", "hsv", "http", "ik",
    "krita", "lospec", "mastodon", "mkfx", "ora", "pxc", "sdf", "shadertoy",
    "twitter", "pixel_composer_discord", "delimiter_space", "false",
    "gradient_editor_blend_CMYK", "gradient_editor_blend_HSV",
    "gradient_editor_blend_OKLAB", "gradient_editor_blend_RGB",
}

#: 节点条目里需要翻译的字段（其余字段是类型/键名，不能动）
NODE_TEXT_FIELDS = ("name", "tooltip", "display_data")


def _setup_stdio():
    """重定向到文件/管道时把 stdout/stderr 固定成 UTF-8。

    Windows 上被 .bat / 任务计划重定向后，Python 可能按系统 ANSI 代码页（GBK）
    编码输出，中文日志会变成乱码。真交互终端走 WriteConsoleW 不受影响，
    所以这里只处理非 tty 的流（与 patch_tool._setup_stdio 同做法）。
    """
    for name in ("stdout", "stderr"):
        s = getattr(sys, name, None)
        if s is None:
            continue
        try:
            if s.isatty():
                continue
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


# --------------------------------------------------------------------------
# 上游取数
# --------------------------------------------------------------------------
def find_root(install):
    """返回含 Locale 的游戏数据根目录。"""
    if not install:
        return None
    for cand in (os.path.join(install, "PixelComposer"), install):
        if os.path.isdir(os.path.join(cand, "Locale")):
            return cand
    return None


def extract_en(install, log):
    """把 pack/locale.zip 里的 en/ 解到内存 dict。"""
    zp = os.path.join(install, "pack", "locale.zip")
    if not os.path.isfile(zp):
        raise SystemExit(f"[错误] 找不到 {zp}")
    data = {}
    with zipfile.ZipFile(zp) as z:
        for name in z.namelist():
            if not name.startswith("en/") or name.endswith("/"):
                continue
            rel = name[len("en/"):]
            data[rel] = z.read(name)
    log(f"已从 pack/locale.zip 取出 {len(data)} 个 en 文件：{', '.join(sorted(data))}")
    return data


def game_version(root):
    p = os.path.join(root, "Locale", "version")
    if os.path.isfile(p):
        try:
            return json.load(open(p, encoding="utf-8")).get("version")
        except Exception:
            pass
    return None


# --------------------------------------------------------------------------
# 节点深翻
# --------------------------------------------------------------------------
def translate_node(obj):
    """递归翻译节点条目里的展示字段（name / tooltip / display_data）。"""
    if isinstance(obj, str):
        return translate(obj)
    if isinstance(obj, list):
        return [translate_node(x) for x in obj]
    if isinstance(obj, dict):
        return {k: (translate_node(v) if k in NODE_TEXT_FIELDS else v)
                for k, v in obj.items()}
    return obj


# --------------------------------------------------------------------------
# 工具
# --------------------------------------------------------------------------
def bump_version(cur):
    parts = str(cur or "1.0.0").split(".")
    while len(parts) < 3:
        parts.append("0")
    try:
        parts[-1] = str(int(re.sub(r"\D", "", parts[-1]) or 0) + 1)
    except Exception:
        parts[-1] = "1"
    return ".".join(parts[:3])


def load_json_tolerant_bytes(files, name):
    for rel, data in files.items():
        if rel == name or rel.endswith("/" + name):
            return json.loads(re.sub(r",(\s*[}\]])", r"\1",
                                     re.sub(r"^\s*//.*$", "", data.decode("utf-8"), flags=re.M)))
    return {}


def write_json(path, obj):
    # newline="\n" 很关键：Windows 下文本模式默认写 CRLF，会让包内文件字节与
    # git blob（LF）不一致，同步时就对不上哈希了（见 zhsync.normalize_bytes）。
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


def load_prev(name):
    """读上次同步时的 en 快照；没有（首次运行）返回 None。"""
    p = os.path.join(PREV, name)
    if not os.path.isfile(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def snapshot_en(en_words, en_nodes, en_junc):
    """保存本次的 en 快照，供下次发现"英文原文被官方改了"。"""
    os.makedirs(PREV, exist_ok=True)
    for name, obj in (("words.json", en_words), ("nodes.json", en_nodes),
                      ("junctions.json", en_junc)):
        if obj:
            write_json(os.path.join(PREV, name), obj)


def is_untranslated(zh, en):
    """该条是否仍然「未译」（游戏会显示英文原文）。"""
    if not isinstance(zh, str) or not zh.strip():
        return True
    if zh == en:
        return True
    if CJK.search(zh):
        return False
    return bool(LATIN.search(zh))


def diff_changed(prev, new):
    """返回 prev 与 new 都存在的 key 中，值发生变化的那些。"""
    if not prev:
        return []
    out = []
    for k, v in new.items():
        if k not in prev:
            continue
        if k in KEEP_KEYS:
            continue
        a = json.dumps(prev[k], sort_keys=True, ensure_ascii=False)
        b = json.dumps(v, sort_keys=True, ensure_ascii=False)
        if a != b:
            out.append(k)
    return out


def load_manifest_version():
    mp = os.path.join(ZH, "manifest.json")
    if not os.path.isfile(mp):
        return None, None
    try:
        with open(mp, encoding="utf-8") as f:
            man = json.load(f)
        return man.get("version"), man.get("game_version")
    except Exception:
        return None, None


def plan_version(cur_ver, cur_gv, new_gv, content_changed, upstream_advanced, override=None):
    """按「版本号跟 game_version」的规则决定新版本号，返回 (版本, 说明)。"""
    if override:
        return override, f"命令行指定 --version {override}"
    base = str(cur_ver or "1.0.0")
    nxt = bump_version(base)
    if upstream_advanced:
        return nxt, f"上游 Locale v{cur_gv} → v{new_gv}，版本号跟进 {base} → {nxt}"
    if content_changed:
        return nxt, f"内容有更新，版本号 {base} → {nxt}"
    return None, f"版本号保持 {base}（无上游推进、无内容变更）"


def gather_words_plain(en_words, key):
    v = en_words.get(key)
    return v if isinstance(v, str) else ""


# --------------------------------------------------------------------------
# 待办 / 待复核清单
# --------------------------------------------------------------------------
def esc(text, limit=140):
    s = str(text or "").replace("|", "\\|").replace("\n", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= limit else s[:limit] + "…"


def write_todo_report(sections, gv, log):
    """把「未译 / 待复核」写成一份给人看的 markdown。

    ⚠️ 这是**给人看的报告**，不会把 "TODO:" 之类的标记写进汉化包；
    汉化包里那些条目保持英文回退即可（游戏缺 key / 值等于英文时会显示英文原文）。
    """
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    lines = [
        "# 汉化待办 / 待复核清单",
        "",
        f"> 由 `build/sync_upstream.py` 于 {now} 自动生成（上游 Locale v{gv}）。",
        "> 每周自动同步跑完后，把这个文件作为「还欠多少」的入口。",
        "",
        "## 怎么消化这里的条目",
        "",
        "1. **要永久修某个词** → 加进 `translate_core.LOCALE_OVERRIDE`（推荐）。",
        "   下一次同步时 `apply_locale_extras` 会自动把它注进 `zh/`，不会被后续同步冲掉。",
        "2. **官方改了英文原文、旧中文可能过时** → 人工确认；仍适用就不管，",
        "   不适用就把新译法同样加进 `LOCALE_OVERRIDE`。",
        "3. **节点名没译出来** → 同上，按 key 加进 `LOCALE_OVERRIDE`（节点 key 形如 `Node_Blur`）。",
        "",
        "本清单里的条目在汉化包中一律呈**英文回退**状态（不是说会显示 \"TODO\" 字串），",
        "所以修不修都不会影响用户正常使用，只是界面上混着英文。",
        "",
    ]
    total = 0
    for title, hint, rows in sections:
        lines.append(f"## {title}")
        lines.append("")
        if hint:
            lines.append(hint)
            lines.append("")
        if not rows:
            lines.append("（无）")
            lines.append("")
            continue
        lines.append("| key | 英文原文 | 当前中文 | 说明 |")
        lines.append("| --- | --- | --- | --- |")
        for r in rows:
            lines.append(f"| `{esc(r[0], 60)}` | {esc(r[1])} | {esc(r[2])} | {esc(r[3], 60)} |")
        lines.append("")
        total += len(rows)
    lines.append(f"---")
    lines.append("")
    lines.append(f"合计待处理：**{total}** 条。")
    lines.append("")
    os.makedirs(BUILD, exist_ok=True)
    with open(TODO, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    log(f"已写入待办清单：{os.path.relpath(TODO, ROOT)}（{total} 条待处理）")


# --------------------------------------------------------------------------
# 入门指南 welcome_files.zip 同步
# --------------------------------------------------------------------------
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sync_welcome(install, dry_run=False, log=print):
    """若游戏 pack/welcome_files.zip 与上次缓存不同，重新生成 zh/welcome_files.zip。

    返回 (changed, msg)。changed=True 表示已重新生成（或应该重新生成）。
    """
    src = os.path.join(install, "pack", "welcome_files.zip")
    if not os.path.isfile(src):
        return False, "未找到 pack/welcome_files.zip，跳过入门指南同步"
    cur_sha = sha256_file(src)
    prev_sha = ""
    if os.path.isfile(WELCOME_SOURCE_SHA):
        try:
            prev_sha = open(WELCOME_SOURCE_SHA, "r", encoding="utf-8").read().strip().split()[0]
        except Exception:
            prev_sha = ""
    if prev_sha == cur_sha:
        return False, "入门指南源包未变化"
    if dry_run:
        return True, f"入门指南源包有变化（sha256 {cur_sha[:16]}...）"
    # 调用维护者侧脚本生成中文命名 zip 与 zh/welcome/
    script = os.path.join(BUILD, "translate_welcome.py")
    r = subprocess.run([sys.executable, script], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        return True, f"translate_welcome.py 失败：{(r.stderr or r.stdout or '').strip()[:200]}"
    os.makedirs(CACHE, exist_ok=True)
    with open(WELCOME_SOURCE_SHA, "w", encoding="utf-8", newline="\n") as f:
        f.write(cur_sha + "\n")
    return True, "已重新生成 zh/welcome_files.zip 与 zh/welcome/"


# --------------------------------------------------------------------------
# git 推送（直接推 main，不建 PR）
# --------------------------------------------------------------------------
def _git(*a, **kw):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, **kw)


def read_token():
    """从 ~/.git-credentials 取本机已存的 GitHub PAT（只在 push 失败时才用）。

    ⚠️ 令牌只用于构造 push 的 URL，**绝不打印到日志**。
    """
    p = os.path.join(os.path.expanduser("~"), ".git-credentials")
    if not os.path.isfile(p):
        return ""
    try:
        txt = open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        return ""
    for ln in txt.splitlines():
        if "github.com" not in ln:
            continue
        try:
            after = ln.split("//", 1)[1]
            cred = after.split("@", 1)[0]
            tok = cred.split(":", 1)[1]
            if tok:
                return tok
        except Exception:
            continue
    return ""


def push(ver, gv, stat, log):
    add = ["zh"]
    rel_todo = os.path.relpath(TODO, ROOT).replace("\\", "/")
    if os.path.isfile(TODO):
        add.append(rel_todo)
    # 入门指南重命名映射与翻译对照表若更新也一并提交
    for rel in ("build/welcome_rename.json", "build/welcome_zh.json",
                "build/translate_welcome.py", "zhsync.py", "patch_tool.py"):
        p = os.path.join(ROOT, rel)
        if os.path.isfile(p):
            add.append(rel.replace("\\", "/"))
    st = _git("add", *add)
    st = _git("status", "--porcelain", *add)
    if not st.stdout.strip():
        log("git：没有变化，跳过提交")
        return
    welcome_note = ""
    if stat.get("welcome_changed"):
        welcome_note = "入门指南 welcome_files.zip 已更新\n"
    msg = (
        f"汉化包 v{ver}：同步上游 Locale v{gv}\n"
        f"\n"
        f"新增词条 {stat['added']} / 补翻残留 {stat['retrans']} / 新增节点 {stat['nodes']}\n"
        f"待处理清单 {stat['todo']} 条\n"
        f"{welcome_note}"
        f"\n"
        f"由 build/sync_upstream.py 自动生成（每月定时同步）"
    )
    r = subprocess.run(
        ["git", "-c", "user.name=DC1024", "-c", "user.email=DC1024@users.noreply.github.com",
         "commit", "-q", "-F", "-"],
        cwd=ROOT, input=msg, text=True, capture_output=True)
    if r.returncode != 0:
        log(f"[警告] git commit 失败：{(r.stderr or r.stdout or '').strip()[:300]}")
        return
    log(f"git：已提交「汉化包 v{ver}」")

    # 先试本机已存的凭据；失败再退回 ~/.git-credentials 里的 PAT 直连
    r = _git("-c", "credential.helper=store", "push", "origin", "main")
    if r.returncode == 0:
        log("git：已推送到 origin/main（约 1 分钟后 GitHub Pages 生效）")
        return
    log(f"[提示] 常规推送失败（{(r.stderr or '').strip()[:120]}），改用本机凭据直连重试…")
    tok = read_token()
    if not tok:
        log("[警告] 未能从 ~/.git-credentials 取到令牌，推送失败")
        return
    url = f"https://x-access-token:{tok}@github.com/DC1024/pixel-composer-cn.git"
    r = _git("-c", "credential.helper=", "push", url, "main:main")
    if r.returncode != 0:
        log(f"[警告] git push 失败：{(r.stderr or '').strip()[:300]}")
    else:
        log("git：已推送到 main（约 1 分钟后 GitHub Pages 生效）")


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------
def main():
    _setup_stdio()
    ap = argparse.ArgumentParser(description="同步上游官方语言包并更新 zh/")
    ap.add_argument("--install", default=None, help="游戏安装目录（默认自动探测）")
    ap.add_argument("--dry-run", action="store_true", help="只报告差异，不写 zh/ 与清单")
    ap.add_argument("--push", action="store_true", help="同步后 git commit & push 到 main")
    ap.add_argument("--force", action="store_true", help="没有变化也重写 zh/ 与 manifest")
    ap.add_argument("--version", default=None, help="新汉化包版本号（默认 patch +1）")
    args = ap.parse_args()

    def log(msg):
        print(msg, flush=True)

    # 1) 定位游戏与上游
    install = args.install
    if not install:
        import patch_tool                      # 只用于复用安装目录探测
        install = patch_tool.find_install_dir()
    root = find_root(install)
    if not install or not root:
        raise SystemExit("[错误] 未找到 Pixel Composer 安装目录，请用 --install 指定")
    gv = game_version(root)
    log(f"安装目录: {install}")
    log(f"数据目录: {root}")
    log(f"上游 Locale/version = {gv}")

    en_files = extract_en(install, log)
    en_words = load_json_tolerant_bytes(en_files, "words.json")
    en_nodes = load_json_tolerant_bytes(en_files, "nodes.json")
    en_junc = load_json_tolerant_bytes(en_files, "junctions.json")
    log(f"上游 en：words {len(en_words)} 条 / nodes {len(en_nodes)} 个")

    cur_ver, cur_gv = load_manifest_version()
    log(f"仓库清单：version={cur_ver} game_version={cur_gv}")

    # 同步入门指南 welcome_files.zip（独立于 locale）
    welcome_changed, welcome_msg = sync_welcome(install, args.dry_run, log=log)
    log(f"入门指南：{welcome_msg}")

    prev_words = load_prev("words.json")
    prev_nodes = load_prev("nodes.json")
    if prev_words is None:
        # 首次运行必须把基线建立起来：否则「无变化 → 早退」这条路会永远不写快照，
        # 导致下一次官方更新时的「英文原文被改」检测整代漏掉（累计丢一次）。
        if args.dry_run:
            log("提示：尚无 en 基线快照（首次运行）。真实运行会自动建立，"
                "之后才能发现「英文原文被官方改了」")
        else:
            snapshot_en(en_words, en_nodes, en_junc)
            log("首次运行：已建立 en 基线快照 → " + os.path.relpath(PREV, ROOT)
                + "，之后即可检测「英文原文被官方改动」")
            prev_words = en_words

    # 2) 读本地 zh
    zh_words = json.load(open(os.path.join(ZH, "words.json"), encoding="utf-8"))
    zh_nodes = json.load(open(os.path.join(ZH, "nodes.json"), encoding="utf-8"))
    log(f"本地 zh：words {len(zh_words)} / nodes {len(zh_nodes)}")

    # 3) 词条：补新增 + 补残留
    added, retrans = [], []
    for k, ev in en_words.items():
        if not isinstance(ev, str) or not ev.strip():
            continue
        if k not in zh_words:
            nv = translate(ev)
            if nv and nv != ev:
                zh_words[k] = nv
                added.append(k)
        elif zh_words[k] == ev and k not in KEEP_KEYS and LATIN.search(ev):
            nv = translate(ev)
            if nv and nv != ev:
                zh_words[k] = nv
                retrans.append(k)

    # 4) 节点：补新增
    new_nodes = []
    for k, ev in en_nodes.items():
        if k not in zh_nodes:
            zh_nodes[k] = translate_node(ev)
            new_nodes.append(k)

    # 5) 变化的 key（英文原文被官方改了 → 旧译文可能过时，交人工复核）
    changed_words = diff_changed(prev_words, en_words)
    changed_nodes = diff_changed(prev_nodes, en_nodes)
    log(f"词条：新增 {len(added)} 条，补翻残留 {len(retrans)} 条，"
        f"官方改原文 {len(changed_words)} 条")
    if added[:8]:
        log("   新增示例：" + ", ".join(added[:8]))
    if retrans[:8]:
        log("   补翻示例：" + ", ".join(retrans[:8]))
    if changed_words[:8]:
        log("   原文变动示例：" + ", ".join(changed_words[:8]))
    log(f"节点：新增 {len(new_nodes)} 个" + (f"（{', '.join(new_nodes[:5])}）" if new_nodes else ""))
    if changed_nodes[:5]:
        log(f"   节点定义变动：{', '.join(changed_nodes[:5])}")

    content_changed = bool(added or retrans or new_nodes) or welcome_changed
    review_needed = bool(changed_words or changed_nodes)
    upstream_advanced = cur_gv is not None and gv is not None and str(cur_gv) != str(gv)
    if upstream_advanced:
        log(f"上游已推进：Locale v{cur_gv} → v{gv}")

    if not content_changed and not review_needed and not upstream_advanced and not args.force:
        log("== 上游没有新内容，无需更新 ==")
        return 0

    # 6) 待办 / 待复核清单
    todo_rows, review_rows, node_rows = [], [], []
    for k in added:
        if k in KEEP_KEYS:
            continue
        zhv = zh_words.get(k)
        if is_untranslated(zhv, en_words.get(k, "")):
            todo_rows.append((k, en_words.get(k, ""), zhv or "", "新增但未译出，当前英文回退"))
    for k in retrans:
        zhv = zh_words.get(k)
        if is_untranslated(zhv, en_words.get(k, "")):
            todo_rows.append((k, en_words.get(k, ""), zhv or "", "残留未译，当前英文回退"))
    for k in changed_words:
        if k in added or k in retrans:
            continue
        review_rows.append((k, en_words.get(k, ""), zh_words.get(k, ""),
                            f"官方原文已改（原为 {esc(prev_words.get(k, ''), 40)}）"))
    for k in new_nodes + changed_nodes:
        if k in new_nodes and k not in changed_nodes:
            nm = (zh_nodes.get(k) or {}).get("name") if isinstance(zh_nodes.get(k), dict) else None
            en_nm = en_nodes.get(k, {}).get("name", "")
            if is_untranslated(nm, en_nm):
                node_rows.append((k, en_nm, nm or "", "新增节点，名称未译出"))
        else:
            node_rows.append((k, en_nodes.get(k, {}).get("name", ""),
                              (zh_nodes.get(k) or {}).get("name", ""), "节点定义被官方改动，待复核"))
    todo_total = len(todo_rows) + len(review_rows) + len(node_rows)
    write_todo_report(
        [("一、译成不了的（当前英文回退）", None, todo_rows),
         ("二、官方改了英文原文，旧译文待复核",
          "这些条目仍用旧中文（通常依然适用），但官方措辞变了，值得扫一眼。", review_rows),
         ("三、节点", None, node_rows)],
        gv, log)

    if args.dry_run:
        log("--dry-run：未写入 zh/ 与清单（待办清单已生成，属本地报告）")
        return 0

    # 7) 写盘
    if content_changed or args.force:
        write_json(os.path.join(ZH, "words.json"), zh_words)
        write_json(os.path.join(ZH, "nodes.json"), zh_nodes)
        stats = apply_locale_extras(ZH)
        log(f"已注入补充表：新增 {stats['added']}，纠正 {stats['overridden']}")
    elif upstream_advanced:
        stats = apply_locale_extras(ZH)
        log(f"内容无新增，但上游已推进 → 仍注入补充表以确保一致（新增 {stats['added']}，"
            f"纠正 {stats['overridden']}）")

    if content_changed or upstream_advanced or args.force:
        ver, why = plan_version(cur_ver, cur_gv, gv, content_changed,
                                upstream_advanced, args.version)
        log(f"版本号：{why}")
        man = zhsync.build_manifest(ZH, ver, game_version=gv, log=log)
        write_json(os.path.join(ZH, "manifest.json"), man)
        log(f"已写入清单 v{ver}：{man['counts']}，共 {len(man['files'])} 个文件")
    else:
        ver = cur_ver
        log(f"仅待复核变化（含入门指南），版本号保持 v{ver}，未重写清单")

    # 8) 覆盖率报告
    tr = sum(1 for k, v in en_words.items() if isinstance(v, str) and zh_words.get(k) not in (None, v))
    total = sum(1 for v in en_words.values() if isinstance(v, str) and v.strip())
    log(f"官方词条覆盖：{tr}/{total} = {100.0 * tr / max(total, 1):.1f}%")

    snapshot_en(en_words, en_nodes, en_junc)
    log(f"已保存本次 en 快照到 {os.path.relpath(PREV, ROOT)}")

    if args.push:
        push(ver, gv, {"added": len(added), "retrans": len(retrans),
                       "nodes": len(new_nodes), "todo": todo_total,
                       "welcome_changed": welcome_changed}, log)
    else:
        log("未推送（加 --push 可自动 commit & push 到 main）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
