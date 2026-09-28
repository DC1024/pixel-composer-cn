# Pixel Composer 中文汉化包
# Pixel Composer Chinese Localization

> 中英双语说明 · Bilingual README
> 适用于 Pixel Composer（https://pixel-composer.com/）的中文汉化方案：安装后即可离线使用，联网时可一键同步最新汉化。
> A Chinese localization for Pixel Composer — fully usable offline once installed, with one-click online sync to the latest pack.

---

## 简介 / Introduction

**中文** — 本仓库为 Pixel Composer 提供一套高质量**中文汉化**。汉化内容由维护者定期同步上游官方语言包，统一补翻、校正后发布到本仓库；客户端工具只负责**把成品包下载到本地并安装**，不在你的机器上跑翻译引擎。装好后完全离线可用；想拿最新汉化时点一下「② 同步最新汉化」即可，断网会自动回退到随附的汉化包。相比网上流传的旧汉化包，本方案覆盖率更高、可一键回滚、并能持续跟进官方更新。

**English** — This repo provides a high-quality **Chinese localization** for Pixel Composer. The maintainer periodically syncs the official upstream locale, retranslates and proofreads it, then publishes it here; the client tool only **downloads and installs the finished pack** — no translation engine runs on your machine. Once installed it works fully offline; click "② Sync latest" to pull updates, and it falls back to the bundled pack when offline. Compared with older community packs, it offers higher coverage, one-click rollback, and keeps up with official updates.

- 项目地址 / Repo: https://github.com/DC1024/pixel-composer-cn
- 官网（GitHub Pages）/ Website: https://dc1024.github.io/pixel-composer-cn/
- 许可证 / License: MIT

---

## 下载 / Download

