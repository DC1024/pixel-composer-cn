#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pixel Composer 一键汉化工具（Windows / Linux / macOS · 标准库 only）
作者：DC1024  <https://github.com/DC1024/pixel-composer-cn>
功能：
  1) 安装汉化   : 把自带 zh 汉化包复制到 PixelComposer 运行时 Locale 目录，并启用中文
  2) 同步最新汉化: 从 GitHub 拉取「维护者定期同步上游、已经翻好」的最新汉化包并安装
                  （只下载成品，本地不再跑翻译引擎）；断网/仓库不可达时自动回退随附包
  3) 恢复英文   : 切回 en，并把「入门指南」示例文件还原成官方英文原版
  4) 还原上一版 : 回滚到最近一次安装前的汉化包（zh.bak_*）
  5) 查看状态   : 显示当前语言、目录、包版本与已选汉化区域
  6) 汉化工作区标签 : 自带布局改名成中文；同时改写 pack/layouts.zip 的条目名
                      （只改文件名会被游戏重新解出英文名还原，故必须连 zip 一起改）
  7) 还原布局名 : 把上面两条改动还原成英文
  8) 按区域汉化 : 可逐项勾选要汉化的区域（界面词条 / 面板与对话框 / 节点 / 连接点 /
                  中文字体 / 入门指南示例），默认全部汉化。取消勾选 = 不安装该文件，
                  游戏会回退到内置英文，方便保留英文习惯。
  9) 入门指南   : 把 Getting started / Sample Projects / Templates 里教程页的说明文字
                  也换成中文（原地覆盖同名 .pxc，文件名保持英文，可一键还原）
 10) 残留清点   : 列出旧社区汉化包（zh/ + Welcome files/ + 汉化 EXE）在安装目录里留下的
                  文件清单（路径 / 大小 / 文件数）。**只列出，不删除、不移动**。

平台说明：
  Windows  数据目录 %LOCALAPPDATA%\\PixelComposer（或 persistPreference.json 重定向处）
  Linux    数据目录 $XDG_DATA_HOME/PixelComposer；原生版与 Proton 前缀都探测
  macOS    数据目录 ~/Library/Application Support/PixelComposer
  Linux 上 tkinter 常需另装（Debian/Ubuntu: python3-tk；Arch: tk），缺失时自动
  退回命令行界面 —— 一键脚本见 install.sh。
  安装目录可用环境变量覆盖：PIXELCOMPOSER_DIR（游戏目录）、STEAM_ROOT（Steam 根）。
依赖：仅 Python 标准库（tkinter 做界面，缺失时自动退回命令行）
配色：与 Pixel Composer 官方 default 主题一致（Themes/default/values.json）
"""
import os, sys, json, shutil, zipfile, tempfile, datetime, re, glob

IS_WIN = os.name == "nt"
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

STEAM_APPID = "2299510"
STEAM_APP_DIRNAME = "Pixel Composer"
STEAM_REG_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Steam App 2299510"
COMMON_STEAM = [
    r"D:\SteamLibrary\steamapps\common\Pixel Composer",
    r"E:\SteamLibrary\steamapps\common\Pixel Composer",
    r"C:\Program Files (x86)\Steam\steamapps\common\Pixel Composer",
    r"C:\Program Files\Steam\steamapps\common\Pixel Composer",
    r"D:\Steam\steamapps\common\Pixel Composer",
]

def here():
    return os.path.dirname(os.path.abspath(__file__))

def is_frozen():
    return getattr(sys, "frozen", False)

def resource_dir():
    """随附资源（zh/、app_icon.ico、translate_core.py）所在目录。
    PyInstaller onefile 会解包到 sys._MEIPASS；源码运行时即脚本目录。"""
    if is_frozen():
        return getattr(sys, "_MEIPASS", here())
    return here()

def scratch_dir():
    """可写的临时工作目录（_en_tmp / _zh_gen）。"""
    if is_frozen():
        base = os.path.join(tempfile.gettempdir(), "pixelcomposer_hh")
    else:
        base = here()
    try:
        os.makedirs(base, exist_ok=True)
    except Exception:
        base = tempfile.gettempdir()
    return base

def _bootstrap_paths():
    """冻结(EXE)运行时，把随附目录加入 sys.path，便于 import translate_core。"""
    if is_frozen():
        rd = resource_dir()
        if rd not in sys.path:
            sys.path.insert(0, rd)

def _setup_stdio():
    """让命令行输出的字节在不同运行方式下保持一致（UTF-8）。

    背景（2026-09-28 实测）：PyInstaller 打包出的 windowed EXE 在**输出被重定向
    到文件或管道**时，`sys.stdout.encoding` 会退化成系统 ANSI 代码页（简体中文
    Windows 上是 cp936/GBK），而同一个脚本用 `python patch_tool.py` 跑却是
    UTF-8 —— 于是 `--version` 的「汉化工具」四个字在 EXE 下是 `BA BA BB AF …`，
    在源码方式下是 `E6 B1 89 …`。抓日志/做校验的人很容易把前者当成乱码。

    **真控制台不做处理**：Windows 下 Python 3.6+ 直接调 `WriteConsoleW` 写
    宽字符，编码属性只影响重定向后的字节，所以控制台显示本来就是对的。
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
            pass      # 被替换成 StringIO / 老版本解释器：忽略即可

# ------------------------- 路径探测 -------------------------
def _uniq(paths):
    """按真实路径去重（保留先出现的那个写法）。"""
    out = []
    for p in paths:
        if not p:
            continue
        try:
            rp = os.path.realpath(p)
        except Exception:
            rp = os.path.abspath(p)
        if rp not in [os.path.realpath(x) for x in out]:
            out.append(p)
    return out


def _vdf_library_paths(vdf):
    """从 libraryfolders.vdf 里抠出 "path" 值（不引入 VDF 解析依赖）。"""
    out = []
    try:
        with open(vdf, encoding="utf-8", errors="replace") as f:
            text = f.read()
        for m in re.finditer(r'"path"\s*"([^"]+)"', text):
            out.append(m.group(1).replace("\\\\", "\\"))
    except Exception:
        pass
    return out


