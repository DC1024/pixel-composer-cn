# Pixel Composer 中文汉化包（离线版）
# Pixel Composer Chinese Localization (Offline)

> 中英双语说明 · Bilingual README
> 适用于 Pixel Composer（https://pixel-composer.com/）的离线、自包含中文汉化方案。
> An offline, self-contained Chinese localization for Pixel Composer.

---

## 简介 / Introduction

**中文** — 这是一个为 Pixel Composer 打造的**离线中文汉化包**。它把一整套已经预先翻译好的 `zh` 语言包、一个内置的翻译引擎，以及一个一键式打补丁工具打包在一起。你不需要联网、不需要手动改文件、也不需要等社区更新。相比网上流传的旧汉化包，本方案覆盖率更高、更新更快、可一键回滚。

**English** — This is an **offline Chinese localization pack** for Pixel Composer. It bundles a fully pre-translated `zh` locale, a built-in translation engine, and a one-click patcher. No internet, no manual file editing, no waiting for community updates. Compared with older community packs, it offers higher coverage, faster updates, and one-click rollback.

- 项目地址 / Repo: https://github.com/DC1024/pixel-composer-cn
- 官网（GitHub Pages）/ Website: https://dc1024.github.io/pixel-composer-cn/
- 许可证 / License: MIT

---

## 下载 / Download

