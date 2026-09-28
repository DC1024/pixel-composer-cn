# -*- coding: utf-8 -*-
"""维护者侧：定期同步上游官方语言包 → 补翻 → 更新 zh/ 与 manifest.json →（可选）推送。

为什么要有这个脚本
------------------
用户机器上跑翻译引擎有几个问题：结果不稳定、质量取决于客户端旧版本的工具、
每个用户各翻一套。改成「维护者定期同步上游 → 推 GitHub → 客户端只下载成品」后，
用户拿到的是一份经过统一处理（并可持续人工校对）的包，客户端也不必再带翻译逻辑。

上游 = 游戏自带的 `pack/locale.zip`（官方 `en` 基准）+ `Locale/version`。
只要游戏更新，`Locale/version` 会变，本脚本就能感知到"上游有新东西"。

用法
----
    python build/sync_upstream.py                    # 同步并写入 zh/（不推送）
    python build/sync_upstream.py --dry-run          # 只报告差异，不写任何文件
    python build/sync_upstream.py --push             # 同步后 git commit & push
    python build/sync_upstream.py --version 1.0.4    # 指定包版本（默认 patch +1）
    python build/sync_upstream.py --install "D:\\SteamLibrary\\steamapps\\common\\Pixel Composer"

返回码：0 = 成功（有更新已写入，或本来就无更新）；1 = 出错。
"""
import argparse
import datetime
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
LATIN = re.compile(r"[A-Za-z]{2,}")

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
# 主流程
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


def main():
    ap = argparse.ArgumentParser(description="同步上游官方语言包并更新 zh/")
    ap.add_argument("--install", default=None, help="游戏安装目录（默认自动探测）")
    ap.add_argument("--dry-run", action="store_true", help="只报告差异，不写文件")
    ap.add_argument("--push", action="store_true", help="同步后 git commit & push")
    ap.add_argument("--force", action="store_true", help="没有变化也重写 zh/ 与 manifest")
    ap.add_argument("--version", default=None, help="新包版本号（默认 patch +1）")
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
    log(f"上游 en：words {len(en_words)} 条 / nodes {len(en_nodes)} 个")

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

    log(f"词条：新增 {len(added)} 条，补翻残留 {len(retrans)} 条")
    if added[:8]:
        log("   新增示例：" + ", ".join(added[:8]))
    if retrans[:8]:
        log("   补翻示例：" + ", ".join(retrans[:8]))
    log(f"节点：新增 {len(new_nodes)} 个" + (f"（{', '.join(new_nodes[:5])}）" if new_nodes else ""))

    changed = bool(added or retrans or new_nodes)
    if not changed and not args.force:
        log("== 上游没有新内容，无需更新 ==")
        return 0

    # 5) 覆盖率报告
    tr = sum(1 for k, v in en_words.items() if isinstance(v, str) and zh_words.get(k) not in (None, v))
    total = sum(1 for v in en_words.values() if isinstance(v, str) and v.strip())
    log(f"官方词条覆盖：{tr}/{total} = {100.0 * tr / max(total, 1):.1f}%")

    if args.dry_run:
        log("--dry-run：未写入任何文件")
        return 0

    # 6) 写盘
    write_json(os.path.join(ZH, "words.json"), zh_words)
    write_json(os.path.join(ZH, "nodes.json"), zh_nodes)
    stats = apply_locale_extras(ZH)
    log(f"已注入补充表：新增 {stats['added']}，纠正 {stats['overridden']}")

    cur = None
    mp = os.path.join(ZH, "manifest.json")
    if os.path.isfile(mp):
        try:
            cur = json.load(open(mp, encoding="utf-8")).get("version")
        except Exception:
            pass
    ver = args.version or bump_version(cur)
    man = zhsync.build_manifest(ZH, ver, game_version=gv, log=log)
    write_json(mp, man)
    log(f"已写入清单 v{ver}：{man['counts']}，共 {len(man['files'])} 个文件")

    if args.push:
        push(ver, gv, len(added), len(new_nodes), log)
    else:
        log("未推送（加 --push 可自动 commit & push）")
    return 0


def load_json_tolerant_bytes(files, name):
    for rel, data in files.items():
        if rel == name or rel.endswith("/" + name):
            return json.loads(re.sub(r",(\s*[}\]])", r"\1",
                                     re.sub(r"^\s*//.*$", "", data.decode("utf-8"), flags=re.M)))
    return {}


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


def push(ver, gv, n_words, n_nodes, log):
    def git(*a, **kw):
        r = subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, **kw)
        return r

    git("add", "zh")
    st = git("status", "--porcelain", "zh")
    if not st.stdout.strip():
        log("git：zh/ 没有变化，跳过提交")
        return
    msg = f"汉化包 v{ver}：同步上游 Locale v{gv}（新增词条 {n_words} / 节点 {n_nodes}）"
    r = git("-c", "user.name=DC1024", "-c", "user.email=DC1024@users.noreply.github.com",
            "commit", "-q", "-m", msg)
    if r.returncode != 0:
        log(f"[警告] git commit 失败：{r.stderr.strip()[:300]}")
        return
    log(f"git：已提交「{msg}」")
    r = git("-c", "credential.helper=store", "push", "origin", "main")
    if r.returncode != 0:
        log(f"[警告] git push 失败：{r.stderr.strip()[:300]}")
    else:
        log("git：已推送到 origin/main（约 1 分钟后 GitHub Pages 生效）")


if __name__ == "__main__":
    sys.exit(main())
