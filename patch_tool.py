# -*- coding: utf-8 -*-
"""
Pixel Composer 一键汉化工具（离线版 / 标准库 only）
作者：DC1024  <https://github.com/DC1024/pixel-composer-cn>
功能：
  1) 安装汉化   : 把自带 zh 汉化包复制到 PixelComposer 运行时 Locale 目录，并启用中文
  2) 同步最新汉化: 从 GitHub 拉取「维护者定期同步上游、已经翻好」的最新汉化包并安装
                  （只下载成品，本地不再跑翻译引擎）；断网/仓库不可达时自动回退随附包
  3) 恢复英文   : 切回 en
  4) 还原上一版 : 回滚到最近一次安装前的汉化包（zh.bak_*）
  5) 查看状态   : 显示当前语言与目录
  6) 汉化工作区标签 : 自带布局改名成中文；同时改写 pack/layouts.zip 的条目名
                      （只改文件名会被游戏重新解出英文名还原，故必须连 zip 一起改）
  7) 还原布局名 : 把上面两条改动还原成英文
依赖：仅 Python 标准库（tkinter 做界面，缺失时自动退回命令行）
配色：与 Pixel Composer 官方 default 主题一致（Themes/default/values.json）
"""
import os, sys, json, shutil, zipfile, tempfile, datetime

# ------------------------- 路径探测 -------------------------
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

def find_install_dir():
    """定位游戏安装目录（含 PixelComposer.exe / pack/locale.zip）"""
    # 1) 注册表
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, STEAM_REG_KEY, 0, winreg.KEY_READ)
        val, _ = winreg.QueryValueEx(k, "InstallLocation")
        winreg.CloseKey(k)
        p = os.path.normpath(val.strip('"'))
        if os.path.isdir(p): return p
    except Exception:
        pass
    # 2) 常见路径
    for p in COMMON_STEAM:
        if os.path.isdir(p): return p
    # 3) 未探测到
    return None

def find_all_data_roots(install=None):
    """返回所有可能的数据目录（含 Locale 与 preferences），按真实路径去重。
    覆盖：LocalAppData 默认、游戏安装子目录，以及各 persistPreference.json 的 path 指向处。
    这样无论游戏从哪个目录读取，汉化包与语言设置都能生效。"""
    roots = []
    def add(p):
        if not p: return
        try: rp = os.path.realpath(p)
        except Exception: rp = os.path.abspath(p)
        if rp not in [os.path.realpath(x) for x in roots]:
            roots.append(p)
    # 1) LocalAppData 默认
    add(os.path.join(os.path.expanduser("~"), "AppData", "Local", "PixelComposer"))
    # 2) 游戏安装子目录（PixelComposer.exe 所在的上层）
    if install:
        add(os.path.join(install, "PixelComposer"))
    # 3) 各 persistPreference.json 的 path 字段
    bases = [os.path.join(os.path.expanduser("~"), "AppData", "Local", "PixelComposer")]
    if install:
        bases.append(os.path.join(install, "PixelComposer"))
    for base in bases:
        if not os.path.isdir(base): continue
        pp = os.path.join(base, "persistPreference.json")
        if os.path.isfile(pp):
            try:
                d = json.load(open(pp, encoding="utf-8"))
                p = d.get("path", "").strip().replace("\\/", "/").replace("/", os.sep)
                if p: add(p)
            except Exception:
                pass
    return roots

def find_runtime_dir():
    """兼容旧调用：返回第一个数据目录（通常是游戏实际读取处）。"""
    roots = find_all_data_roots(find_install_dir())
    return roots[0] if roots else os.path.join(os.path.expanduser("~"), "AppData", "Local", "PixelComposer")

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
    """确保目标 Locale/en 存在（游戏以此判断 Locale 目录有效）"""
    en_dst = os.path.join(runtime, "Locale", "en")
    if os.path.isdir(en_dst):
        return
    src = None
    if install:
        cand = os.path.join(install, "PixelComposer", "Locale", "en")
        if os.path.isdir(cand): src = cand
        cand2 = os.path.join(install, "Locale", "en")
        if not src and os.path.isdir(cand2): src = cand2
    if src:
        shutil.copytree(src, en_dst, dirs_exist_ok=True)
        log("已补齐默认 en 语言包", logbox)
    else:
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
def _install_pack(src, roots, install, logbox=None):
    """把 src 汉化包装进所有数据目录，并启用中文。返回是否全部成功。"""
    for root in roots:
        t = os.path.join(root, "Locale", "zh")
        if not backup_and_copy(src, t, logbox):
            return False
        apply_extras(root, logbox)
        ensure_en(root, install, logbox)
        set_language("zh", root, logbox)
    return True