def steam_library_dirs():
    """所有可能含 steamapps 的 Steam 库目录。

    覆盖：环境变量 STEAM_ROOT → 各平台默认安装位置 → libraryfolders.vdf 登记的
    外挂库 → Linux 上常见挂载点（/media、/run/media、/mnt）。
    """
    cands = []
    ev = os.environ.get("STEAM_ROOT") or os.environ.get("STEAM_DIR")
    if ev:
        cands.append(ev)
    home = os.path.expanduser("~")
    if IS_WIN:
        cands += [r"C:\Program Files (x86)\Steam", r"C:\Program Files\Steam",
                  r"D:\Steam", r"E:\Steam"]
        try:
            import winreg
            for hive, key, val in (
                (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
            ):
                try:
                    k = winreg.OpenKey(hive, key, 0, winreg.KEY_READ)
                    v, _ = winreg.QueryValueEx(k, val)
                    winreg.CloseKey(k)
                    cands.append(os.path.normpath(v))
                except Exception:
                    pass
        except Exception:
            pass
    elif IS_MAC:
        cands += [os.path.join(home, "Library", "Application Support", "Steam")]
    else:
        cands += [
            os.path.join(home, ".steam", "steam"),
            os.path.join(home, ".steam", "root"),
            os.path.join(home, ".local", "share", "Steam"),
            os.path.join(home, ".var", "app", "com.valvesoftware.Steam", "data", "Steam"),
            os.path.join(home, "snap", "steam", "common", ".local", "share", "Steam"),
            "/usr/share/steam", "/usr/lib/steam",
        ]
        for pat in ("/media/*/SteamLibrary", "/media/*/*/SteamLibrary",
                    "/run/media/*/*/SteamLibrary", "/run/media/*/SteamLibrary",
                    "/mnt/*/SteamLibrary", "/mnt/SteamLibrary"):
            cands += glob.glob(pat)
    out = list(cands)
    for root in cands:
        for sub in ("steamapps", "SteamApps"):
            vdf = os.path.join(root, sub, "libraryfolders.vdf")
            if os.path.isfile(vdf):
                out += _vdf_library_paths(vdf)
    return _uniq(out)


def find_install_dir():
    """定位游戏安装目录（含 pack/locale.zip）。"""
    ev = os.environ.get("PIXELCOMPOSER_DIR")
    if ev and os.path.isdir(ev):
        return ev
    if IS_WIN:
        try:
            import winreg
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, STEAM_REG_KEY, 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(k, "InstallLocation")
            winreg.CloseKey(k)
            p = os.path.normpath(val.strip('"'))
            if os.path.isdir(p):
                return p
        except Exception:
            pass
        for p in COMMON_STEAM:
            if os.path.isdir(p):
                return p
    for lib in steam_library_dirs():
        for rel in (os.path.join("steamapps", "common", STEAM_APP_DIRNAME),
                    os.path.join("steamapps", "Common", STEAM_APP_DIRNAME),
                    os.path.join("common", STEAM_APP_DIRNAME),
                    STEAM_APP_DIRNAME):
            p = os.path.join(lib, rel)
            if not os.path.isdir(p):
                continue
            if os.path.isfile(os.path.join(p, "pack", "locale.zip")):
                return p
            # macOS 版把 executables 放在 PixelComposer/ 子目录里
            if IS_MAC and os.path.isdir(os.path.join(p, "PixelComposer")):
                return p
    # 便携 / 手动解压：就在当前目录
    if os.path.isdir(os.path.join(os.getcwd(), "pack")):
        return os.getcwd()
    return None


def _proton_data_roots(install):
    """Proton 前缀里的 Windows 侧数据目录（Linux 用 Proton 跑 Windows 版时）。"""
    out = []
    if not install:
        return out
    steamapps = os.path.dirname(os.path.dirname(install))
    users = os.path.join(steamapps, "compatdata", STEAM_APPID, "pfx",
                         "drive_c", "users")
    if os.path.isdir(users):
        try:
            for u in os.listdir(users):
                out.append(os.path.join(users, u, "AppData", "Local", "PixelComposer"))
        except Exception:
            pass
    return out


def data_root_candidates(install=None):
    """按平台给出数据目录候选。

    GameMaker 各平台把 game_save_id 放在不同位置：
    Windows = %LOCALAPPDATA%、macOS = ~/Library/Application Support、
    Linux = $XDG_DATA_HOME（通常是 ~/.local/share）。
    """
    home = os.path.expanduser("~")
    out = []
    if IS_WIN:
        out.append(os.path.join(home, "AppData", "Local", "PixelComposer"))
    elif IS_MAC:
        out.append(os.path.join(home, "Library", "Application Support", "PixelComposer"))
        out.append(os.path.join(home, "Library", "Application Support", "Pixel Composer"))
    else:
        xdg = os.environ.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
        out.append(os.path.join(xdg, "PixelComposer"))
        out.append(os.path.join(xdg, "Pixel Composer"))
        out.append(os.path.join(home, ".local", "share", "PixelComposer"))
        out.append(os.path.join(home, ".config", "PixelComposer"))
        out += _proton_data_roots(install)
    if install:
        out.append(os.path.join(install, "PixelComposer"))
    return _uniq(out)


def _root_liveness(root):
    """给数据目录打个"像不像游戏真正在用"的分。

    实测（2026-09-28）：Pixel Composer 会把数据目录**重定向**到
    persistPreference.json 指定的位置 —— 本机就指到了安装目录下的
    ``Pixel Composer\\PixelComposer``，而 ``%LOCALAPPDATA%\\PixelComposer``
    里只剩一个指针和旧社区汉化包的残留（Locale/version 还停在 119009）。
    因此顺序不能只看"哪个是平台默认"，得看谁的数据是新的：
    Locale/version 越大越新，另外有 Welcome files/version 说明欢迎页也被解压过。
    """
    score = 0
    v = os.path.join(root, "Locale", "version")
    if os.path.isfile(v):
        try:
            with open(v, encoding="utf-8") as f:
                score += int(json.load(f).get("version") or 0) // 1000
        except Exception:
            pass
    if os.path.isfile(os.path.join(root, "Welcome files", "version")):
        score += 5
    return score


def find_all_data_roots(install=None):
    """返回所有可能的数据目录（含 Locale 与 preferences），按真实路径去重。

    覆盖：各平台默认位置、游戏安装子目录、Proton 前缀，以及各
    persistPreference.json 的 path 字段 —— 这样无论游戏从哪个目录读取，
    汉化包与语言设置都能生效。

    若一个都还没出现（游戏从未运行过），返回**首选候选**而不是空列表：
    否则首次安装会直接失败，而那恰恰是最需要一键汉化的场景。
    """
    bases = data_root_candidates(install)
    roots = [p for p in bases if os.path.isdir(p)]
    for base in bases:
        pp = os.path.join(base, "persistPreference.json")
        if not os.path.isfile(pp):
            continue
        try:
            d = json.load(open(pp, encoding="utf-8"))
            p = str(d.get("path", "")).strip()
        except Exception:
            continue
        if not p:
            continue
        p = p.replace("\\/", "/")
        if IS_WIN:
            p = p.replace("/", os.sep)
        if os.path.isdir(p):
            roots.append(p)
    roots = _uniq(roots)
    if not roots and bases:
        roots = [bases[0]]
    # 稳定的活跃度排序：游戏实际在用的目录排在最前（同分保持原候选顺序）
    roots.sort(key=_root_liveness, reverse=True)
    return roots


def find_runtime_dir():
    """兼容旧调用：返回第一个数据目录（通常是游戏实际读取处）。"""
    roots = find_all_data_roots(find_install_dir())
    if roots:
        return roots[0]
    return data_root_candidates(None)[0]

def find_keys_json(runtime):
    pref = os.path.join(runtime, "preferences")
    cand = []
    if os.path.isdir(pref):
        for name in os.listdir(pref):
            kp = os.path.join(pref, name, "keys.json")
            if os.path.isfile(kp): cand.append(kp)
    # 优先 1171
    for kp in cand:
        if "1171" in kp: return kp
    if cand: return cand[0]
    # 不存在则创建
    target = os.path.join(pref, "1171", "keys.json")
    return target

# ------------------------- 辅助 -------------------------
def log(msg, box=None):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    if box is not None:
        try:
            box.configure(state="normal")
            box.insert("end", line + "\n")
            box.see("end")
        except Exception:
            pass

def backup_and_copy(src, dst, logbox=None):
    if os.path.exists(dst) or os.path.islink(dst):
        ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        bak = f"{dst}.bak_{ts}"
        i = 1
        while os.path.exists(bak) or os.path.islink(bak):
            i += 1
            bak = f"{dst}.bak_{ts}_{i}"
        try:
            shutil.move(dst, bak)
        except Exception as e:
            log(f"备份失败，已中止写入以免破坏现有文件: {e}", logbox)
            return False
        log(f"已备份旧 zh -> {os.path.basename(bak)}", logbox)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copytree(src, dst, dirs_exist_ok=True)
    log(f"已写入: {dst}", logbox)
    return True

# ------------------- 汉化区域（按选中区域汉化）--------------------
#: 兜底模块表；正常走 zhsync.MODULES（两处保持一致）
FALLBACK_MODULES = (
    ("words",     "界面词条",       ("words.json",)),
    ("ui",        "面板与对话框",   ("UI.json",)),
    ("nodes",     "节点名称与提示", ("nodes.json",)),
    ("junctions", "连接点名称",     ("junctions.json",)),
    ("fonts",     "中文字体",       ("fonts/",)),
    ("welcome",   "入门指南示例",   ("welcome/",)),
)

WELCOME_DIRNAME = "Welcome files"


def _zhsync():
    try:
        import zhsync
        return zhsync
    except Exception:
        return None


def module_table():
    return getattr(_zhsync(), "MODULES", FALLBACK_MODULES)


def module_ids():
    return tuple(m[0] for m in module_table())


def module_label(mid):
    for i, l, _p in module_table():
        if i == mid:
            return l
    return mid


def resolve_modules(spec=None):
    """把 CLI/GUI 给的模块选择解析成 id 列表（None = 全部）。"""
    z = _zhsync()
    if z is not None and hasattr(z, "resolve_modules"):
        return z.resolve_modules(spec)
    if spec is None:
        return list(module_ids())
    items = re.split(r"[,\s]+", spec) if isinstance(spec, str) else list(spec)
    out = []
    for x in items:
        k = str(x).strip().lower()
        if k in ("all", "default", "full"):
            return list(module_ids())
        if k in module_ids() and k not in out:
            out.append(k)
    return out


def rel_module(rel):
    z = _zhsync()
    if z is not None and hasattr(z, "rel_module"):
        return z.rel_module(rel)
    for mid, _l, pats in module_table():
        for pat in pats:
            if pat.endswith("/"):
                if rel.startswith(pat):
                    return mid
            elif rel == pat:
                return mid
    return None


def keep_rel(rel, modules):
    """该文件在当前选择下是否安装（不认识的路径默认保留，宁可多装也别漏）。"""
    z = _zhsync()
    if z is not None and hasattr(z, "keep_rel"):
        return z.keep_rel(rel, modules)
    m = rel_module(rel)
    return m is None or m in set(modules)


def module_summary(modules):
    z = _zhsync()
    if z is not None and hasattr(z, "module_summary"):
        return z.module_summary(modules)
    off = [l for i, l, _p in module_table() if i not in set(modules)]
    return "全部模块" if not off else f"未选：{'、'.join(off)}"


def warn_module_combination(modules, logbox=None):
    mods = set(modules)
    text = [m for m in module_ids() if m in mods and m != "fonts"]
    if "fonts" not in mods and text:
        names = "、".join(module_label(m) for m in text if m != "welcome") or "入门指南示例"
        log(f"提示：勾选了「{names}」却未勾选「中文字体」——"
            " 中文字符可能显示成方块。想正常显示中文请补上「中文字体」；"
            "想整体保留英文习惯，请把这些文字区域一并取消。", logbox)


def backup_and_copy_selected(src, dst, modules, logbox=None):
    """只把选中模块的文件复制进 dst（未选中的不安装）。"""
    if os.path.exists(dst) or os.path.islink(dst):
        ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        bak = f"{dst}.bak_{ts}"
        i = 1
        while os.path.exists(bak) or os.path.islink(bak):
            i += 1
            bak = f"{dst}.bak_{ts}_{i}"
        try:
            shutil.move(dst, bak)
        except Exception as e:
            log(f"备份失败，已中止写入以免破坏现有文件: {e}", logbox)
            return False
        log(f"已备份旧 zh -> {os.path.basename(bak)}", logbox)
    os.makedirs(dst, exist_ok=True)
    n = 0
    for base, _dirs, names in os.walk(src):
        for nm in names:
            p = os.path.join(base, nm)
            rel = os.path.relpath(p, src).replace(os.sep, "/")
            if not keep_rel(rel, modules):
                continue
            t = os.path.join(dst, *rel.split("/"))
            os.makedirs(os.path.dirname(t), exist_ok=True)
            try:
                shutil.copy2(p, t)
                n += 1
            except Exception as e:
                log(f"写入失败 {rel}: {e}", logbox)
    log(f"已写入: {dst}（{n} 个文件 · {module_summary(modules)}）", logbox)
    return True


def mark_selection(zh_dir, modules):
    """把本次的汉化区域记进已安装清单的 "selected" 字段。

    必须记：取消勾选某个区域时文件数可能一个都没变，只按哈希比对会误判
    "已是最新"，取消就永远不生效（见 zhsync.installed_signature）。
    """
    p = os.path.join(zh_dir, "manifest.json")
    if not os.path.isfile(p):
        return
    try:
        with open(p, encoding="utf-8") as f:
            man = json.load(f)
    except Exception:
        return
    man["selected"] = list(modules)
    man["skipped"] = [m for m in module_ids() if m not in set(modules)]
    try:
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            json.dump(man, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def install_welcome(root, src, logbox=None, install=None):
    """把汉化包里的 welcome/**.pxc **按同名覆盖**到 <root>/Welcome files/。

    为什么原地覆盖同名文件、而不是整目录替换：
      * 官方 welcome_files.zip 每个教程页还配了 256×192 缩略图 PNG，
        整目录替换会把缩略图一起丢掉；
      * 文件名保持英文原名，游戏看到的仍是标准目录结构，不会出现中英两套重复项。
    被覆盖的原文件先备份到 <root>/Welcome files.bak_cn/（保持相对路径），
    可用「③ 恢复英文」一键还原。

    备份的来源是**游戏自带的 pack/welcome_files.zip**，而不是"当前文件"：
    第二次安装时当前文件已经是我们自己的中文版，若照抄当前文件，
    备份里存的就成了中文，「恢复英文」会还原出中文（实测踩过）。
    从官方 zip 取原版更权威，而且能顺带自愈已经存错的旧备份。

    另外：若目标目录缺配套缩略图（例如该数据目录只被解压过一部分），
    也会从同一个 zip 里补一份，让目录保持自洽。
    """
    wsrc = os.path.join(src, "welcome")
    if not os.path.isdir(wsrc):
        log("汉化包里没有入门指南内容（welcome/），跳过。", logbox)
        return 0
    dstroot = os.path.join(root, WELCOME_DIRNAME)
    bakroot = os.path.join(root, WELCOME_DIRNAME + ".bak_cn")
    zp = os.path.join(install, "pack", "welcome_files.zip") if install else None
    zf = None
    if zp and os.path.isfile(zp):
        try:
            zf = zipfile.ZipFile(zp)
        except Exception:
            zf = None

    def official(rel):
        """从官方 zip 取原版字节；不可用时返回 None。"""
        if zf is None:
            return None
        try:
            return zf.read(rel)
        except Exception:
            return None

    n = healed = 0
    for base, _dirs, names in os.walk(wsrc):
        for nm in names:
            p = os.path.join(base, nm)
            rel = os.path.relpath(p, wsrc).replace(os.sep, "/")
            t = os.path.join(dstroot, *rel.split("/"))
            bk = os.path.join(bakroot, *rel.split("/"))
            orig = official(rel)
            # 1) 备份原版（已有且正确就跳过；存错了就纠正过来）
            if orig is not None:
                cur = None
                if os.path.isfile(bk):
                    try:
                        with open(bk, "rb") as f:
                            cur = f.read()
                    except Exception:
                        cur = None
                if cur != orig:
                    try:
                        os.makedirs(os.path.dirname(bk), exist_ok=True)
                        with open(bk, "wb") as f:
                            f.write(orig)
                        if cur is not None:
                            healed += 1
                    except Exception:
                        pass
            elif not os.path.isfile(bk) and os.path.isfile(t):
                # 拿不到官方原版时，退而记录当前文件
                try:
                    os.makedirs(os.path.dirname(bk), exist_ok=True)
                    shutil.copy2(t, bk)
                except Exception:
                    pass
            # 2) 覆盖同名文件
            try:
                os.makedirs(os.path.dirname(t), exist_ok=True)
                shutil.copy2(p, t)
                n += 1
            except Exception as e:
                log(f"入门指南写入失败 {rel}: {e}", logbox)
                continue
            # 3) 补齐配套缩略图（缺了会让欢迎页显示空白）
            if rel.lower().endswith(".pxc"):
                png_rel = rel[:-4] + ".png"
                pt = os.path.join(dstroot, *png_rel.split("/"))
                if not os.path.isfile(pt):
                    data = official(png_rel)
                    if data:
                        try:
                            os.makedirs(os.path.dirname(pt), exist_ok=True)
                            with open(pt, "wb") as f:
                                f.write(data)
                        except Exception:
                            pass
    if zf is not None:
        try:
            zf.close()
        except Exception:
            pass
    if n:
        extra = f"（其中纠正 {healed} 个存错的备份）" if healed else ""
        log(f"入门指南示例：已汉化 {n} 个教程/示例文件"
            f"（原文件备份于 {os.path.basename(bakroot)}/）{extra}", logbox)
    else:
        log("入门指南示例：没有可写的文件。", logbox)
    return n


def restore_welcome(root, logbox=None):
    """从 <root>/Welcome files.bak_cn/ 还原原版入门指南文件。"""
    bakroot = os.path.join(root, WELCOME_DIRNAME + ".bak_cn")
    if not os.path.isdir(bakroot):
        return 0
    dstroot = os.path.join(root, WELCOME_DIRNAME)
    n = 0
    for base, _dirs, names in os.walk(bakroot):
        for nm in names:
            p = os.path.join(base, nm)
            rel = os.path.relpath(p, bakroot).replace(os.sep, "/")
            t = os.path.join(dstroot, *rel.split("/"))
            try:
                os.makedirs(os.path.dirname(t), exist_ok=True)
                shutil.copy2(p, t)
                n += 1
            except Exception:
                pass
    if n:
        log(f"已还原 {n} 个原版入门指南文件", logbox)
    return n


def selection_changed(roots, modules):
    """已安装记录的汉化区域与本次选择是否不同（含"旧版工具装的、没记录"）。"""
    z = _zhsync()
    if z is None or not hasattr(z, "installed_signature"):
        return False
    want = tuple(m for m in module_ids() if m in set(modules))
    for _ver, sel in z.installed_signature(roots):
        if sel != want:
            return True
    return False

def apply_extras(runtime, logbox=None):
    """把内置补充表（LOCALE_ADD / LOCALE_OVERRIDE）注入已安装的 zh 包。

    这两张表修的是「官方 en/words.json 里根本没登记、因此任何语言包都覆盖不到」
    的键（面板标题 toolbar_panel、面板右键菜单 lock_panel、工具栏/侧栏编辑器键族
    preview_edit_toolbar / nodes_toggle_sidebar 等），以及旧版机翻拆坏的句子。
    安装与更新两条路径都会调用，保证不会被覆盖回去。"""
    try:
        from translate_core import apply_locale_extras
    except Exception as e:
        log(f"补充词表不可用，跳过（不影响主流程）: {e}", logbox)
        return
    zh = os.path.join(runtime, "Locale", "zh")
    if not os.path.isdir(zh):
        return
    try:
        st = apply_locale_extras(zh)
    except Exception as e:
        log(f"补充词表注入失败: {e}", logbox)
        return
    if st.get("added") or st.get("overridden"):
        log(f"补充词表：新增 {st['added']} 条、纠正 {st['overridden']} 条", logbox)


def set_language(code, runtime, logbox=None):
    kp = find_keys_json(runtime)
    os.makedirs(os.path.dirname(kp), exist_ok=True)
    data = {}
    if os.path.exists(kp):
        try: data = json.load(open(kp, encoding="utf-8"))
        except Exception: data = {}
    if data.get("local") != code:
        data["local"] = code
        json.dump(data, open(kp, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        log(f"已设置界面语言 = {code}（重启软件后生效）", logbox)
    else:
        log(f"界面语言已是 {code}，无需修改", logbox)

def ensure_en(runtime, install, logbox=None):
    """确保目标 Locale/en 存在（游戏以此判断 Locale 目录有效）。

    顺序：本目录已有 → 从别的数据目录借一份 → 直接从游戏自带的
    ``pack/locale.zip`` 解出来。最后这条最关键：它是官方 en 基准的唯一权威来源，
    Linux/macOS 上数据目录布局与 Windows 不同，靠猜路径不如直接解包。
    """
    en_dst = os.path.join(runtime, "Locale", "en")
    if os.path.isdir(en_dst) and os.listdir(en_dst):
        return
    src = None
    if install:
        for cand in (os.path.join(install, "PixelComposer", "Locale", "en"),
                     os.path.join(install, "Locale", "en")):
            if os.path.isdir(cand):
                src = cand
                break
    for root in find_all_data_roots(install):
        if os.path.abspath(root) == os.path.abspath(runtime):
            continue
        cand = os.path.join(root, "Locale", "en")
        if os.path.isdir(cand):
            src = cand
            break
    if src:
        shutil.copytree(src, en_dst, dirs_exist_ok=True)
        log("已补齐默认 en 语言包", logbox)
        return
    # 从 pack/locale.zip 解出 en/
    if install:
        zp = os.path.join(install, "pack", "locale.zip")
        if os.path.isfile(zp):
            try:
                n = 0
                with zipfile.ZipFile(zp) as z:
                    for name in z.namelist():
                        if not name.startswith("en/") or name.endswith("/"):
                            continue
                        rel = name[len("en/"):]
                        t = os.path.join(en_dst, *rel.split("/"))
                        os.makedirs(os.path.dirname(t), exist_ok=True)
                        with open(t, "wb") as f:
                            f.write(z.read(name))
                        n += 1
                if n:
                    log(f"已从 pack/locale.zip 解出默认 en 语言包（{n} 个文件）", logbox)
                    return
            except Exception as e:
                log(f"从 locale.zip 解出 en 失败: {e}", logbox)
    os.makedirs(en_dst, exist_ok=True)
    log("警告：未找到 en 基准，已创建空目录（如界面异常请运行一次官方英文版）", logbox)

def _unused_legacy_note():
    """（已移除）早期「客户端本地翻译引擎」的 extract_en_base / regenerate_from_en。

    它们原先负责在用户机器上从 pack/locale.zip 抽 en 基准再用内置引擎补翻。
    现在改为一句话分工：**翻译只在维护者侧做一次**（见 build/sync_upstream.py），
    客户端只从 GitHub 下载翻好的成品包（见 sync_from_github）。
    保留本注释是为了让后来者知道这两条路径是「有意去掉」的，而不是丢了。
    """
    return None

# ------------------------- 主操作 -------------------------
def _install_pack(src, roots, install, logbox=None, modules=None):
    """把 src 汉化包装进所有数据目录，并启用中文。返回是否全部成功。"""
    modules = resolve_modules(modules)
    for root in roots:
        t = os.path.join(root, "Locale", "zh")
        if os.path.isdir(src):
            if not backup_and_copy_selected(src, t, modules, logbox):
                return False
        elif not backup_and_copy(src, t, logbox):
            return False
        apply_extras(root, logbox)
        ensure_en(root, install, logbox)
        set_language("zh", root, logbox)
        mark_selection(t, modules)
        if "welcome" in modules:
            install_welcome(root, src, logbox, install)
        else:
            # 取消勾选要把示例还原成英文原版 —— 否则"取消"看着像没生效
            restore_welcome(root, logbox)
    return True

def sync_from_github(roots, logbox=None, modules=None):
    """从 GitHub 同步「已经翻好」的汉化包（本地不再跑翻译引擎）。

    汉化流程改为：维护者定期同步上游官方语言包 → 补翻 → 推送 GitHub；
    用户侧只负责把成品包拉下来。返回 (status, src)：

      "uptodate" —— 已选区域内都与线上一致，无需安装
      "ready"    —— src = 已同步好的完整包目录，可直接安装
      "offline"  —— 清单/下载不可用（断网、仓库不可达等），调用方回退随附包

    ``modules`` 只影响"哪些文件算需要同步"，未选中的区域完全不参与比对，
    否则每次同步都会因为"少装了某个文件"而误报有更新。

    传给 ``fetch_manifest`` 的 ``floor`` 是本地已装的最高版本：jsDelivr 对
    ``@main`` 有较长缓存，推送后会有一段时间返回**上一版**的清单，加这道闸
    避免在 Pages 临时不可达时把用户装好的包降级（详见 ``zhsync.fetch_manifest``）。
    """
    try:
        import zhsync
    except Exception as e:
        log(f"同步模块不可用（{e}）", logbox)
        return "offline", None

    floor = None
    for r in roots:
        v = zhsync.installed_version(r)
        if v and (floor is None or zhsync.version_key(v) > zhsync.version_key(floor)):
            floor = v

    log("正在检查线上最新汉化包…", logbox)
    man, src_name, base = zhsync.fetch_manifest(lambda m: log(m, logbox), floor=floor)
    if not man:
        log("无法获取线上清单（网络不可用或仓库暂不可达）", logbox)
        return "offline", None

    local = [os.path.join(r, "Locale", "zh") for r in roots]
    local = [d for d in local if os.path.isdir(d)]
    dest = os.path.join(scratch_dir(), "_zh_sync")
    try:
        status, n = zhsync.sync_pack(man, base, local, dest,
                                     lambda m: log(m, logbox), only=modules)
    except Exception as e:
        log(f"同步失败：{e}", logbox)
        return "offline", None
    if status == "uptodate":
        log(f"已是最新汉化包 v{man.get('version')}，无需更新。", logbox)
        return "uptodate", None
    log(f"已获取汉化包 v{man.get('version')}（本次更新 {n} 个文件）", logbox)
    return "ready", dest

def _local_pack_dir(roots):
    """任一数据目录里现有的 zh 包（用于"线上已最新但汉化区域变了"时重装）。"""
    for r in roots:
        d = os.path.join(r, "Locale", "zh")
        if os.path.isdir(d):
            return d
    return None

def _snapshot(src):
    """把目录快照一份到临时区。

    必须做：安装时会把「旧的 zh 目录」改名成 zh.bak_* 作为备份。
    如果源目录恰好就是那个旧 zh（"线上已最新、只是换了汉化区域"的情形），
    备份动作会先把源搬走，接着复制就会失败。
    """
    dest = os.path.join(scratch_dir(), "_zh_local_snap")
    try:
        if os.path.isdir(dest):
            shutil.rmtree(dest, ignore_errors=True)
        shutil.copytree(src, dest)
        return dest
    except Exception as e:
        log(f"本地包快照失败（{e}），改为直接使用原目录", None)
        return src

def do_install(update=False, logbox=None, modules=None):
    modules = resolve_modules(modules)
    install = find_install_dir()
    roots = find_all_data_roots(install)
    bundled = os.path.join(resource_dir(), "zh")
    if not os.path.isdir(bundled):
        log("错误：未找到随附的 zh 汉化包目录", logbox); return False
    log(f"安装目录: {install or '(未自动探测)'}", logbox)
    log(f"检测到 {len(roots)} 个数据目录: {', '.join(roots) or '(无)'}", logbox)
    log(f"汉化区域: {module_summary(modules)}", logbox)
    warn_module_combination(modules, logbox)
    if not roots:
        log("错误：没有可写入的数据目录", logbox); return False

    src = bundled
    if update:
        status, synced = sync_from_github(roots, logbox, modules)
        if status == "uptodate":
            if selection_changed(roots, modules):
                local = _local_pack_dir(roots)
                if local:
                    log("线上内容已是最新，但汉化区域有变化，按新选择重装一次。", logbox)
                    src = _snapshot(local)
                else:
                    log("完成：本地汉化已是最新。", logbox)
                    return True
            else:
                log("完成：本地汉化已是最新，未做任何改动。", logbox)
                return True
        elif status == "ready":
            src = synced
        else:
            log("回退：改用随附汉化包安装（联网后重试可获取最新汉化）。", logbox)

    ok = _install_pack(src, roots, install, logbox, modules)
    if ok:
        log("完成！请重启 Pixel Composer 查看中文界面。", logbox)
    else:
        log("部分目录写入失败，请检查磁盘权限后重试。", logbox)
    return ok

def do_restore(logbox=None):
    """恢复英文：切回 en，并把入门指南的原版文件还原回去。"""
    install = find_install_dir()
    for root in find_all_data_roots(install):
        set_language("en", root, logbox)
        restore_welcome(root, logbox)
    log("已恢复英文，重启软件生效。", logbox)

# ------------------- 工作区标签（布局文件名）--------------------
# 工作区标签显示的是 layouts/*.json 的文件名，本身不走语言包。
# 若「按原名查表」不生效，就用这里把自带布局改名成中文（可一键还原）。
# __default.json 被程序按名引用，绝不改动。
LAYOUT_CN = {
    "Horizontal.json": "水平.json",
    "Vertical.json": "垂直.json",
    "Preview.json": "预览.json",
    "Drawing.json": "绘画.json",
    "Side menu.json": "侧边菜单.json",
}

def find_layout_dirs(install=None):
    out = []
    for root in find_all_data_roots(install):
        d = os.path.join(root, "layouts")
        if os.path.isdir(d):
            rp = os.path.realpath(d)
            if rp not in [os.path.realpath(x) for x in out]:
                out.append(d)
    return out

def _retarget_layout_pref(runtime, mapping, logbox=None):
    """把 Preferences/*/keys.json 里记录的当前布局名同步改名，避免加载失败。"""
    kp = find_keys_json(runtime)
    if not os.path.isfile(kp):
        return
    try:
        d = json.load(open(kp, encoding="utf-8"))
    except Exception:
        return
    cur = d.get("panel_layout_file")
    if isinstance(cur, str) and cur in mapping:
        d["panel_layout_file"] = mapping[cur]
        try:
            json.dump(d, open(kp, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
            log(f"当前布局引用已同步为「{mapping[cur]}」", logbox)
        except Exception:
            pass

def patch_layout_zip(pairs, logbox=None):
    """改写 pack/layouts.zip 里的条目名（pairs: [(旧名, 新名)]），返回改动条数。

    为什么必须改 zip：只要 layouts/ 里缺了任一个自带布局，游戏启动时会从
    pack/layouts.zip 把整套自带布局重新解出来 —— 光改文件名会被还原成英文
    （实测：改完名后启动一次，Horizontal.json 等 5 个英文文件全部回来，
    变成中英文各一套的重复项）。把 zip 里的条目名也改掉，游戏自己解出来的
    就是中文名，才是稳定的做法。
    首次调用会把原 zip 备份成 layouts.zip.bak_cn，便于还原。
    """
    install = find_install_dir()
    zp = os.path.join(install, "pack", "layouts.zip") if install else ""
    if not zp or not os.path.isfile(zp):
        log("未找到 pack/layouts.zip，跳过内置布局改写。", logbox)
        return 0
    bak = zp + ".bak_cn"
    if not os.path.isfile(bak):
        try:
            shutil.copy2(zp, bak)
            log("已备份 pack/layouts.zip -> layouts.zip.bak_cn", logbox)
        except Exception as e:
            log(f"备份 layouts.zip 失败: {e}", logbox)
    try:
        with zipfile.ZipFile(zp) as zin:
            items = [(i, zin.read(i.filename)) for i in zin.infolist()]
    except Exception as e:
        log(f"读取 layouts.zip 失败: {e}", logbox)
        return 0
    m = dict(pairs)
    changed = 0
    tmp = zp + ".tmp"
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zo:
            for info, data in items:
                name = m.get(info.filename, info.filename)
                if name != info.filename:
                    changed += 1
                ni = zipfile.ZipInfo(name, date_time=info.date_time)
                ni.compress_type = info.compress_type
                ni.external_attr = info.external_attr
                zo.writestr(ni, data)
        if changed:
            os.replace(tmp, zp)
            log(f"pack/layouts.zip 内置布局改名 {changed} 项", logbox)
        else:
            os.remove(tmp)
            log("pack/layouts.zip 无需改动（可能已处理过）。", logbox)
    except Exception as e:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass
        log(f"改写 layouts.zip 失败（游戏可能在运行中）: {e}", logbox)
        return 0
    return changed

def do_layouts(restore=False, logbox=None):
    """汉化 / 还原工作区标签（同时改写 layouts/*.json 文件名与 pack/layouts.zip 条目名）。"""
    install = find_install_dir()
    dirs = find_layout_dirs(install)
    if not dirs:
        log("未找到 layouts 目录，跳过。", logbox)
        return
    pairs = [(a, b) for a, b in LAYOUT_CN.items()]
    if restore:
        pairs = [(b, a) for a, b in pairs]
    # 1) 先改 pack/layouts.zip，避免游戏下次启动把英文名解回来
    patch_layout_zip(pairs, logbox)
    # 2) 再改已解出来的布局文件
    mapping, done = {}, 0
    for d in dirs:
        for src_name, dst_name in pairs:
            src, dst = os.path.join(d, src_name), os.path.join(d, dst_name)
            if not os.path.isfile(src):
                continue
            if os.path.exists(dst):
                log(f"目标已存在，跳过: {dst_name}", logbox)
                continue
            try:
                shutil.move(src, dst)
            except Exception as e:
                log(f"改名失败 {src_name}: {e}", logbox)
                continue
            mapping[src_name[:-5]] = dst_name[:-5]
            done += 1
            log(f"{'还原' if restore else '汉化'}布局 {src_name} -> {dst_name}", logbox)
        # layouts/version 不动：保持不变才不会触发游戏重新解压覆盖
    if not done:
        log("没有需要改名的布局文件（可能已处理过）。", logbox)
    else:
        for root in find_all_data_roots(install):
            _retarget_layout_pref(root, mapping, logbox)
        log("完成：重启 Pixel Composer 后查看工作区标签。", logbox)

def do_rollback(logbox=None):
    """还原到最近一次安装前的汉化包（从各数据目录的 zh.bak_* 取最新一份）"""
    roots = find_all_data_roots(find_install_dir())
    done = 0
    for runtime in roots:
        loc = os.path.join(runtime, "Locale")
        if not os.path.isdir(loc): continue
        baks = sorted(
            d for d in os.listdir(loc)
            if d.startswith("zh.bak_") and os.path.isdir(os.path.join(loc, d))
        )
        if not baks:
            log(f"无备份: {loc}", logbox); continue
        bak = os.path.join(loc, baks[-1])
        zh = os.path.join(loc, "zh")
        # 若备份内存在嵌套的 zh/（旧版工具遗留），先展平到顶层
        nested = os.path.join(bak, "zh")
        if os.path.isdir(nested) and not os.path.isfile(os.path.join(bak, "words.json")):
            for nm in os.listdir(nested):
                shutil.move(os.path.join(nested, nm), os.path.join(bak, nm))
            os.rmdir(nested)
        # 先把当前 zh 暂存，避免直接覆盖丢失
        if os.path.exists(zh) or os.path.islink(zh):
            ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            shutil.move(zh, f"{zh}.pre_rollback_{ts}")
        shutil.move(bak, zh)
        set_language("zh", runtime, logbox)
        log(f"已还原汉化包：{os.path.basename(bak)} @ {runtime}", logbox)
        done += 1
    if not done:
        log("没有可用的汉化备份（zh.bak_*）", logbox)

def do_status(logbox=None):
    plat = "Windows" if IS_WIN else ("macOS" if IS_MAC else ("Linux" if IS_LINUX else sys.platform))
    install = find_install_dir()
    roots = find_all_data_roots(install)
    log(f"运行平台 : {plat}（Python {sys.version.split()[0]}）", logbox)
    log(f"安装目录 : {install or '(未探测到，可用 --install-dir 指定)'}", logbox)
    if not roots:
        log("未检测到任何数据目录", logbox); return
    z = _zhsync()
    pv = None
    for i, root in enumerate(roots, 1):
        zh = os.path.join(root, "Locale", "zh")
        kp = find_keys_json(root)
        cur = "未知"
        if os.path.exists(kp):
            try: cur = json.load(open(kp, encoding="utf-8")).get("local", "未知")
            except Exception: pass
        ver = z.installed_version(root) if z and hasattr(z, "installed_version") else None
        sel = z.installed_modules(root) if z and hasattr(z, "installed_modules") else None
        if ver and pv is None:
            pv = ver
        tag = f"v{ver}" if ver else "版本未知（旧版工具/社区包）"
        log(f"[{i}] 数据目录 : {root}", logbox)
        log(f"    zh 汉化包 : {'已安装' if os.path.isdir(zh) else '未安装'}（{tag}） | 当前语言 : {cur}", logbox)
        if sel is not None:
            log(f"    汉化区域 : {module_summary(sel)}", logbox)
        wb = os.path.join(root, WELCOME_DIRNAME + ".bak_cn")
        wd = os.path.join(root, WELCOME_DIRNAME)
        if os.path.isdir(wb) and os.listdir(wb):
            log(f"    入门指南 : 已汉化（原文件备份于 {os.path.basename(wb)}/，可用「③ 恢复英文」还原）", logbox)
        elif os.path.isdir(wd):
            log("    入门指南 : 官方原版（未汉化）", logbox)
    if pv:
        try:
            _v, summary = z.installed_summary(roots)
            if "不一致" in summary:
                log(f"注意：{summary}（点「② 同步最新汉化」可统一到最新）", logbox)
        except Exception:
            pass

# ------------- 旧社区汉化包残留（只读清点；本功能绝不移动/删除任何文件）-------------
# 背景：2025 年前后流传过一份"小羊 / 安尘"等做的社区汉化包（zh/ + Welcome files/
# + 一个汉化 EXE）。它的安装方式是把 zh/ 与 Welcome files/ 直接扔进游戏根目录，
# 并把教程整包替换成中文名文件夹（A开始入门 / B示例项目 / C模板）。
# 本工具从不用这些位置（只写 <数据目录>/Locale/zh 与 <数据目录>/Welcome files），
# 所以这些路径一旦存在，就一定是那个旧包留下的，可安全认定为"残留"。
# 按用户要求：这里只**列出**，不删除、不移动。想清理请自行核对后手动处理。
OLD_PACK_DIRNAMES = ("A开始入门", "B示例项目", "C模板")
OLD_PACK_FILE_HINTS = ("一键汉化", "汉化包", "汉化软件", "汉化工具", "汉化说明",
                       "汉化教程", "注意事项", "使用教程", "汉化组")


def _path_size(path):
    """返回 (文件数, 字节数)。只读。"""
    if os.path.isfile(path):
        try:
            return 1, os.path.getsize(path)
        except Exception:
            return 1, 0
    n = s = 0
    for dp, _dns, fns in os.walk(path):
        for f in fns:
            try:
                s += os.path.getsize(os.path.join(dp, f)); n += 1
            except Exception:
                pass
    return n, s


def _has_non_ascii(name):
    """目录名含非 ASCII 字符（旧包的中文名文件夹特征）。"""
    try:
        name.encode("ascii")
        return False
    except UnicodeEncodeError:
        return True


def scan_leftovers(install=None, roots=None, sample=3):
    """只读扫描旧社区汉化包残留，返回条目列表。

    识别依据全部是"本工具绝不会写"的位置或命名，因此不会把自己装的东西
    误报成残留：
      · 安装根目录下的 zh/            （本工具只写 <数据目录>/Locale/zh）
      · 安装根目录下的 Welcome files/  （本工具只写 <数据目录>/Welcome files）
      · 任意 Welcome files/ 里非 ASCII 目录名（旧包的中文教程文件夹）
      · 文件名含"汉化 / 注意事项 / 使用教程"等字样的文件与 EXE
    """
    items = []

    def add(path, kind, note=""):
        if not os.path.exists(path):
            return
        n, s = _path_size(path)
        items.append({"path": path, "kind": kind, "files": n, "size": s, "note": note})

    def scan_welcome_tree(base, kind):
        """扫一个 Welcome files 目录：里面非 ASCII 名的子目录就是旧包替换的教程。"""
        if not os.path.isdir(base):
            return
        try:
            entries = sorted(os.listdir(base))
        except Exception:
            return
        for e in entries:
            if not _has_non_ascii(e):
                continue          # Getting started / Sample Projects 等官方英文名一律跳过
            sub = os.path.join(base, e)
            if os.path.isdir(sub):
                add(sub, kind, "旧包换入的中文名教程文件夹")
            elif os.path.isfile(sub):
                add(sub, kind, "旧包留下的中文名文件")

    if install and os.path.isdir(install):
        add(os.path.join(install, "zh"), "旧包汉化目录",
            "本工具只写 <数据目录>/Locale/zh，安装根目录下的 zh/ 属旧包")
        scan_welcome_tree(os.path.join(install, "Welcome files"), "旧包教程目录")
        try:
            top = sorted(os.listdir(install))
        except Exception:
            top = []
        for e in top:
            p = os.path.join(install, e)
            if not os.path.isfile(p) or not e.lower().endswith((".exe", ".txt", ".md")):
                continue
            if e.lower().endswith(".exe") and "汉化" in e:
                add(p, "旧包汉化程序", "非官方汉化 EXE，本工具不依赖它")
            elif any(h in e for h in OLD_PACK_FILE_HINTS):
                add(p, "旧包说明文件", "旧包自带的使用说明")

    for root in (roots or []):
        scan_welcome_tree(os.path.join(root, WELCOME_DIRNAME), "旧包教程目录")
        loc = os.path.join(root, "Locale")
        if not os.path.isdir(loc):
            continue
        try:
            for e in sorted(os.listdir(loc)):
                p = os.path.join(loc, e)
                if os.path.isfile(p) and any(h in e for h in OLD_PACK_FILE_HINTS):
                    add(p, "旧包说明文件", "旧包塞进 Locale 的说明文件")
        except Exception:
            pass

    # 去重（同一路径可能被 install 与 roots 两条线各扫到一次）
    seen, out = set(), []
    for it in items:
        rp = os.path.realpath(it["path"])
        if rp in seen:
            continue
        seen.add(rp)
        out.append(it)

    # 采集每个条目的前几个文件名，便于用户核对是不是自己需要的东西
    for it in out:
        names = []
        if os.path.isdir(it["path"]):
            try:
                names = sorted(os.listdir(it["path"]))[:sample]
            except Exception:
                names = []
        it["sample"] = names
    out.sort(key=lambda d: d["size"], reverse=True)
    return out


def scan_own_backups(roots=None):
    """本工具自己产生的备份（Locale/zh.bak_*、Welcome files.bak_cn），也只列出。"""
    items = []
    for root in (roots or []):
        loc = os.path.join(root, "Locale")
        if os.path.isdir(loc):
            try:
                for e in sorted(os.listdir(loc)):
                    if (e.startswith("zh.bak_") or e.startswith("zh.pre_rollback_")) \
                            and os.path.isdir(os.path.join(loc, e)):
                        p = os.path.join(loc, e)
                        n, s = _path_size(p)
                        items.append({"path": p, "kind": "汉化包备份",
                                      "files": n, "size": s, "sample": [],
                                      "note": "「④ 还原上一版汉化」只取最新一份"})
            except Exception:
                pass
        wb = os.path.join(root, WELCOME_DIRNAME + ".bak_cn")
        if os.path.isdir(wb) and os.listdir(wb):
            n, s = _path_size(wb)
            items.append({"path": wb, "kind": "入门指南原文件备份", "files": n,
                          "size": s, "sample": [], "note": "「③ 恢复英文」会用到的备份，请勿删"})
    return items


def _fmt_size(n):
    for unit, div in (("GB", 1 << 30), ("MB", 1 << 20), ("KB", 1 << 10)):
        if n >= div:
            return f"{n / div:.2f} {unit}"
    return f"{n} B"


def do_leftovers(logbox=None):
    """列出旧社区汉化包残留（只读）。不删除、不移动任何文件。"""
    install = find_install_dir()
    roots = find_all_data_roots(install)
    log("旧汉化包残留清点（只读，不会删除或移动任何文件）", logbox)
    log(f"安装目录 : {install or '(未探测到，可用 --install-dir 指定)'}", logbox)
    items = scan_leftovers(install, roots)
    if not items:
        log("未发现旧社区汉化包残留。", logbox)
    else:
        total = sum(i["size"] for i in items)
        log(f"发现 {len(items)} 项，合计约 {_fmt_size(total)}：", logbox)
        for i, it in enumerate(items, 1):
            log(f"  {i:>2}. [{it['kind']}] {_fmt_size(it['size'])} / {it['files']} 文件", logbox)
            log(f"      {it['path']}", logbox)
            if it["note"]:
                log(f"      说明：{it['note']}", logbox)
            if it["sample"]:
                more = " …" if it["files"] > len(it["sample"]) else ""
                log(f"      内含：{'、'.join(it['sample'])}{more}", logbox)
        log("以上仅为清单。确认不需要后请自行手动删除；本工具不会碰它们。", logbox)
    own = scan_own_backups(roots)
    if own:
        total = sum(i["size"] for i in own)
        log(f"另：本工具生成的备份 {len(own)} 项，约 {_fmt_size(total)}（「④ 还原上一版」只用每个目录里最新的一份，更早的可自行清理）：", logbox)
        for it in own:
            log(f"      {it['path']}  ({_fmt_size(it['size'])} / {it['files']} 文件)", logbox)

# ==================== 界面（配色 = Pixel Composer 官方 default 主题）====================
PC_BG      = "#1c1c23"   # main_bg
PC_DEEP    = "#191925"   # main_dkblack
PC_PANEL   = "#23232f"   # 卡片
PC_DKGREY  = "#3b3b4e"   # main_dkgrey
PC_DARK    = "#505066"   # main_dark
PC_GREY    = "#6d6d81"   # main_grey
PC_MDWHITE = "#9f9fb5"   # main_mdwhite
PC_WHITE   = "#d6d6e8"   # main_white
ORANGE     = "#ff9166"   # 主强调色
ORANGE_HOV = "#ffab8c"
CYAN       = "#88ffe9"
INK        = "#272736"   # main_black（橙底上的深色文字）

def _rounded_points(x1, y1, x2, y2, r):
    return [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]

class PCButton:
    """基于 Canvas 的圆角按钮（8px 圆角，配色随 Pixel Composer 主题）。"""
    def __init__(self, master, text, command, width=230, height=44, primary=False, font=None):
        import tkinter as tk
        self.tk = tk
        self.command = command
        self.w, self.h = width, height
        self.primary = primary
        self.text = text
        self.font = font
        self.normal = ORANGE if primary else PC_DKGREY
        self.hover = ORANGE_HOV if primary else PC_DARK
        self.fg = INK if primary else PC_WHITE
        self.cv = tk.Canvas(master, width=width, height=height, bg=PC_BG,
                            highlightthickness=0, bd=0, cursor="hand2")
        self._draw(self.normal)
        self.cv.bind("<Enter>", lambda e: self._draw(self.hover))
        self.cv.bind("<Leave>", lambda e: self._draw(self.normal))
        self.cv.bind("<Button-1>", lambda e: self._press())
        self.cv.bind("<ButtonRelease-1>", lambda e: self._release())
    def _draw(self, fill):
        cv = self.cv
        cv.delete("all")
        cv.create_polygon(_rounded_points(0.5, 0.5, self.w - 0.5, self.h - 0.5, 9),
                          fill=fill, smooth=True, splinesteps=24)
        cv.create_text(self.w / 2, self.h / 2, text=self.text, fill=self.fg, font=self.font)
    def _press(self):
        self._draw(self.hover)
    def _release(self):
        self._draw(self.normal)
        try: self.command()
        except Exception as e:
            print("命令执行异常:", e)
    def pack(self, **kw):
        self.cv.pack(**kw)
    def grid(self, **kw):
        self.cv.grid(**kw)

VERSION = "1.2.1"

def _ui_font(size, bold=False, mono=False):
    """按平台挑一个存在的字体。

    Windows 上写死 "Microsoft YaHei" / "Consolas" 在 Linux 上会整片变成方框，
    所以这里先探测系统字体，实在找不到就退回 Tk 的默认/等宽具名字体再改尺寸。
    """
    import tkinter.font as tkfont
    try:
        fams = set(tkfont.families())
    except Exception:
        fams = set()
    if mono:
        cands = ["Consolas", "JetBrains Mono", "Noto Sans Mono CJK SC",
                 "Noto Sans Mono", "Source Han Mono SC", "DejaVu Sans Mono",
                 "Liberation Mono", "Menlo", "Monaco", "Courier New"]
        base_name = "TkFixedFont"
    else:
        cands = ["Microsoft YaHei", "微软雅黑", "Noto Sans CJK SC", "Noto Sans SC",
                 "Source Han Sans SC", "WenQuanYi Micro Hei", "WenQuanYi Zen Hei",
                 "PingFang SC", "Hiragino Sans GB", "DejaVu Sans", "Liberation Sans",
                 "Helvetica Neue", "Helvetica"]
        base_name = "TkDefaultFont"
    fam = next((c for c in cands if c in fams), None)
    if fam:
        return tkfont.Font(family=fam, size=size, weight="bold" if bold else "normal")
    f = tkfont.nametofont(base_name).copy()
    f.configure(size=size, weight="bold" if bold else "normal")
    return f

def gui():
    import tkinter as tk
    from tkinter import scrolledtext

    root = tk.Tk()
    root.title(f"Pixel Composer 汉化工具 v{VERSION}  ·  按区域汉化 / 在线同步")
    root.configure(bg=PC_BG)
    root.geometry("620x944")
    root.minsize(560, 820)
    try:
        if is_frozen():
            root.iconbitmap(os.path.join(resource_dir(), "app_icon.ico"))
    except Exception:
        pass

    F_TITLE = _ui_font(19, bold=True)
    F_SUB   = _ui_font(9)
    F_CHK   = _ui_font(10)
    F_BTN   = _ui_font(11, bold=True)
    F_MONO  = _ui_font(9, mono=True)

    # 顶栏
    header = tk.Frame(root, bg=PC_BG)
    header.pack(fill="x", padx=22, pady=(16, 6))
    tk.Label(header, text=f"Pixel Composer 汉化工具  v{VERSION}", font=F_TITLE,
             bg=PC_BG, fg=PC_WHITE).pack(anchor="w")
    tk.Label(header, text="一键安装 · 联网同步最新汉化 · 按区域汉化 · 可一键回滚",
             font=F_SUB, bg=PC_BG, fg=PC_MDWHITE).pack(anchor="w", pady=(3, 0))
    tk.Frame(root, bg=PC_DKGREY, height=1).pack(fill="x", padx=22, pady=(10, 0))

    # 汉化区域
    modpanel = tk.Frame(root, bg=PC_PANEL)
    modpanel.pack(fill="x", padx=22, pady=(10, 0))
    top = tk.Frame(modpanel, bg=PC_PANEL)
    top.pack(fill="x", padx=12, pady=(8, 0))
    tk.Label(top, text="汉化区域（取消勾选 = 该区域保留英文）", font=F_SUB,
             bg=PC_PANEL, fg=PC_MDWHITE).pack(side="left")
    grid = tk.Frame(modpanel, bg=PC_PANEL)
    grid.pack(fill="x", padx=10, pady=(2, 8))
    modvars = {}
    for i, (mid, label, _p) in enumerate(module_table()):
        v = tk.BooleanVar(value=True)
        modvars[mid] = v
        tk.Checkbutton(grid, text=label, variable=v, font=F_CHK,
                       bg=PC_PANEL, fg=PC_WHITE, activebackground=PC_PANEL,
                       activeforeground=ORANGE, selectcolor=PC_DEEP,
                       highlightthickness=0, bd=0, anchor="w",
                       cursor="hand2").grid(row=i // 2, column=i % 2,
                                            sticky="w", padx=8, pady=2)

    def chosen():
        return [m for m in module_ids() if modvars[m].get()]

    def set_all(flag):
        for m in modvars:
            modvars[m].set(flag)

    btns = tk.Frame(top, bg=PC_PANEL)
    btns.pack(side="right")
    for text, flag in (("全选", True), ("全不选", False)):
        lb = tk.Label(btns, text=text, font=F_SUB, bg=PC_PANEL, fg=CYAN, cursor="hand2")
        lb.pack(side="left", padx=(10, 0))
        lb.bind("<Button-1>", lambda e, f=flag: set_all(f))
    tk.Frame(root, bg=PC_BG, height=10).pack()

    # 主按钮
    body = tk.Frame(root, bg=PC_BG)
    body.pack(fill="x", padx=22, pady=(4, 12))
    PCButton(body, "①  一键汉化（安装 / 启用）",
             lambda: do_install(False, box, chosen()),
             width=576, height=52, primary=True, font=F_BTN).pack()

    # 次按钮
    row1 = tk.Frame(root, bg=PC_BG); row1.pack(padx=22, pady=(0, 8))
    PCButton(row1, "②  同步最新汉化（联网）",
             lambda: do_install(True, box, chosen()),
             width=282, height=42, font=F_BTN).pack(side="left")
    tk.Frame(row1, bg=PC_BG, width=12).pack(side="left")
    PCButton(row1, "③  恢复英文（含示例还原）", lambda: do_restore(box),
             width=282, height=42, font=F_BTN).pack(side="left")
    row2 = tk.Frame(root, bg=PC_BG); row2.pack(padx=22, pady=(0, 8))
    PCButton(row2, "④  还原上一版汉化", lambda: do_rollback(box),
             width=282, height=42, font=F_BTN).pack(side="left")
    tk.Frame(row2, bg=PC_BG, width=12).pack(side="left")
    PCButton(row2, "⑤  查看状态", lambda: do_status(box),
             width=282, height=42, font=F_BTN).pack(side="left")
    row3 = tk.Frame(root, bg=PC_BG); row3.pack(padx=22, pady=(0, 8))
    PCButton(row3, "⑥  汉化工作区标签", lambda: do_layouts(False, box),
             width=282, height=42, font=F_BTN).pack(side="left")
    tk.Frame(row3, bg=PC_BG, width=12).pack(side="left")
    PCButton(row3, "⑦  还原布局名", lambda: do_layouts(True, box),
             width=282, height=42, font=F_BTN).pack(side="left")
    row4 = tk.Frame(root, bg=PC_BG); row4.pack(padx=22, pady=(0, 8))
    PCButton(row4, "⑧  旧汉化包残留清点（只列出，不删除）", lambda: do_leftovers(box),
             width=576, height=42, font=F_BTN).pack()
    tk.Label(root, text="① 按上面勾选的「汉化区域」安装；② 从 GitHub 下载维护者已同步好的成品包"
                      "（断网自动回退随附包）；\n"
                      "③ 同时把入门指南示例还原成英文原版；⑥ 连 pack/layouts.zip 一起改名"
                      "（只改文件名会被游戏解回英文）；\n"
                      "⑧ 只生成旧社区汉化包的残留清单（路径 / 大小 / 文件数），不会移动或删除任何文件。",
             font=F_SUB, bg=PC_BG, fg=PC_GREY, wraplength=572,
             justify="left").pack(padx=22, pady=(0, 8), anchor="w")

    # 日志区
    logwrap = tk.Frame(root, bg=PC_DKGREY, bd=0)
    logwrap.pack(fill="both", expand=True, padx=22, pady=(4, 10))
    box = scrolledtext.ScrolledText(logwrap, height=10, font=F_MONO, wrap="word",
                                    bg=PC_DEEP, fg=PC_WHITE, insertbackground=ORANGE,
                                    selectbackground=PC_DARK, selectforeground=PC_WHITE,
                                    relief="flat", bd=0, padx=12, pady=10)
    box.pack(fill="both", expand=True, padx=1, pady=1)

    # 底栏
    foot = tk.Frame(root, bg=PC_BG); foot.pack(fill="x", padx=22, pady=(0, 12))
    tk.Label(foot, text="GitHub  DC1024/pixel-composer-cn", font=F_SUB,
             bg=PC_BG, fg=CYAN).pack(side="left")
    tk.Label(foot, text="MIT License", font=F_SUB,
             bg=PC_BG, fg=PC_GREY).pack(side="right")

    do_status(box)
    root.mainloop()

# ------------------------- 命令行 -------------------------
MODES = ("install", "update", "sync", "restore", "rollback", "status",
         "layouts", "layouts-restore", "no-gui", "cli", "modules", "leftovers")

def parse_args(argv):
    """极简参数解析：支持 --flag 与 --key value / --key=value。

    不引 argparse 是为了让 EXE 的入口逻辑保持最薄，也方便 --key=value 与
    --key value 两种写法在 install.sh 里都能用。
    """
    opts, rest, i = {}, [], 0
    while i < len(argv):
        a = argv[i]
        if a == "--modules" and i + 1 < len(argv):
            opts["modules"] = argv[i + 1]; i += 2; continue
        if a.startswith("--modules="):
            opts["modules"] = a.split("=", 1)[1]; i += 1; continue
        if a == "--install-dir" and i + 1 < len(argv):
            opts["install_dir"] = argv[i + 1]; i += 2; continue
        if a.startswith("--install-dir="):
            opts["install_dir"] = a.split("=", 1)[1]; i += 1; continue
        rest.append(a); i += 1
    return opts, rest

def main():
    _bootstrap_paths()
    _setup_stdio()
    opts, rest = parse_args(sys.argv[1:])
    if opts.get("install_dir"):
        os.environ["PIXELCOMPOSER_DIR"] = opts["install_dir"]

    mode = None
    for a in rest:
        m = a.lstrip("-")
        if m in MODES:
            mode = m
    if "--version" in rest or "-V" in rest:
        print(f"Pixel Composer 汉化工具 v{VERSION}（{sys.platform} / Python {sys.version.split()[0]}）")
        return
    if "--list-modules" in rest or mode in ("modules", "list-modules"):
        print("可选汉化区域（CLI 用 --modules 传逗号分隔的 id）：")
        for mid, label, _p in module_table():
            print(f"  {mid:<10} {label}")
        print(f"  默认：全部（{','.join(module_ids())}）")
        return

    try:
        mods = resolve_modules(opts.get("modules"))
    except Exception as e:
        print(f"[错误] {e}")
        sys.exit(2)

    if mode and mode != "cli":
        if mode in ("install", "no-gui"): do_install(False, None, mods)
        elif mode in ("update", "sync"): do_install(True, None, mods)
        elif mode == "restore": do_restore()
        elif mode == "rollback": do_rollback()
        elif mode == "status": do_status()
        elif mode == "layouts": do_layouts(False)
        elif mode == "layouts-restore": do_layouts(True)
        elif mode == "leftovers": do_leftovers()
        return
    # 尝试 GUI，否则 CLI
    if "--cli" in rest or mode == "cli":
        cli_loop(mods)
        return
    try:
        import tkinter  # noqa: F401
    except Exception:
        print("未检测到图形界面（tkinter），改用命令行模式。")
        cli_loop(mods)
        return
    gui()

def cli_loop(modules=None):
    _bootstrap_paths()
    _setup_stdio()
    modules = resolve_modules(modules)
    print(f"Pixel Composer 一键汉化工具 v{VERSION}（CLI）")
    print(f"当前汉化区域: {module_summary(modules)}")
    while True:
        print("\n1) 一键汉化  2) 同步最新汉化(联网)  3) 恢复英文  4) 还原上一版汉化  5) 查看状态")
        print("6) 汉化工作区标签  7) 还原布局名  8) 选择汉化区域  9) 旧汉化包残留清点  0) 退出")
        try:
            c = input("选择> ").strip()
        except EOFError:
            break
        if c == "1": do_install(False, None, modules)
        elif c == "2": do_install(True, None, modules)
        elif c == "3": do_restore()
        elif c == "4": do_rollback()
        elif c == "5": do_status()
        elif c == "6": do_layouts(False)
        elif c == "7": do_layouts(True)
        elif c == "8":
            print("可选：" + "、".join(f"{m}({l})" for m, l, _p in module_table()))
            try:
                spec = input("输入要汉化的区域（逗号分隔，直接回车=全部，none=全不选）> ").strip()
            except EOFError:
                break
            try:
                modules = resolve_modules(spec or None)
                print(f"已设置: {module_summary(modules)}")
            except Exception as e:
                print(f"[错误] {e}")
        elif c == "9": do_leftovers()
        elif c == "0": break
        else: print("无效输入")

if __name__ == "__main__":
    main()
