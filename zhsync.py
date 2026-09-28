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

**大文件（>2 MB，实际就是 11 MB 中文字体）会改用「CDN 优先」的顺序** ——
实测 Pages 对静态大文件限速明显（同一机器上 25 KB/s vs jsDelivr 71 KB/s），
详见 `_download_order()`。小文件仍保持 Pages 优先。

可用环境变量 `PCCN_SOURCE` 覆盖为自定义镜像的 base url（仓库地址或 zh 目录地址都可）。

清单协议（`zh/manifest.json`）
------------------------------
    {
      "schema": 1,
      "pack": "pixel-composer-cn",
      "version": "1.0.3",            # 汉化包版本
      "game_version": 122000,        # 对应游戏 Locale/version
      "built_at": "2026-09-28 21:30:00 +0800",
      "counts": {"words": 2096, "UI": 560, "nodes": 942, "junctions": 3, "welcome": 33},
      "files": {"words.json": {"size": 78266, "sha256": "..."}, ...}
    }

`files` 不含 manifest.json 自身。客户端按 sha256 只下载有变化的文件：
11MB 的中文字体只在首次同步时下载一次，之后每次同步通常只拉几个几十 KB 的 json。

仓库里的清单描述**完整包**；安装到本地的清单会多一个 `"selected"` 字段，
记录用户这次选了哪些模块（"按选中区域汉化"）。该字段不参与哈希比对，
只用来判断"模块选择是否变了、要不要重装"（见 `installed_signature()`）。

按选中区域汉化
--------------
`MODULES` 列出可逐项开关的汉化区域（界面词条 / 面板与对话框 / 节点 / 连接点 /
中文字体 / 入门指南示例）。**取消勾选 = 不安装对应文件**，游戏需要时会回退到
内置 en —— 干净、可逆；千万不能改成"写入英文副本"，那样包内字节永远与清单
对不上，同步会陷入"每次都重下整包"的循环。

⚠️ 哈希按**原始字节**计算，因此包内文件在「仓库 / 工作区 / 各下载源」上必须是
同一份字节 —— 这靠仓库根的 `.gitattributes` 保证（文本统一 LF、字体按 binary）。
详见 `sha256_bytes()` 里记录的踩坑说明（不要把 CRLF 归一加回来，会误伤字体）。

