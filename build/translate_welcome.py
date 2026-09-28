# -*- coding: utf-8 -*-
"""维护者侧：汉化「入门指南」示例文件（Welcome files）。

用户所说的「入门指南里的示例文件」＝ 游戏 ``pack/welcome_files.zip`` 解出来的三组内容：

* ``Getting started/``  —— 14 个教程页（控制、节点、粒子、仿真、UV…）
* ``Sample Projects/`` —— 15 个示例工程
* ``Templates/``       —— 画布模板

其中教程文字**不在图片里**，而在 ``.pxc`` 工程文件的文本节点上：

* ``Node_Display_Text`` —— 就是那些说明段落（含 ``<node …>`` / ``<bt …>`` / ``<spr …>``
  这类富文本标签，游戏会把它们渲染成节点图标、按键胶囊、小图标）
* ``Node_Slideshow``    —— 幻灯片标题（如 ``Node basics``）

⚠️ 同样位置在别的节点类型里也有 ``r.d``，但内容是**调色曲线 JSON / 文件路径 / 文件名**，
翻译它们会直接把工程弄坏。所以这里**只**处理上面两种节点类型（见 ``pxc.TEXT_NODE_TYPES``）。

标签是**查找键**，必须原样保留：``<bt Middle mouse drag>`` 这种不能翻成中文，
否则游戏找不到对应的按键名/图标。对照表 ``welcome_zh.json`` 里的译文已经带着原标签。

产出
----
``zh/welcome/<与官方包完全相同的相对路径>.pxc``（只放 .pxc，缩略图 PNG 不动）。
客户端按**同名覆盖**写进数据目录的 ``Welcome files/``，所以相对路径必须严格一致。
整个 ``zh/`` 目录会被打包进汉化包并由 ``zhsync`` 的清单覆盖，无需另行注册。

用法
----
    python build/translate_welcome.py                     # 生成到 zh/welcome/
    python build/translate_welcome.py --install "D:\\…"   # 指定安装目录
    python build/translate_welcome.py --report            # 只报告，不写文件
    python build/translate_welcome.py --manifest          # 顺带重建 manifest.json（版本 +1）
    python build/translate_welcome.py --zip some.zip      # 用别的包（自测用）

返回码：0 = 成功；1 = 出错（例如对照表有缺失/标签被改动）。
"""
import argparse
import io
import json
import os
import re
import sys
import zipfile

BUILD = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BUILD)
sys.path.insert(0, BUILD)
sys.path.insert(0, ROOT)

from pxc import Pxc, PxcError, TEXT_NODE_TYPES      # noqa: E402

ZH_WELCOME = os.path.join(ROOT, "zh", "welcome")
TABLE_PATH = os.path.join(BUILD, "welcome_zh.json")
TAG = re.compile(r"<[^<>]*>")


def log(msg):
    print(msg, flush=True)


def load_table():
    with open(TABLE_PATH, encoding="utf-8") as f:
        tb = json.load(f)
    if not isinstance(tb, dict) or not tb:
        raise SystemExit(f"[错误] 对照表为空或格式不对：{TABLE_PATH}")
    return tb


def check_table(tb):
    """自检：每条译文的标签多重集合必须与原文一致。"""
    bad = []
    for en, zh in tb.items():
        if sorted(TAG.findall(en)) != sorted(TAG.findall(zh)):
            bad.append((en, zh))
    return bad


def looks_like_prose(s):
    """粗略判断一条文本节点内容是不是"该翻译的说明文字"。"""
    return bool(re.search(r"[A-Za-z]{2,}", s))


def translate_pxc(raw, tb, rel):
    """返回 (新字节, 替换条数, 未命中条目列表)。"""
    px = Pxc.from_bytes(raw)
    n, miss = 0, []
    for _node, inp in px.text_nodes():
        r = inp["r"]
        s = r["d"]
        if not s.strip():
            continue
        zh = tb.get(s)
        if zh is None:
            if looks_like_prose(s):
                miss.append(s)
            continue
        if zh != s:
            r["d"] = zh
            n += 1
    return px.to_bytes(), n, miss