def sync_from_github(roots, logbox=None):
    """从 GitHub 同步「已经翻好」的汉化包（本地不再跑翻译引擎）。

    汉化流程改为：维护者定期同步上游官方语言包 → 补翻 → 推送 GitHub；
    用户侧只负责把成品包拉下来。返回 (status, src)：

      "uptodate" —— 各数据目录都与线上一致，无需安装
      "ready"    —— src = 已同步好的完整包目录，可直接安装
      "offline"  —— 清单/下载不可用（断网、仓库不可达等），调用方回退随附包
    """
    try:
        import zhsync
    except Exception as e:
        log(f"同步模块不可用（{e}）", logbox)
        return "offline", None

    log("正在检查线上最新汉化包…", logbox)
    man, src_name, base = zhsync.fetch_manifest(lambda m: log(m, logbox))
    if not man:
        log("无法获取线上清单（网络不可用或仓库暂不可达）", logbox)
        return "offline", None

    local = [os.path.join(r, "Locale", "zh") for r in roots]
    local = [d for d in local if os.path.isdir(d)]
    dest = os.path.join(scratch_dir(), "_zh_sync")
    try:
        status, n = zhsync.sync_pack(man, base, local, dest, lambda m: log(m, logbox))
    except Exception as e:
        log(f"同步失败：{e}", logbox)
        return "offline", None
    if status == "uptodate":
        log(f"已是最新汉化包 v{man.get('version')}，无需更新。", logbox)
        return "uptodate", None
    log(f"已获取汉化包 v{man.get('version')}（本次更新 {n} 个文件）", logbox)
    return "ready", dest

def do_install(update=False, logbox=None):
    install = find_install_dir()
    roots = find_all_data_roots(install)
    bundled = os.path.join(resource_dir(), "zh")
    if not os.path.isdir(bundled):
        log("错误：未找到随附的 zh 汉化包目录", logbox); return False
    log(f"安装目录: {install or '(未自动探测)'}", logbox)
    log(f"检测到 {len(roots)} 个数据目录: {', '.join(roots) or '(无)'}", logbox)
    if not roots:
        log("错误：没有可写入的数据目录", logbox); return False

    src = bundled
    if update:
        status, synced = sync_from_github(roots, logbox)
        if status == "uptodate":
            log("完成：本地汉化已是最新，未做任何改动。", logbox)
            return True
        if status == "ready":
            src = synced
        else:
            log("回退：改用随附汉化包安装（联网后重试可获取最新汉化）。", logbox)

    ok = _install_pack(src, roots, install, logbox)
    if ok:
        log("完成！请重启 Pixel Composer 查看中文界面。", logbox)
    else:
        log("部分目录写入失败，请检查磁盘权限后重试。", logbox)
    return ok

def do_restore(logbox=None):
    roots = find_all_data_roots(find_install_dir())
    for root in roots:
        set_language("en", root, logbox)
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
    install = find_install_dir()
    roots = find_all_data_roots(install)
    log(f"安装目录 : {install or '(未探测到)'}", logbox)
    if not roots:
        log("未检测到任何数据目录", logbox); return
    pv = None
    for i, root in enumerate(roots, 1):
        zh = os.path.join(root, "Locale", "zh")
        kp = find_keys_json(root)
        cur = "未知"
        if os.path.exists(kp):
            try: cur = json.load(open(kp, encoding="utf-8")).get("local", "未知")
            except Exception: pass
        ver = None
        try:
            import zhsync
            ver = zhsync.installed_version(root)
        except Exception:
            pass
        if ver and pv is None:
            pv = ver
        tag = f"v{ver}" if ver else "版本未知（旧版工具/社区包）"
        log(f"[{i}] 数据目录 : {root}", logbox)
        log(f"    zh 汉化包 : {'已安装' if os.path.isdir(zh) else '未安装'}（{tag}） | 当前语言 : {cur}", logbox)
    if pv:
        try:
            import zhsync
            _v, summary = zhsync.installed_summary(roots)
            if "不一致" in summary:
                log(f"注意：{summary}（点「② 同步最新汉化」可统一到最新）", logbox)
        except Exception:
            pass

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

