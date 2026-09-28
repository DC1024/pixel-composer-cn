# -*- coding: utf-8 -*-
"""Pixel Composer 汉化包「在线同步」模块（仅标准库）。

设计分工
--------
* 维护者侧 —— `build/sync_upstream.py`
    定期从游戏自带 `pack/locale.zip` 取官方 `en` 基准 → 用 `translate_core`
    引擎补翻新增/残留条目 → 重写 `zh/` 与 `zh/manifest.json` → commit & push。
* 客户端侧 —— 本模块
    只负责「把已经翻好的 `zh` 包从 GitHub 同步到本地」，**不在用户机器上跑翻译引擎**。
    `patch_tool.py` 的「② 同步最新汉化」即调用 `fetch_manifest()` + `sync_pack()`。

多源容错
--------
依次尝试下面三个源，任一可用即停止；某源下载/校验失败会自动换下一个源重试。

1. GitHub Pages   —— 本仓库自己的站点，推送后约 1 分钟生效，最"新"
2. jsDelivr CDN   —— 国内一般可直连（有缓存，最长约 12 小时）
3. GitHub Raw     —— 最快，但部分网络环境不可达

可用环境变量 `PCCN_SOURCE` 覆盖为自定义镜像的 base url（仓库地址或 zh 目录地址都可）。

清单协议（`zh/manifest.json`）
------------------------------
    {
      "schema": 1,
      "pack": "pixel-composer-cn",
      "version": "1.0.3",            # 汉化包版本
      "game_version": 122000,        # 对应游戏 Locale/version
      "built_at": "2026-09-28 21:30:00 +0800",
      "counts": {"words": 2096, "UI": 560, "nodes": 942, "junctions": 3},
      "files": {"words.json": {"size": 78266, "sha256": "..."}, ...}
    }

`files` 不含 manifest.json 自身。客户端按 sha256 只下载有变化的文件：
11MB 的中文字体只在首次同步时下载一次，之后每次同步通常只拉几个几十 KB 的 json。
"""
import hashlib
import json
import os
import shutil
import datetime
import urllib.request

SCHEMA = 1
PACK = "pixel-composer-cn"
MANIFEST_NAME = "manifest.json"

#: 清单随包一起放（`Locale/zh/manifest.json`）—— 版本号跟着包走，
#: 客户端读它就知道本地是哪个版本；语言目录额外多一个 json 对游戏无影响
#: （游戏只按固定文件名加载 words/nodes/UI/junctions/config/fonts/notes）。

REPO = "DC1024/pixel-composer-cn"
BRANCH = "main"