def find_zip(install, override):
    """返回 (zip 路径, 安装目录或 None)。"""
    if override:
        if not os.path.isfile(override):
            raise SystemExit(f"[错误] 找不到 {override}")
        return override, install
    if not install:
        import patch_tool
        install = patch_tool.find_install_dir()
    if not install:
        raise SystemExit("[错误] 未找到游戏安装目录，请用 --install 或 --zip 指定")
    p = os.path.join(install, "pack", "welcome_files.zip")
    if not os.path.isfile(p):
        raise SystemExit(f"[错误] 找不到 {p}")
    return p, install


def main():
    ap = argparse.ArgumentParser(description="汉化 Welcome files 里的教程文字")
    ap.add_argument("--install", default=None, help="游戏安装目录（默认自动探测）")
    ap.add_argument("--zip", default=None, help="直接指定 welcome_files.zip（自测用）")
    ap.add_argument("--out", default=ZH_WELCOME, help="输出目录（默认 zh/welcome）")
    ap.add_argument("--report", action="store_true", help="只报告，不写文件")
    ap.add_argument("--manifest", action="store_true",
                    help="顺带重建 zh/manifest.json（版本 patch +1）")
    ap.add_argument("--version", default=None, help="重建清单时使用的包版本号（默认 patch +1）")
    ap.add_argument("--show-missing", type=int, default=20,
                    help="最多列出多少条未命中原文（默认 20）")
    args = ap.parse_args()

    tb = load_table()
    bad = check_table(tb)
    if bad:
        log(f"[错误] 对照表里有 {len(bad)} 条译文的标签与原文不一致（标签是查找键，必须原样保留）：")
        for en, zh in bad[:10]:
            log(f"   原文标签 {sorted(TAG.findall(en))}")
            log(f"   译文标签 {sorted(TAG.findall(zh))}")
        return 1

    found = find_zip(args.install, args.zip)
    zp, install = found if isinstance(found, tuple) else (found, None)
    log(f"源包: {zp}")
    log(f"对照表: {len(tb)} 条（标签自检通过）")

    outdir = args.out
    total_files = total_repl = 0
    all_miss = {}
    skipped = []
    with zipfile.ZipFile(zp) as z:
        names = sorted(n for n in z.namelist() if n.endswith(".pxc"))
        if not names:
            raise SystemExit("[错误] 包里没有 .pxc 文件")
        for rel in names:
            try:
                data, n, miss = translate_pxc(z.read(rel), tb, rel)
            except PxcError as e:
                skipped.append((rel, str(e)))
                continue
            for m in miss:
                all_miss.setdefault(m, []).append(rel)
            total_files += 1
            total_repl += n
            if not args.report:
                dst = os.path.join(outdir, *rel.split("/"))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                # 二进制，显式 newline 无关；用 to_bytes 已经是确定的字节序列
                with open(dst, "wb") as f:
                    f.write(data)

    log(f"处理 .pxc：{total_files} 个，替换文本 {total_repl} 处")
    if skipped:
        log(f"跳过 {len(skipped)} 个无法解析的文件：{[s[0] for s in skipped]}")
    if all_miss:
        uniq = len(all_miss)
        log(f"[注意] 有 {uniq} 条原文不在对照表里（已保持英文）"
            f"{'，示例：' if args.show_missing else ''}")
        for m in list(all_miss)[:args.show_missing]:
            log(f"   · {m[:100]}")
    else:
        log("对照表已覆盖全部说明文字，无遗漏。")

    if not args.report:
        log(f"已写入: {outdir}")

    if args.manifest:
        import zhsync
        cur = None
        mp = os.path.join(ROOT, "zh", "manifest.json")
        if os.path.isfile(mp):
            try:
                cur = json.load(open(mp, encoding="utf-8")).get("version")
            except Exception:
                pass
        parts = str(cur or "1.0.0").split(".")
        while len(parts) < 3:
            parts.append("0")
        parts[-1] = str(int(re.sub(r"\D", "", parts[-1]) or 0) + 1)
        ver = args.version or ".".join(parts[:3])
        gv = None
        try:
            import patch_tool
            from sync_upstream import find_root, game_version
            root = find_root(args.install or patch_tool.find_install_dir())
            if root:
                gv = game_version(root)
        except Exception:
            pass
        man = zhsync.build_manifest(os.path.join(ROOT, "zh"), ver, game_version=gv, log=log)
        with open(mp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(man, f, ensure_ascii=False, indent=1)
            f.write("\n")
        log(f"已重建清单 v{ver}：{man['counts']}，共 {len(man['files'])} 个文件")

    return 1 if skipped else 0


if __name__ == "__main__":
    sys.exit(main())