def gui():
    import tkinter as tk
    from tkinter import scrolledtext

    root = tk.Tk()
    root.title("Pixel Composer 汉化工具 v1.0.3  ·  在线同步 / 离线可用")
    root.configure(bg=PC_BG)
    root.geometry("620x724")
    root.minsize(560, 660)
    try:
        root.iconbitmap(os.path.join(resource_dir(), "app_icon.ico"))
    except Exception:
        pass

    F_TITLE = ("Microsoft YaHei", 19, "bold")
    F_SUB   = ("Microsoft YaHei", 9)
    F_BTN   = ("Microsoft YaHei", 11, "bold")
    F_MONO  = ("Consolas", 9)

    # 顶栏
    header = tk.Frame(root, bg=PC_BG)
    header.pack(fill="x", padx=22, pady=(18, 6))
    tk.Label(header, text="Pixel Composer 汉化工具  v1.0.3", font=F_TITLE, bg=PC_BG, fg=PC_WHITE).pack(anchor="w")
    tk.Label(header, text="一键安装随附汉化包 · 联网同步最新汉化 · 可一键回滚",
             font=F_SUB, bg=PC_BG, fg=PC_MDWHITE).pack(anchor="w", pady=(3, 0))
    tk.Frame(root, bg=PC_DKGREY, height=1).pack(fill="x", padx=22, pady=(12, 0))

    # 主按钮
    body = tk.Frame(root, bg=PC_BG)
    body.pack(fill="x", padx=22, pady=14)
    PCButton(body, "①  一键汉化（安装 / 启用）", lambda: do_install(False, box),
             width=576, height=52, primary=True, font=F_BTN).pack()

    # 次按钮 2x2
    row1 = tk.Frame(root, bg=PC_BG); row1.pack(padx=22, pady=(0, 8))
    PCButton(row1, "②  同步最新汉化（联网）", lambda: do_install(True, box),
             width=282, height=42, font=F_BTN).pack(side="left")
    tk.Frame(row1, bg=PC_BG, width=12).pack(side="left")
    PCButton(row1, "③  恢复英文", lambda: do_restore(box),
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
    tk.Label(root, text="② 「同步最新汉化」从 GitHub 下载维护者已更新好的成品包（本地不再跑翻译引擎），"
                      "断网时自动回退随附汉化包；\n"
                      "⑥ 汉化工作区标签：同时改写 layouts 文件名与 pack/layouts.zip 条目名"
                      "（只改文件名会被游戏解回英文），⑦ 可随时还原。",
             font=F_SUB, bg=PC_BG, fg=PC_GREY, wraplength=572, justify="left").pack(padx=22, pady=(0, 8), anchor="w")

    # 日志区
    logwrap = tk.Frame(root, bg=PC_DKGREY, bd=0)
    logwrap.pack(fill="both", expand=True, padx=22, pady=(4, 10))
    box = scrolledtext.ScrolledText(logwrap, height=12, font=F_MONO, wrap="word",
                                    bg=PC_DEEP, fg=PC_WHITE, insertbackground=ORANGE,
                                    selectbackground=PC_DARK, selectforeground=PC_WHITE,
                                    relief="flat", bd=0, padx=12, pady=10)
    box.pack(fill="both", expand=True, padx=1, pady=1)

    # 底栏
    foot = tk.Frame(root, bg=PC_BG); foot.pack(fill="x", padx=22, pady=(0, 14))
    tk.Label(foot, text="GitHub  DC1024/pixel-composer-cn", font=F_SUB,
             bg=PC_BG, fg=CYAN).pack(side="left")
    tk.Label(foot, text="MIT License", font=F_SUB,
             bg=PC_BG, fg=PC_GREY).pack(side="right")

    do_status(box)
    root.mainloop()

def main():
    _bootstrap_paths()
    args = sys.argv[1:]
    mode = None
    for a in args:
        if a in ("--install", "--update", "--sync", "--restore", "--rollback", "--status",
                 "--layouts", "--layouts-restore", "--no-gui", "--cli"):
            mode = a.lstrip("-")
    if mode and mode != "cli":
        if mode in ("install", "no-gui"): do_install(False)
        elif mode in ("update", "sync"): do_install(True)
        elif mode == "restore": do_restore()
        elif mode == "rollback": do_rollback()
        elif mode == "status": do_status()
        elif mode == "layouts": do_layouts(False)
        elif mode == "layouts-restore": do_layouts(True)
        return
    # 尝试 GUI，否则 CLI
    try:
        import tkinter  # noqa: F401
    except Exception:
        cli_loop()
        return
    gui()

def cli_loop():
    _bootstrap_paths()
    print("Pixel Composer 一键汉化工具（CLI）")
    while True:
        print("\n1) 一键汉化  2) 同步最新汉化(联网)  3) 恢复英文  4) 还原上一版汉化  5) 查看状态")
        print("6) 汉化工作区标签  7) 还原布局名  0) 退出")
        try:
            c = input("选择> ").strip()
        except EOFError:
            break
        if c == "1": do_install(False)
        elif c == "2": do_install(True)
        elif c == "3": do_restore()
        elif c == "4": do_rollback()
        elif c == "5": do_status()
        elif c == "6": do_layouts(False)
        elif c == "7": do_layouts(True)
        elif c == "0": break
        else: print("无效输入")

if __name__ == "__main__":
    main()