| 方式 Option | 说明 Description |
|---|---|
| **一键汉化 EXE（推荐）** | [⬇ 下载 `PixelComposer-CN-Patcher.exe`（最新发行版）](https://github.com/DC1024/pixel-composer-cn/releases/latest/download/PixelComposer-CN-Patcher.exe) —— 免安装、免 Python，双击即用。 |
| **One-click EXE (recommended)** | [⬇ Download `PixelComposer-CN-Patcher.exe` (latest release)](https://github.com/DC1024/pixel-composer-cn/releases/latest/download/PixelComposer-CN-Patcher.exe) — portable, no Python, just double-click. |
| 源码 Source | 克隆本仓库后运行 `patch_tool.py` / `一键汉化.bat`。 Clone and run `patch_tool.py` / `一键汉化.bat`. |

> **EXE 只从 Releases 下载，仓库内不再存放**（两个约 18 MB 的构建产物每次发版都会进 git 历史，太浪费）。
> 想要二进制请点上面的链接：[最新发行版](https://github.com/DC1024/pixel-composer-cn/releases/latest)。
> **The EXE lives in Releases only** — the repo no longer tracks the ~18 MB build artifacts. Grab the binary from the [latest release](https://github.com/DC1024/pixel-composer-cn/releases/latest).

![工具界面 / GUI](assets/screenshot.png)

> **配色 / Palette**：EXE 界面与官网均取自 Pixel Composer 官方 `default` 主题（`Themes/default/values.json`）——背景 `#1c1c23`、面板 `#3b3b4e`、主强调色橙 `#ff9166`、文字 `#d6d6e8`。
> Both the GUI and the website use Pixel Composer's official `default` theme palette — bg `#1c1c23`, panel `#3b3b4e`, accent orange `#ff9166`, text `#d6d6e8`.

---

## 特性 / Features

| 特性 Feature | 说明 Description |
|---|---|
| 离线可用 Offline-ready | 随附完整 `zh` 汉化包，安装后全程无需联网；② 联网只是「取更新」，断网会自动回退随附包。 Ships with a complete `zh` pack — no network needed after install; ② only fetches updates and falls back to the bundled pack. |
| 持续更新 Actively synced | 维护者定期同步官方语言包 → 补翻校正 → 推送本仓库 → 客户端一键同步成品包，无需重装工具。 Maintainer syncs the official locale, retranslates, pushes; clients pull the finished pack in one click — no reinstall. |
| 一键 One-click | EXE / 图形界面 / 命令行 / 批处理四种方式任选。 EXE, GUI, CLI, or `.bat` — your choice. |
| 配色一致 Themed | 界面配色与 Pixel Composer 官方主题一致。 GUI palette matches Pixel Composer's official theme. |
| 安全 Safe | 写入前自动备份原文件，支持「恢复英文」与「还原上一版」。 Auto-backup before writing; restore English or roll back. |
| 双目录 Dual-root | 自动同时写入 `LocalAppData` 与游戏目录，避免汉化"不生效"。 Writes to both data dirs so the language actually applies. |
| 高覆盖 High coverage | 官方词条 1888 / 1916 已汉化（**98.5%**），另补 180 条官方未收录词条；节点约 93%。 See [覆盖率 / Coverage](#覆盖率-coverage). |

---

## 快速开始 / Quick Start

### 方式一：下载 EXE（推荐）/ Method 1: Download the EXE (recommended)
从 [Releases](https://github.com/DC1024/pixel-composer-cn/releases) 下载 [`PixelComposer-CN-Patcher.exe`](https://github.com/DC1024/pixel-composer-cn/releases/latest/download/PixelComposer-CN-Patcher.exe)，双击打开，点击「① 一键汉化」即可。免安装、无需 Python。
Download [`PixelComposer-CN-Patcher.exe`](https://github.com/DC1024/pixel-composer-cn/releases/latest/download/PixelComposer-CN-Patcher.exe) from [Releases](https://github.com/DC1024/pixel-composer-cn/releases), double-click, then click "① 一键汉化". Portable, no Python required.

### 方式二：一键批处理 / Method 2: One-click `.bat`
双击仓库内的 **`一键汉化.bat`**，按提示操作即可（需 Python 3.7+）。
Double-click **`一键汉化.bat`** in the repo (requires Python 3.7+).

### 方式三：图形界面 / Method 3: GUI
```bash
python patch_tool.py
```
会弹出一个窗口，点击「① 一键汉化」即可。
A window opens; click "① 一键汉化（安装/启用）".

### 方式四：命令行 / Method 4: Command line
```bash
python patch_tool.py --install
```
> 需要 Python 3.7+。若系统默认 `python` 不是 Python 3，请用 `py` 或 `python3`。
> Requires Python 3.7+. If `python` isn't Python 3, use `py` or `python3`.

完成后再**重启 Pixel Composer**，界面即为中文。
**Restart Pixel Composer** afterward — the UI will be in Chinese.

---

## 使用方法 / Usage

### 图形界面按钮 / GUI buttons
| 按钮 Button | 作用 Action |
|---|---|
| ① 一键汉化（安装/启用） Install & enable | 安装并启用中文（完整写入）。 Install + enable Chinese (full write). |
| ② 同步最新汉化 Sync latest | **联网**从 GitHub 拉取维护者已翻好的最新汉化包并安装（只下载成品，本地不跑翻译引擎）；断网自动回退随附包。 Online: download and install the maintainer's latest finished pack from GitHub (no local engine); falls back to the bundled pack when offline. |
| ③ 恢复英文 Restore English | 切回英文（保留汉化备份）。 Switch back to English (keeps a backup). |
| ④ 还原上一版汉化 Rollback | 回滚到上一次安装的汉化包。 Roll back to the previously installed pack. |
| ⑤ 查看状态 Status | 显示安装目录、汉化状态与当前语言。 Show install path, pack status, current language. |
| ⑥ 汉化工作区标签 Localize layout tabs | 把自带布局改名为中文：**同时**改写 `layouts/*.json` 文件名与游戏自带 `pack/layouts.zip` 里的条目名（原 zip 备份为 `layouts.zip.bak_cn`）。 Renames the layout files **and** the entries inside the game's own `pack/layouts.zip` (the original zip is backed up as `layouts.zip.bak_cn`). |
| ⑦ 还原布局名 Restore layout names | 把布局文件名还原成英文。 Restore the original English layout file names. |

> **②「同步最新汉化」到底做了什么？ / What does ② actually do?**
> 它**不在你的电脑上做翻译**，而是从 GitHub 下载一份**已经翻好的成品包**（`zh/`）。步骤是：① 依次尝试三个源拉取清单 `zh/manifest.json`（GitHub Pages → jsDelivr CDN → GitHub Raw）；② 用 sha256 比对本地已装的包，**只下载有变化的文件**（11 MB 的中文字体通常只在首次下载，之后每次一般只有几十 KB 的 json）；③ 备份现有 `zh` 后整包写入两个数据目录并保持中文。断网或源全部不可达时，会自动改用随附的汉化包，不会让汉化"变空"。若本地已是最新，会直接提示"无需更新"。
>
> It does **not translate anything on your machine** — it downloads an **already-translated pack** (`zh/`) from GitHub. It fetches the manifest `zh/manifest.json` from three sources in order (GitHub Pages → jsDelivr CDN → GitHub Raw), compares sha256 against your installed pack, and **downloads only changed files** (the 11 MB CJK font is normally fetched once; later syncs are usually a few dozen KB of JSON). The existing `zh` is backed up before the whole pack is written to both data roots. If the network is unavailable, it falls back to the bundled pack instead of leaving you with nothing. If you're already current, it simply reports "nothing to update".

> **为什么这样设计 / Why it works this way**：翻译只在**维护者侧做一次**（同步上游官方语言包 → 补翻 → 统一校正 → 推送），而不是在每台用户机器上各跑一遍。好处是：结果统一、质量可控（可持续人工校对）、客户端不再需要携带翻译引擎、也避免了"每个用户翻出来的版本都不一样"。
>
> Translation happens **once, on the maintainer side** (sync the official locale → retranslate → proofread → push), not once per user machine. That means consistent results, quality you can keep improving by hand, no translation engine shipped to clients, and no divergence between users.

### 命令行参数 / Command-line flags
```text
--install           安装并启用中文（等价于 --no-gui）
--update / --sync   从 GitHub 同步最新汉化包并安装（断网回退随附包）
--restore           恢复英文
--rollback          还原上一版汉化
--status            查看当前状态（含已安装汉化包版本）
--layouts           汉化工作区标签（重命名布局文件）
--layouts-restore   还原布局文件名
--no-gui            无界面直接安装（用于脚本/自动化）
--cli               强制进入交互式命令行
```
示例 / Examples:
```bash
python patch_tool.py --sync              # 同步最新汉化包
python patch_tool.py --status            # 查看状态
python patch_tool.py --layouts           # 工作区标签改中文
python patch_tool.py --no-gui            # 脚本中静默安装
```

自定义同步源（镜像 / 内网）/ Custom sync source:
```bash
set PCCN_SOURCE=https://my-mirror.example.com/pixel-composer-cn
python patch_tool.py --sync
```
> `PCCN_SOURCE` 可填仓库地址或 `zh/` 目录地址，会被排到三个默认源之前优先尝试。

---

## 更新机制 / How Updates Work

**翻译只在维护者侧做一次，客户端只下载成品包。**
Translation happens **once, on the maintainer side**; the client only downloads the finished pack.

```text
游戏自带 pack/locale.zip（官方 en 基准） + Locale/version
        │  ① 维护者：定期同步上游
        ▼
build/sync_upstream.py    抽取 en → 补翻新增/残留条目 → 注入补充表 → 写 zh/
        │  ② 生成 zh/manifest.json（版本号 / sha256 清单）
        ▼
git push origin main      →  GitHub（Raw / Pages / jsDelivr 三个下载源）
        │  ③ 客户端：一键同步
        ▼
「② 同步最新汉化」        拉清单 → 比对 sha256 → 只下载变化的文件 → 备份后安装
```

| 角色 Role | 做什么 What it does |
|---|---|
| **上游 Upstream** | 游戏自带的 `pack/locale.zip` 与 `Locale/version`。游戏一更新，官方词条与版本号就会变，维护者脚本据此感知。 The game's own `pack/locale.zip` + `Locale/version`; a game update changes them, which the maintainer script detects. |
| **维护者 Maintainer** | 运行 `python build/sync_upstream.py --push`：抽取官方 `en` 基准 → 补翻新增/残留词条 → 注入补充表 → 写 `zh/` 与 `zh/manifest.json` → 提交推送。 Runs `build/sync_upstream.py --push`: extracts the official `en` baseline, retranslates new/leftover entries, injects the extra tables, writes `zh/` + `zh/manifest.json`, then commits and pushes. |
| **客户端 Client** | 点「② 同步最新汉化」（或 `--sync`）：拉清单 → 按文件哈希比对 → 只下载有变化的文件 → 备份现有 `zh` 后整包安装。**本地不跑翻译引擎。** Clicks "② Sync latest" (or `--sync`): fetches the manifest, compares per-file hashes, downloads only changed files, backs up the current `zh`, installs the pack. **No engine runs locally.** |

汉化包版本记录在 `zh/manifest.json` 的 `version` 字段，随包一起下发；「⑤ 查看状态」会显示当前安装的包版本。若某源不可用，会自动换下一个源（可用环境变量 `PCCN_SOURCE` 指定镜像）。
The pack version lives in `zh/manifest.json` (`version`) and travels with the pack; "⑤ Status" shows which version is installed. If a source is unavailable it falls back to the next one (set `PCCN_SOURCE` to use a mirror).

---

## 覆盖率 / Coverage

| 文件 File | 条目 Entries | 内容 Content |
|---|---|---|
| `words.json` | **2096** | 词条 / 标签 / 菜单项。官方 `en` 的 1916 条中已汉化 **1888** 条（**98.5%**），另额外补充 180 条官方未收录词条。 |
| `UI.json` | 560 | 界面文本 / UI strings |
| `nodes.json` | 942 | 节点名称 / node names（约 93%） |
| `junctions.json` | 3 | 连接点 / junctions |
| `config.json` / `fonts/` / `notes/` | 已含 / included | 配置与字体 / config & fonts |

> 说明 / Note：剩余未翻译的词条多为品牌名、格式名或专有名词（如 `CMYK`、`OKLAB`、`PXC`、`ORA`、`Aseprite`、`ShaderToy`、`Bluesky` 等），按约定保留英文，以避免歧义。
> The few untranslated entries are intentional English keeps — brand/format/proper nouns (e.g. `CMYK`, `OKLAB`, `PXC`, `ORA`, `Aseprite`, `ShaderToy`, `Bluesky`) kept as-is to avoid ambiguity.

---

## 工作原理 / How It Works

**中文** — Pixel Composer 采用 **Locale 覆盖机制**（而非修改二进制）：程序会从 `Locale/{语言}/` 读取 `words.json`、`nodes.json`、`UI.json`、`junctions.json`、`config.json`、`fonts/`、`notes/` 等文件，`en` 作为兜底语言最先加载。本工具把预翻好的 `zh` 包写入该目录，并把语言开关 `preferences/1171/keys.json` 中的 `local` 改为 `"zh"`。`Locale/zh/` 里还会多一个 `manifest.json`（版本号 + 各文件 sha256 清单），供同步功能比对版本用；游戏只按上述固定文件名加载，多这一个 JSON 对游戏没有影响。

由于该游戏的 `persistPreference.json` 在 `LocalAppData` 与游戏目录之间互相指向，工具会**同时写入两个数据目录**并确保两处的 `keys.json` 都设为 `zh`，从而保证汉化稳定生效。

**English** — Pixel Composer uses a **Locale overlay** (not binary patching): it reads `words.json`, `nodes.json`, `UI.json`, `junctions.json`, `config.json`, `fonts/`, `notes/` from `Locale/{lang}/`, with `en` loaded first as a fallback. This tool drops the pre-translated `zh` pack into that folder and flips the language switch in `preferences/1171/keys.json` (`local` → `"zh"`). `Locale/zh/` additionally carries a `manifest.json` (version + per-file sha256) used by the sync feature to compare versions; the game loads only the fixed file names above, so the extra JSON has no effect on it.

Because the game's `persistPreference.json` points circularly between `LocalAppData` and the game directory, the tool **writes to both data roots** and sets `zh` in each `keys.json`, so the localization reliably applies.

```
LocalAppData/PixelComposer/Locale/zh/...      ← 写入点 1 / root 1
游戏目录/PixelComposer/Locale/zh/...           ← 写入点 2 / root 2
两处 preferences/1171/keys.json 均设 local="zh"
```

---

## 已知限制 / Known Limitations

| 位置 Where | 情况 Status | 处理 Workaround |
|---|---|---|
| **浮动面板标题**（`Toolbar`、`Collections` 等） | 这些标题由主程序内部维护的**面板注册表**直接绘制，**不走语言包**。已实测 20 余种候选键名（`panel_toolbar`、`panel_collections`、`Toolbar Panel`、原始字符串 `Toolbar` / `Collections` 等）全部无效。 | 无需处理：**打开面板的入口在「面板菜单」里，条目已全部汉化**（显示为「工具栏」「集合」「图表」等），不影响日常使用。 |
| **工作区布局标签**（`Horizontal` / `Vertical` / `Preview` / `Drawing` / `Side menu`） | 标签显示的是 `layouts/*.json` 的**文件名**，本身不查语言表（已确认布局名不存在于任何语言包或偏好设置中，程序按目录枚举文件）。⚠️ 只改文件名**会被还原**：实测改完名启动一次，游戏就从 `pack/layouts.zip` 把 5 个英文名重新解了出来，变成中英两套重复标签。 | 点 **⑥ 汉化工作区标签** —— 它会**同时改写 `pack/layouts.zip` 里的条目名**（原 zip 备份为 `layouts.zip.bak_cn`），改完启动实测**只剩中文名、英文名不再回来**；不满意点 **⑦ 还原布局名**。注意：执行 ⑥ 会触发游戏按 zip 重新解出一次内置布局，若你改过这 5 个内置布局的内容会被还原（你自建的布局不受影响）；`__default.json` 与 `layouts/version` 永不被改动。 |
| **内置参考文档 `notes/`**（`Blend modes reference` / `Lindenmayer system reference` / `MK Panels reference`） | 这三篇是带专用排版标记（`{g}`、`<x20>`、`<x128>` 等）的 Markdown 参考文档，官方语言包中只有英文版，当前**未翻译**（游戏会回退显示英文原文）。 | 待补。翻译它们需要保留排版标记，属于独立的校对工作；需要的话可提 Issue。 |
| `2d` / `3d` / `CMYK` / `OKLAB` / `PXC` 等 | 品牌名 / 格式名 / 专有名词。 | 按约定保留英文，避免歧义。 |

**English** — Floating panel titles (`Toolbar`, `Collections`, …) are drawn by the executable's internal panel registry and **never pass through the locale tables** — 20+ candidate key forms were tested and none had any effect. The panel *menu* entries (the way you actually open these panels) are fully translated, so this is cosmetic. Workspace layout tabs show `layouts/*.json` **file names**, which the locale tables cannot touch — use button ⑥ to rename them (⑦ reverts); `__default.json` and `layouts/version` are never modified. The three built-in reference documents under `notes/` are Markdown files using a custom layout markup (`{g}`, `<x20>`, …) and ship in English only — they are **not translated yet** and fall back to English.

---

## 与旧社区汉化包的区别 / vs. Old Community Pack

| 对比项 / Aspect | 旧社区汉化包 Old pack | 本方案 This project |
|---|---|---|
| 更新速度 Updates | 慢，依赖作者手动发布 / slow, manual | 维护者定期同步上游，客户端一键取最新包 / maintainer syncs upstream, clients pull in one click |
| 覆盖率 Coverage | 较低 / lower | 词条 98.5%（1888/1916）· 节点 ~93% |
| 联网需求 Network | 常需联网取包 / often online | 装好后离线可用；② 联网只取更新，断网自动回退 / offline-ready; ② only fetches updates and falls back offline |
| 可回滚 Rollback | 通常不支持 / usually no | 备份 + 一键回滚 / backup + one-click rollback |
| 双目录 Dual-root | 易漏写导致不生效 / easy to miss | 自动双写 / auto dual-write |

---

## 从源码构建 EXE / Build the EXE from Source

需要 Python 3.7+（含 tkinter）。双击运行 **`build_exe.bat`**，脚本会自动安装 PyInstaller、把 `zh/` 汉化包与同步模块内嵌进程序，产出单文件 **`PixelComposer一键汉化.exe`**（免安装、双击即用）。产物已被 `.gitignore` 忽略，不会进版本库 —— 正式发行请上传到 GitHub Releases。

Requires Python 3.7+ (with tkinter). Double-click **`build_exe.bat`**; it installs PyInstaller, embeds the `zh/` pack + sync module, and produces a single-file **`PixelComposer一键汉化.exe`**. The artifact is git-ignored on purpose — publish it as a GitHub Release instead of committing it.

等价的命令行 / Equivalent CLI:
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name PixelComposer-CN-Patcher \
  --icon app_icon.ico --add-data "zh;zh" --add-data "app_icon.ico;." \
  --add-data "translate_core.py;." --add-data "zhsync.py;." \
  --hidden-import translate_core --hidden-import zhsync patch_tool.py
```

> ⚠️ 如果你给 PyInstaller 传了 `--specpath`，`--add-data` / `--icon` **必须改用绝对路径** —— PyInstaller 以 spec 文件所在目录为基准解析相对路径，否则会报 `Unable to find ...\spec\zh`。
> If you pass `--specpath`, make `--add-data` / `--icon` **absolute** — PyInstaller resolves relative paths against the spec directory, otherwise it fails with `Unable to find ...\spec\zh`.

图标由 `build/make_icon.py` 生成（配色取自 Pixel Composer 官方主题）。
The icon is generated by `build/make_icon.py` (colors from Pixel Composer's official theme).

---

## 贡献 / Contribute

翻译引擎与源数据位于 `build/` 目录（**引擎只用于维护者侧生成汉化包，客户端不运行**）：

- `build/translate_core.py` — 翻译引擎（短语表 + 词条表 + 规则组合）。
- `build/sync_upstream.py` — **维护者主脚本**：同步上游官方语言包 → 补翻 → 更新 `zh/` 与 `zh/manifest.json`（`--push` 可自动提交推送）。
- `zhsync.py` — **客户端同步模块**：拉清单、比对 sha256、按需下载并安装（`patch_tool.py` 的 ② 即调用它）。
- `build/en_*.json` — 从游戏原始 `en` 语言包抽取的源数据。
- `build/zh_*_seed.json` — 人工校对的中文种子。
- `build/build_locale.py` / `build/analyze.py` — 构建与分析脚本。
- `build/retranslate_leftovers.py` — 补翻残留英文条目。

如需补充翻译，可直接编辑 `zh/words.json` / `zh/nodes.json` —— **手工修正基本不会被自动覆盖**：补翻逻辑只在「该条目的中文值仍等于英文原文」时才重新翻译，已有中文值一律跳过（例外：`translate_core.py` 里 `LOCALE_OVERRIDE` 列出的键是工具刻意纠正项，会强制覆盖）。改完运行 `python build/sync_upstream.py --force --version <新版号>` 重新生成清单并推送。

To improve translations, edit `zh/words.json` / `zh/nodes.json` directly — **manual fixes are generally not overwritten** (the re-translate step only touches entries whose value still equals the English original; exceptions are the keys listed in `LOCALE_OVERRIDE`, which the tool intentionally forces). Then run `python build/sync_upstream.py --force --version <new>` to regenerate the manifest and push.

---

## 许可证 / License

[MIT](LICENSE) © DC1024

你可以自由使用、修改、再分发本汉化包；但 Pixel Composer 本身 © 其原作者，请遵守其许可。
Free to use, modify, and redistribute. Pixel Composer itself © its original author — respect its license.
