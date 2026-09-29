#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成仓库根目录的 tool.json —— 程序自更新元数据（客户端「⑨ 检查程序更新」用）。

用法（维护者发版时）：
    python build/make_tool_meta.py --tag v1.3.3
读取 patch_tool.py 的 VERSION + 仓库根目录下两个发行资产的 size/sha256，
写出 tool.json 后随仓库一起推送（Pages / jsDelivr / Raw 三源都可取到）。
"""
import argparse, hashlib, json, os, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = "DC1024/pixel-composer-cn"
ASSETS = [("windows", "PixelComposer-CN-Patcher.exe"),
          ("linux",   "PixelComposer-CN-Linux.tar.gz")]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True, help="发行版标签，例如 v1.3.3")
    args = ap.parse_args()

    ver_line = ""
    with open(os.path.join(ROOT, "patch_tool.py"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("VERSION"):
                ver_line = line.split("=", 1)[1].strip().strip('"')
                break
    if not ver_line:
        sys.exit("无法从 patch_tool.py 读取 VERSION")

    files = {}
    for plat, name in ASSETS:
        p = os.path.join(ROOT, name)
        if not os.path.isfile(p):
            sys.exit(f"缺少发行资产：{p}（请先构建）")
        files[name] = {"platform": plat,
                       "size": os.path.getsize(p),
                       "sha256": sha256_file(p)}
        print(f"  {name}: {files[name]['size']} B  sha256={files[name]['sha256'][:16]}…")

    meta = {
        "name": "pixel-composer-cn-tool",
        "version": ver_line,
        "tag": args.tag,
        "updated": datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z"),
        "releases_url": f"https://github.com/{REPO}/releases/latest",
        "files": files,
    }
    out = os.path.join(ROOT, "tool.json")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"tool.json 写好了：version={ver_line} tag={args.tag} -> {out}")
    if ver_line.lstrip("v") != args.tag.lstrip("v"):
        print("⚠️ 注意：VERSION 与 tag 号不一致（自 v1.3.3 起二者应保持一致）")


if __name__ == "__main__":
    main()