⚠️ 拼下载 URL 必须过 `_url()` 做百分号编码。`zh/welcome/**` 的路径里带空格
（``Getting started/000 UI/000 Introduction.pxc``），直接 `base + rel` 拼出来的
URL 三个源都取不到（实测 Pages 返回 000），而本地文件路径**不能**编码。
详见 `_url()` 的踩坑说明。
"""
import hashlib
import json
import os
import re
import shutil
import datetime
import urllib.error
import urllib.parse
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


# --------------------------------------------------------------------------
# 汉化模块（"按选中区域汉化"用）
# --------------------------------------------------------------------------
#: 用户可以逐项开关的汉化区域。第三项是该模块在 zh 包里的相对路径判定：
#: 以 "/" 结尾表示"整个目录"，否则是精确文件名。
#:
#: 设计要点：**取消勾选 = 不安装该文件**（而不是写入英文）。游戏在需要某个键时
#: 会回退到内置 en，所以少一个文件是安全且干净的；反过来若写入英文副本，
#: 包内字节就永远与线上清单对不上，同步会陷入"每次都重下"的循环。
MODULES = (
    ("words",     "界面词条",       ("words.json",)),
    ("ui",        "面板与对话框",   ("UI.json",)),
    ("nodes",     "节点名称与提示", ("nodes.json",)),
    ("junctions", "连接点名称",     ("junctions.json",)),
    ("fonts",     "中文字体",       ("fonts/",)),
    ("welcome",   "入门指南示例",   ("welcome/",)),
)

MODULE_IDS = tuple(m[0] for m in MODULES)
MODULE_LABEL = {m[0]: m[1] for m in MODULES}

#: 无论选了哪些模块都必须安装的文件（游戏读取的配置，不属于任何可选项）
ALWAYS_FILES = ("config.json",)


def rel_module(rel):
    """返回该相对路径属于哪个模块；不属于任何可选模块时返回 None。"""
    for mid, _label, patterns in MODULES:
        for pat in patterns:
            if pat.endswith("/"):
                if rel.startswith(pat):
                    return mid
            elif rel == pat:
                return mid
    return None


def resolve_modules(spec=None):
    """把用户输入解析成模块 id 列表。

    接受 None / "all" / "default" → 全部；
    也接受 "words,ui" 这样的逗号（或空格）分隔列表；
    含 None 之外的空列表被视为"全部"，避免误把用户锁在英文界面上。
    """
    if spec is None:
        return list(MODULE_IDS)
    items = spec
    if isinstance(items, str):
        s = items.strip().lower()
        if s in ("", "all", "default", "full"):
            return list(MODULE_IDS)
        if s in ("none", "empty"):
            return []
        items = [x for x in re.split(r"[,\s]+", s) if x]
    out = []
    for x in items:
        k = str(x).strip().lower()
        if k in ("all", "default", "full"):
            return list(MODULE_IDS)
        if k not in MODULE_IDS:
            raise SyncError(f"未知汉化模块：{x}（可选：{', '.join(MODULE_IDS)}）")
        if k not in out:
            out.append(k)
    return out


def module_summary(modules):
    """给日志用的一句话描述，例如 "5/6 模块（未选：中文字体）"."""
    modules = list(modules)
    off = [MODULE_LABEL[m] for m in MODULE_IDS if m not in modules]
    if not off:
        return f"{len(MODULE_IDS)}/{len(MODULE_IDS)} 模块（全部）"
    return f"{len(modules)}/{len(MODULE_IDS)} 模块（未选：{'、'.join(off)}）"


def keep_rel(rel, modules):
    """该文件在当前选择下是否应该安装。"""
    if rel in ALWAYS_FILES:
        return True
    m = rel_module(rel)
    if m is None:
        # 不认识的文件（例如将来新增的目录）默认保留，宁可多装也别漏
        return True
    return m in modules


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


def _url(base, rel):
    """把 base + 包内相对路径拼成**可用的 URL**。

    必须对路径做百分号编码：`welcome/**` 的路径里带空格
    （``Getting started/000 UI/000 Introduction.pxc``）。HTTP 客户端不会替你编码，
    原样拼出来的 URL 会让 GitHub Pages / jsDelivr / Raw 全部取不到该文件
    —— 实测返回码 000（连接直接失败），`%20` 编码后 200 正常
    （2026-09-28 踩到：41 个文件只有 8 个能同步下来，32 个 welcome 全失败）。

    ``safe="/"`` 保留路径分隔符；非 ASCII 字符会被编码成 UTF-8 的百分号序列，
    这正是 URL 规范要求的写法，三个下载源都认。

    注意：**只编码 URL**。本地文件路径（_local_copy / os.path.join）绝对不要过这里，
    否则会把文件名里的 %20 当成真实字符。"""
    return base + urllib.parse.quote(rel, safe="/")


def _get(url, timeout=TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def sha256_bytes(data):
    """包内文件的哈希一律按**原始字节**计算（不做任何换行归一）。

    前提：同一份文件在「仓库 blob / 工作区 / 各下载源」上必须是同样的字节。
    这由仓库根的 `.gitattributes` 保证：
        zh/*.json           text eol=lf   # 文本统一 LF
        zh/fonts/*.ttf      binary        # 字体不做任何换行处理

    ⚠️ 2026-09-28 踩过的坑（别再把归一化加回来）：
    Windows 上 `core.autocrlf=true` 时工作区是 CRLF、Git 仓库里是 LF，
    同一个 junctions.json 本地 349 B / 线上 330 B，哈希永远对不上 →
    每次同步都误判"文件变了"而重下整包（含 11 MB 字体）。
    当时一度改成"把 CRLF 归一后再算哈希"，但那样会**误伤字体**：
    LXGW 字体本身就含 4926 处 0x0D0A 字节对，归一等于把字体改坏，
    而且会让"字体被损坏"这种情况也哈希相同而检测不出来。
    正解是在**提交层面**统一换行（.gitattributes），而不是在哈希层面抹平差异。
    """
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
    # 入门指南示例：按 .pxc 个数计（这些文件是二进制容器，不是 JSON 词条）
    welcome = os.path.join(zh_dir, "welcome")
    if os.path.isdir(welcome):
        n = 0
        for _base, _dirs, names in os.walk(welcome):
            n += sum(1 for x in names if x.lower().endswith(".pxc"))
        if n:
            counts["welcome"] = n
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


def installed_modules(root):
    """该目录已安装的模块列表；没有记录（旧版工具装的）返回 None。"""
    man = read_installed_manifest(root)
    if not man:
        return None
    sel = man.get("selected")
    if not isinstance(sel, list):
        return None
    return [m for m in MODULE_IDS if m in sel]


def installed_signature(roots):
    """各数据目录的 (版本, 模块选择) 组合，用于判断"要不要重装"。

    模块选择必须参与判断：用户取消勾选某个模块时，文件数可能一个都没变，
    只看哈希会误判成"已是最新"，取消就永远不生效。
    """
    out = []
    for r in roots:
        man = read_installed_manifest(r) or {}
        sel = man.get("selected")
        sel = tuple(m for m in MODULE_IDS if m in sel) if isinstance(sel, list) else None
        out.append((man.get("version"), sel))
    return out


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


def version_key(v):
    """把 ``"1.2.0"`` 解析成 ``(1, 2, 0)`` 以便比较；解析不了的段按 0 算。

    清单里的 ``version`` 是字符串，直接比大小会踩 ``"1.10.0" < "1.9.0"`` 这种坑。
    """
    try:
        return tuple(int(x) if str(x).isdigit() else 0 for x in str(v).strip().split("."))
    except Exception:
        return ()


def fetch_manifest(log=None, floor=None):
    """依次尝试各源拉取清单。

    返回 (manifest, source_name, base_url)；全部失败返回 (None, None, None)。
    失败原因通过 log 说明，不抛异常（调用方据此回退）。

    ``floor`` 是可接受的最低版本（通常传本地已装的最高版本）：某个源返回比它
    **更旧**的清单时不采用，继续问下一个源。

    为什么要这道闸（2026-09-28 实测）：jsDelivr 对分支引用（``@main``）有较长
    缓存，推送后一段时间内它仍在返回**上一个版本**的清单 —— 实测 v1.2.1 推送后
    ``zh/manifest.json`` 在 jsDelivr 上还是 ``v1.0.3 / 8 个文件``（Pages 和 Raw
    都是 ``v1.2.0 / 41 个文件``）。正常情况 Pages 最先命中、拿到的是最新的，不会
    出事；但一旦 Pages 临时不可达（实测出现过直接返回 000），按"取到第一个就返回"
    就会**把用户已经装好的包降级成 8 个文件**。所以加了这道闸。

    没有源达到 ``floor`` 时返回 (None, None, None)，让调用方走既有的"离线"分支
    —— 那条路会回退到随附包，不会把用户的包换旧。
    """
    def say(msg):
        if log:
            log(msg)

    floor_key = version_key(floor) if floor else ()
    for name, base in sources():
        try:
            man = validate_manifest(json.loads(_get(_url(base, MANIFEST_NAME)).decode("utf-8")))
        except Exception as e:
            say(f"源不可用（{name}）：{getattr(e, 'code', None) or type(e).__name__}")
            continue
        key = version_key(man.get("version"))
        if floor_key and key and key < floor_key:
            say(f"忽略 {name} 上的旧清单 v{man.get('version')}"
                f"（低于本地 v{floor}，可能是 CDN 缓存），换下一个源…")
            continue
        say(f"已获取在线清单 v{man.get('version')}（{name}）")
        return man, name, base
    return None, None, None


# --------------------------------------------------------------------------
# 同步
# --------------------------------------------------------------------------
def plan_files(man, local_hashes_list, only=None):
    """需要下载的文件：在任一已安装目录中缺失或 sha256 不符。

    ``only`` 给出模块 id 列表时，只考虑这些模块的文件（"按选中区域汉化"用）；
    未选中的模块既不下载也不算"不一致"，否则每次同步都会误报有更新。
    """
    sel = set(MODULE_IDS) if only is None else set(only)
    need = []
    for rel, meta in sorted(man["files"].items()):
        if not keep_rel(rel, sel):
            continue
        want = meta.get("sha256")
        if any((h.get(rel) or {}).get("sha256") != want for h in local_hashes_list):
            need.append(rel)
    return need


def _is_pages(base):
    """判断某个 base 是不是 GitHub Pages 站点。"""
    try:
        return (urllib.parse.urlsplit(base).hostname or "").endswith(".github.io")
    except Exception:
        return False


#: 超过这个体积就重新排源（见 _download_order）
BIG_FILE = 2 << 20      # 2 MB


def _download_order(rel, meta, base, all_bases):
    """单个文件的源尝试顺序。

    大文件（>2 MB，实际就是那 11 MB 中文字体）把 **GitHub Pages 排到最后**：
    Pages 对静态大文件明显限速，2026-09-28 实测同一台机器下 11 MB 字体的速度是 ——

        GitHub Pages   24.7 KB/s     （100 秒只下到 2.47 MB，必然撞 180 秒超时）
        jsDelivr CDN   70.6 KB/s
        GitHub Raw     72.3 KB/s

    也就是 Pages 需要约 7.5 分钟、另外两个约 2.6 分钟。首次同步本来就要下这个字体，
    让用户先白等 3 分钟超时再换源毫无意义，所以这里直接换序；小文件仍保持
    Pages 优先（它是推送后最新的那个源）。
    """
    order = [base] + [b for b in (all_bases or []) if b != base]
    if int(meta.get("size") or 0) > BIG_FILE:
        order = ([b for b in order if not _is_pages(b)]
                 + [b for b in order if _is_pages(b)])
    return order


def _download(base, rel, meta, bases=None, log=None, order=None):
    """下载单个文件并校验（大小 + sha256）。

    ``order`` 给出完整的源尝试顺序（见 `_download_order`）；不传则用
    ``[base] + bases``。任一源取不到/校验不过就换下一个源重试，
    不至于因为一个文件而让整次同步失败。

    ``log`` 用于报告换源 —— 首次同步要拉 11 MB 中文字体，慢的时候界面上
    几分钟没动静很像"卡死"，所以每次换源都留一行痕迹。
    """
    timeout = BIG_TIMEOUT if int(meta.get("size") or 0) > BIG_FILE else TIMEOUT
    if order is None:
        order = [base] + [b for b in (bases or []) if b != base]
    last = None
    for i, b in enumerate(order):
        try:
            data = _get(_url(b, rel), timeout)
        except Exception as e:
            last = e
            if log and i + 1 < len(order):
                log(f"  {rel} 在当前源取不到（{getattr(e, 'code', None) or type(e).__name__}），换下一个源…")
            continue
        if int(meta.get("size", -1)) != len(data):
            last = SyncError(f"大小不符: 期望 {meta.get('size')}，实得 {len(data)}")
            continue
        if sha256_bytes(data) != meta.get("sha256"):
            last = SyncError("内容与清单 sha256 不一致")
            continue
        if i:
            _LAST_SOURCE_USED.append(b)
        return data
    reason = getattr(last, "code", None) or last or "无可用源"
    raise SyncError(f"下载失败 {rel}: {reason}")


#: 最近一次 _download 换源记录（诊断用，不参与逻辑）
_LAST_SOURCE_USED = []


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


def sync_pack(man, base, local_dirs, dest, log=None, only=None):
    """按需把远端 zh 包重建到 dest。

    参数
      man         远端清单
      base        首选源 base url
      local_dirs  各数据目录当前 zh 包路径（用于比对 + 复用未变文件）
      dest        输出目录（会被清空重建）
      only        只同步这些模块（None = 全部）—— 见 plan_files()

    返回 (status, n_downloaded)：
      "uptodate" —— 各本地目录都与远端一致，未做任何改动
      "ready"    —— dest 已生成完整包，等待调用方安装
    失败抛 SyncError。

    注意：``only`` 生效时 dest 里**只会有被选中模块的文件** + 必需的配置文件。
    "未选中 = 不安装"是有意的：游戏缺文件时会回退到内置 en，
    而写入英文副本会让包内字节永远与清单对不上，同步就会陷进重复下载。
    """
    def say(msg):
        if log:
            log(msg)

    sel = set(MODULE_IDS) if only is None else set(only)
    wanted = {rel: meta for rel, meta in man["files"].items() if keep_rel(rel, sel)}

    local_hashes = [hash_tree(d) for d in local_dirs]
    need = plan_files(man, local_hashes, only)
    if not need:
        return "uptodate", 0

    if os.path.isdir(dest):
        shutil.rmtree(dest, ignore_errors=True)
    os.makedirs(dest, exist_ok=True)

    say(f"需同步 {len(need)} 个文件，其余从本地复用")
    tried, ok = [], False
    candidates = [b for _n, b in sources() if b != base]
    all_bases = [base] + candidates
    for b in [base] + candidates:
        if b in tried:
            continue
        tried.append(b)
        try:
            for rel in need:
                # 按文件挑源顺序（大文件走 CDN 优先）+ 逐源回退：
                # 单个文件在某源上取不到时自动换下一个源，不必因为一个文件丢弃整批
                data = _download(b, rel, man["files"][rel], log=say,
                                 order=_download_order(rel, man["files"][rel], b, all_bases))
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
    for rel in wanted:
        if rel in need:
            continue
        p = os.path.join(dest, *rel.split("/"))
        if os.path.isfile(p):
            continue
        if not _local_copy(rel, local_dirs, p):
            data = _download(base, rel, man["files"][rel], log=say,
                             order=_download_order(rel, man["files"][rel], base, all_bases))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as f:
                f.write(data)
            say(f"已下载 {rel}（{len(data)} 字节）")

    with open(os.path.join(dest, MANIFEST_NAME), "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=1)
    return "ready", len(need)