| 方式 Option | 说明 Description |
|---|---|
| **一键汉化 EXE（推荐）** | [⬇ 下载 `PixelComposer一键汉化.exe`](https://github.com/DC1024/pixel-composer-cn/raw/main/PixelComposer%E4%B8%80%E9%94%AE%E6%B1%89%E5%8C%96.exe) —— 免安装、免 Python，双击即用。 |
| **One-click EXE (recommended)** | [⬇ Download `PixelComposer一键汉化.exe`](https://github.com/DC1024/pixel-composer-cn/raw/main/PixelComposer%E4%B8%80%E9%94%AE%E6%B1%89%E5%8C%96.exe) — portable, no Python, just double-click. |
| 源码 Source | 克隆本仓库后运行 `patch_tool.py` / `一键汉化.bat`。 Clone and run `patch_tool.py` / `一键汉化.bat`. |

![工具界面 / GUI](assets/screenshot.png)

> **配色 / Palette**：EXE 界面与官网均取自 Pixel Composer 官方 `default` 主题（`Themes/default/values.json`）——背景 `#1c1c23`、面板 `#3b3b4e`、主强调色橙 `#ff9166`、文字 `#d6d6e8`。
> Both the GUI and the website use Pixel Composer's official `default` theme palette — bg `#1c1c23`, panel `#3b3b4e`, accent orange `#ff9166`, text `#d6d6e8`.

---

## 特性 / Features

| 特性 Feature | 说明 Description |
|---|---|
| 离线 Offline | 自带 `zh` 汉化包与翻译引擎，全程无需联网。 Ships with the `zh` pack + engine; no network needed. |
| 一键 One-click | EXE / 图形界面 / 命令行 / 批处理四种方式任选。 EXE, GUI, CLI, or `.bat` — your choice. |
| 配色一致 Themed | 界面配色与 Pixel Composer 官方主题一致。 GUI palette matches Pixel Composer's official theme. |
| 安全 Safe | 写入前自动备份原文件，支持「恢复英文」与「还原上一版」。 Auto-backup before writing; restore English or roll back. |
| 双目录 Dual-root | 自动同时写入 `LocalAppData` 与游戏目录，避免汉化"不生效"。 Writes to both data dirs so the language actually applies. |
| 高覆盖 High coverage | UI 100% / 词条 99.1% / 节点约 93%。 See [覆盖率 / Coverage](#覆盖率-coverage). |

---

## 快速开始 / Quick Start

### 方式一：下载 EXE（推荐）/ Method 1: Download the EXE (recommended)
下载 [`PixelComposer一键汉化.exe`](https://github.com/DC1024/pixel-composer-cn/raw/main/PixelComposer%E4%B8%80%E9%94%AE%E6%B1%89%E5%8C%96.exe)，双击打开，点击「① 一键汉化」即可。免安装、无需 Python。
Download [`PixelComposer一键汉化.exe`](https://github.com/DC1024/pixel-composer-cn/raw/main/PixelComposer%E4%B8%80%E9%94%AE%E6%B1%89%E5%8C%96.exe), double-click, then click "① 一键汉化". Portable, no Python required.

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
| ② 更新汉化（增量补全） Update | 增量更新到最新翻译。 Incrementally update to the latest translations. |
| ③ 恢复英文 Restore English | 切回英文（保留汉化备份）。 Switch back to English (keeps a backup). |
| ④ 还原上一版汉化 Rollback | 回滚到上一次安装的汉化包。 Roll back to the previously installed pack. |
| ⑤ 查看状态 Status | 显示安装目录、汉化状态与当前语言。 Show install path, pack status, current language. |

### 命令行参数 / Command-line flags
```text
--install      安装并启用中文（等价于 --no-gui）
--update       增量更新汉化
--restore      恢复英文
--rollback     还原上一版汉化
--status       查看当前状态
--no-gui       无界面直接安装（用于脚本/自动化）
--cli          强制进入交互式命令行
```
示例 / Examples:
```bash
python patch_tool.py --update     # 更新到最新翻译
python patch_tool.py --status     # 查看状态
python patch_tool.py --no-gui     # 脚本中静默安装
```

---

## 覆盖率 / Coverage

| 文件 File | 覆盖 Coverage | 内容 Content |
|---|---|---|
| `UI.json` | 379 / 379（**100%**） | 界面文本 / UI strings |
| `words.json` | 1916（**99.1%**） | 词条 / 标签 / 菜单项 / words & labels |
| `nodes.json` | 942（**约 93%**） | 节点名称 / node names |
| `junctions.json` | 3 | 连接点 / junctions |
| `config.json` / `fonts/` / `notes/` | 已含 / included | 配置与字体 / config & fonts |

> 说明 / Note：剩余未翻译的词条多为品牌名、格式名或专有名词（如 `CMYK`、`OKLAB`、`PXC`、`ORA`、`Aseprite`、`ShaderToy`、`Bluesky` 等），按约定保留英文，以避免歧义。
> The few untranslated entries are intentional English keeps — brand/format/proper nouns (e.g. `CMYK`, `OKLAB`, `PXC`, `ORA`, `Aseprite`, `ShaderToy`, `Bluesky`) kept as-is to avoid ambiguity.

---

## 工作原理 / How It Works

**中文** — Pixel Composer 采用 **Locale 覆盖机制**（而非修改二进制）：程序会从 `Locale/{语言}/` 读取 `words.json`、`nodes.json`、`UI.json`、`junctions.json`、`config.json`、`fonts/`、`notes/` 等文件，`en` 作为兜底语言最先加载。本工具把预翻好的 `zh` 包写入该目录，并把语言开关 `preferences/1171/keys.json` 中的 `local` 改为 `"zh"`。

由于该游戏的 `persistPreference.json` 在 `LocalAppData` 与游戏目录之间互相指向，工具会**同时写入两个数据目录**并确保两处的 `keys.json` 都设为 `zh`，从而保证汉化稳定生效。

**English** — Pixel Composer uses a **Locale overlay** (not binary patching): it reads `words.json`, `nodes.json`, `UI.json`, `junctions.json`, `config.json`, `fonts/`, `notes/` from `Locale/{lang}/`, with `en` loaded first as a fallback. This tool drops the pre-translated `zh` pack into that folder and flips the language switch in `preferences/1171/keys.json` (`local` → `"zh"`).

Because the game's `persistPreference.json` points circularly between `LocalAppData` and the game directory, the tool **writes to both data roots** and sets `zh` in each `keys.json`, so the localization reliably applies.

```
LocalAppData/PixelComposer/Locale/zh/...      ← 写入点 1 / root 1
游戏目录/PixelComposer/Locale/zh/...           ← 写入点 2 / root 2
两处 preferences/1171/keys.json 均设 local="zh"
```

---

## 与旧社区汉化包的区别 / vs. Old Community Pack

| 对比项 / Aspect | 旧社区汉化包 Old pack | 本方案 This project |
|---|---|---|
| 更新速度 Updates | 慢，依赖作者手动发布 / slow, manual | 内置引擎，可随游戏增量更新 / built-in engine, incremental |
| 覆盖率 Coverage | 较低 / lower | UI 100% · 词条 99.1% · 节点 ~93% |
| 联网需求 Network | 常需联网取包 / often online | 完全离线 / fully offline |
| 可回滚 Rollback | 通常不支持 / usually no | 备份 + 一键回滚 / backup + one-click rollback |
| 双目录 Dual-root | 易漏写导致不生效 / easy to miss | 自动双写 / auto dual-write |

---

## 从源码构建 EXE / Build the EXE from Source

需要 Python 3.7+（含 tkinter）。双击运行 **`build_exe.bat`**，脚本会自动安装 PyInstaller、把 `zh/` 汉化包与翻译引擎内嵌进程序，产出单文件 **`PixelComposer一键汉化.exe`**（免安装、双击即用）。

Requires Python 3.7+ (with tkinter). Double-click **`build_exe.bat`**; it installs PyInstaller, embeds the `zh/` pack + engine, and produces a single-file **`PixelComposer一键汉化.exe`**.

等价的命令行 / Equivalent CLI:
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name PixelComposer-CN-Patcher \
  --icon app_icon.ico --add-data "zh;zh" --add-data "app_icon.ico;." \
  --add-data "translate_core.py;." --hidden-import translate_core patch_tool.py
```

图标由 `build/make_icon.py` 生成（配色取自 Pixel Composer 官方主题）。
The icon is generated by `build/make_icon.py` (colors from Pixel Composer's official theme).

---

## 贡献 / Contribute

翻译引擎与源数据位于 `build/` 目录：

- `build/translate_core.py` — 翻译引擎（短语表 + 词条表 + 规则组合）。
- `build/en_*.json` — 从游戏原始 `en` 语言包抽取的源数据。
- `build/zh_*_seed.json` — 人工校对的中文种子。
- `build/build_locale.py` / `build/analyze.py` — 构建与分析脚本。

如需补充翻译，可编辑字典后运行构建脚本重新生成 `zh/` 包。
To add translations, edit the dictionaries and re-run the build scripts to regenerate the `zh/` pack.

---

## 许可证 / License

[MIT](LICENSE) © DC1024

你可以自由使用、修改、再分发本汉化包；但 Pixel Composer 本身 © 其原作者，请遵守其许可。
Free to use, modify, and redistribute. Pixel Composer itself © its original author — respect its license.