SOURCES = [
    ("GitHub Pages", "https://dc1024.github.io/pixel-composer-cn/zh/"),
    ("jsDelivr CDN", f"https://cdn.jsdelivr.net/gh/{REPO}@{BRANCH}/zh/"),
    ("GitHub Raw", f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/zh/"),
]

UA = "PixelComposer-CN-Patcher"
TIMEOUT = 20          # 清单与小文件
BIG_TIMEOUT = 180     # 字体等大文件


class SyncError(Exception):
    """同步过程中的可预期失败（网络不可达 / 校验不符 / 清单非法）。"""


# --------------------------------------------------------------------------
# 基础工具
# --------------------------------------------------------------------------
def sources():
    """待尝试的源列表；设置 PCCN_SOURCE 时把它排在最前。"""
    out = list(SOURCES)
    custom = os.environ.get("PCCN_SOURCE", "").strip()
    if custom:
        out.insert(0, ("自定义源 (PCCN_SOURCE)", normalize_source(custom)))
    return out


def normalize_source(base):
    """把仓库地址 / 网页地址规范成 zh/ 目录的 base url（以 / 结尾）。"""
    b = (base or "").strip()
    if not b:
        return ""
    if not b.startswith(("http://", "https://")):
        b = "https://" + b
    b = b.rstrip("/")
    for tail in ("/blob", "/tree", "/raw"):
        if b.endswith(tail):
            b = b[: -len(tail)]
    if not b.endswith("/zh"):
        b += "/zh"
    return b + "/"


def _get(url, timeout=TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_tree(dirpath, skip=(MANIFEST_NAME,)):
    """目录内所有文件的 {相对路径: {"size": n, "sha256": ...}}，路径统一用 /。"""
    out = {}
    if not os.path.isdir(dirpath):
        return out
    for base, _dirs, names in os.walk(dirpath):
        for n in names:
            if n in skip:
                continue
            p = os.path.join(base, n)
            rel = os.path.relpath(p, dirpath).replace(os.sep, "/")
            out[rel] = {"size": os.path.getsize(p), "sha256": sha256_file(p)}
    return out


def version_key(v):
    """'1.0.10' -> (1, 0, 10)，用于版本比较。"""
    parts = []
    for seg in str(v or "").replace("-", ".").split("."):
        num = "".join(ch for ch in seg if ch.isdigit())
        parts.append(int(num) if num else 0)
    return tuple(parts)


def build_manifest(zh_dir, version, game_version=None, log=None):
    """为 zh_dir 生成清单（维护者侧 build/sync_upstream.py 使用）。

    清单不含 manifest.json 自身；words/UI/nodes/junctions 的条目数一并写进 counts，
    便于客户端与用户直接看出包的内容。
    """
    counts = {}
    for name in ("words", "UI", "nodes", "junctions"):
        p = os.path.join(zh_dir, name + ".json")
        if not os.path.isfile(p):
            continue
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict):
                counts[name] = len(d)
        except Exception as e:
            if log:
                log(f"警告：{name}.json 解析失败（{e}），counts 里跳过")
    return {
        "schema": SCHEMA,
        "pack": PACK,
        "version": str(version),
        "game_version": game_version,
        "built_at": datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z"),
        "counts": counts,
        "files": hash_tree(zh_dir),
    }


# --------------------------------------------------------------------------
# 已安装包（本地）
# --------------------------------------------------------------------------
def installed_manifest_path(root):
    """root 数据目录下已安装 zh 包的清单路径。"""
    return os.path.join(root, "Locale", "zh", MANIFEST_NAME)


def read_installed_manifest(root):
    p = installed_manifest_path(root)
    if not os.path.isfile(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else None
    except Exception:
        return None


def installed_version(root):
    return (read_installed_manifest(root) or {}).get("version")


def installed_summary(roots):
    """(版本号, 说明串) —— 供「查看状态」展示；roots 都没有记录时版本为 None。"""
    vers = []
    for r in roots:
        v = installed_version(r)
        if v and v not in vers:
            vers.append(v)
    if not vers:
        return None, "未记录版本（可能是旧版工具或社区汉化包安装的）"
    if len(vers) == 1:
        return vers[0], f"v{vers[0]}"
    return vers[0], "多个数据目录版本不一致：" + ", ".join("v" + x for x in vers)


# --------------------------------------------------------------------------
# 远端清单
# --------------------------------------------------------------------------
def validate_manifest(man):
    if not isinstance(man, dict):
        raise SyncError("清单不是 JSON 对象")
    if man.get("schema") != SCHEMA:
        raise SyncError(f"清单 schema 不兼容：{man.get('schema')!r}（本工具支持 {SCHEMA}）")
    if man.get("pack") != PACK:
        raise SyncError(f"清单 pack 不符：{man.get('pack')!r}")
    files = man.get("files")
    if not isinstance(files, dict) or not files:
        raise SyncError("清单缺少 files")
    for rel, meta in files.items():
        if not isinstance(meta, dict) or "sha256" not in meta:
            raise SyncError(f"清单条目非法：{rel}")
        segs = rel.replace("\\", "/").split("/")
        if rel.startswith("/") or ".." in segs:
            raise SyncError(f"清单条目含非法路径：{rel}")
    return man


def fetch_manifest(log=None):
    """依次尝试各源拉取清单。

    返回 (manifest, source_name, base_url)；全部失败返回 (None, None, None)。
    失败原因通过 log 说明，不抛异常（调用方据此回退）。
    """
    def say(msg):
        if log:
            log(msg)

    for name, base in sources():
        try:
            man = validate_manifest(json.loads(_get(base + MANIFEST_NAME).decode("utf-8")))
        except Exception as e:
            say(f"源不可用（{name}）：{getattr(e, 'code', None) or type(e).__name__}")
            continue
        say(f"已获取在线清单 v{man.get('version')}（{name}）")
        return man, name, base
    return None, None, None


# --------------------------------------------------------------------------
# 同步
# --------------------------------------------------------------------------
def plan_files(man, local_hashes_list):
    """需要下载的文件：在任一已安装目录中缺失或 sha256 不符。"""
    need = []
    for rel, meta in sorted(man["files"].items()):
        want = meta.get("sha256")
        if any((h.get(rel) or {}).get("sha256") != want for h in local_hashes_list):
            need.append(rel)
    return need


def _download(base, rel, meta):
    timeout = BIG_TIMEOUT if int(meta.get("size") or 0) > (2 << 20) else TIMEOUT
    try:
        data = _get(base + rel, timeout)
    except Exception as e:
        raise SyncError(f"下载失败 {rel}: {getattr(e, 'code', None) or e}")
    if int(meta.get("size", -1)) != len(data):
        raise SyncError(f"大小不符 {rel}: 期望 {meta.get('size')}，实得 {len(data)}")
    if sha256_bytes(data) != meta.get("sha256"):
        raise SyncError(f"校验不符 {rel}")
    return data


def _local_copy(rel, local_dirs, dst):
    """从任一已安装目录拷贝未变化的文件（其 sha256 已与远端一致）。"""
    for d in local_dirs:
        p = os.path.join(d, *rel.split("/"))
        if os.path.isfile(p):
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(p, dst)
                return True
            except Exception:
                return False
    return False


def sync_pack(man, base, local_dirs, dest, log=None):
    """按需把远端 zh 包重建到 dest（完整包）。

    参数
      man         远端清单
      base        首选源 base url
      local_dirs  各数据目录当前 zh 包路径（用于比对 + 复用未变文件）
      dest        输出目录（会被清空重建）

    返回 (status, n_downloaded)：
      "uptodate" —— 各本地目录都与远端一致，未做任何改动
      "ready"    —— dest 已生成完整包，等待调用方安装
    失败抛 SyncError。
    """
    def say(msg):
        if log:
            log(msg)

    local_hashes = [hash_tree(d) for d in local_dirs]
    need = plan_files(man, local_hashes)
    if not need:
        return "uptodate", 0

    if os.path.isdir(dest):
        shutil.rmtree(dest, ignore_errors=True)
    os.makedirs(dest, exist_ok=True)

    say(f"需同步 {len(need)} 个文件，其余从本地复用")
    tried, ok = [], False
    candidates = [b for _n, b in sources() if b != base]
    for b in [base] + candidates:
        if b in tried:
            continue
        tried.append(b)
        try:
            for rel in need:
                data = _download(b, rel, man["files"][rel])
                p = os.path.join(dest, *rel.split("/"))
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, "wb") as f:
                    f.write(data)
                say(f"已下载 {rel}（{len(data)} 字节）")
            ok = True
            break
        except SyncError as e:
            say(f"该源失败：{e}")
            # 清掉半成品，换源重来
            for rel in need:
                p = os.path.join(dest, *rel.split("/"))
                if os.path.isfile(p):
                    os.remove(p)
    if not ok:
        raise SyncError("所有源都无法完整下载汉化包")

    # 未变化的文件从本地复用；本地也没有（首次同步）就补下载
    for rel in man["files"]:
        if rel in need:
            continue
        p = os.path.join(dest, *rel.split("/"))
        if os.path.isfile(p):
            continue
        if not _local_copy(rel, local_dirs, p):
            data = _download(base, rel, man["files"][rel])
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as f:
                f.write(data)
            say(f"已下载 {rel}（{len(data)} 字节）")

    with open(os.path.join(dest, MANIFEST_NAME), "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=1)
    return "ready", len(need)
