# Pixel Composer 汉化 · 上游同步自动化方案

> 状态：**已定稿并已落地**（2026-09-29）。下文的 4 项决策均已固化到代码。
> 关联：v1.2.1 已发布；客户端「② 同步最新汉化」已自动化；本方案解决**维护者侧**的
> 「捕获官方更新 → 补翻 → 推送 GitHub」这一段。

## 0. 已锁定的决策 Decisions locked

| # | 决策 Decision | 落地实现 Implementation |
|---|---|---|
| 1 | **汉化包版本号跟 `game_version`** | `plan_version()`：上游 `Locale/version` 前进（或本轮有内容更新）→ 自动 patch +1，并在日志里写明原因。可用 `--version` 强制指定。注意**包版本 ≠ 工具版本**（`patch_tool.py` 的 `VERSION`）。 |
| 2 | **新串不写 "TODO" 标记** | 翻不了的条目在该 key 上保持**英文回退**（游戏显示英文原文），同时写进 `build/todo_report.md` 待办清单。永久修正靠 `translate_core.LOCALE_OVERRIDE`，后续同步自动继承。 |
| 3 | **直接推送 GitHub，不走 PR** | `--push` 直接提交并推 `main`（先试本机凭据，失败回退 `~/.git-credentials` 里的 PAT 直连）。无变化时跳过提交。 |
| 4 | **本地定时，每月检测一次** | `build/install_sync_task.ps1` 注册 Windows 计划任务（默认每月 1 号 09:00，`-Frequency weekly` 可改回每周），`build/run_sync.bat` 到点在本地跑并写日志。 |

> ⚠️ **实施过程中的重要修正**：`build/sync_upstream.py` **本来就已经存在**
> （用来同步上游、补翻、写清单、`--push`），所以本次不是重写，而是在它之上做增强
> —— 新增「版本号跟上游」「en 基线快照 + 原文改动检测」「待办清单」「每月定时任务」。
> 下文保留原方案结构，凡与实测不符处以 **【实测修正】** 标注。

---

## 1. 结论速览

| 问题 | 结论 |
|---|---|
| 能不能自动化？ | **能，但只能做半自动**。机械链路（检测版本→提取官方 en→diff→搬运旧译文→打包→开 PR）100% 可脚本化；唯独「新字符串的最终译文质量」必须人肉把关。 |
| 闭源是不是只能靠本地 Pixel Composer？ | 不完全是「只能本地」。**可观测源 = 官方发布的语言包文件**（`pack/locale.zip` 里的 `en/`）。本地安装目录是一种观测点；等价替代是用 steamcmd 把 depot 拉到任意机器。限制在于「只能读成品包，读不到源码」。 |
| 客户端（用户侧）要改吗？ | **不要**。用户点「② 同步最新汉化」已是自动拉取成品包，本方案不碰它。 |

---

## 2. 上游可观测源（落到具体文件）

- **官方英文基准** = 游戏安装目录 `pack/locale.zip` 内的 `en/` 成员
  （`words.json` / `UI.json` / `nodes.json` / `junctions.json` / `config.json`）。
  `patch_tool.ensure_en()` 已经用这一来源解出 `en/`，可直接复用同一 zip，无需另找。
- **版本信号**（任一项变化即触发同步）：
  - `en/version`（或 `Locale/version`）里的 `version` 整型（如 `122000`）；
  - `pack/locale.zip` 自身的 sha256（官方只要动过语言包，这个就会变）。
- **现有可复用函数**（都在仓库里，不用重写）：
  - `patch_tool.find_install_dir()` → 定位含 `pack/locale.zip` 的安装目录；
  - `zhsync.build_manifest()` / `hash_tree()` / `sha256_file()` → 生成清单与逐文件哈希；
  - `translate_core`（`apply_locale_extras` 已知）→ 翻译引擎，新串草稿复用其入口；
  - 维护者侧脚本**约定位置**：`build/sync_upstream.py`（`zhsync.py` 头部注释已预留）。

---

## 3. 半自动流水线（8 步）

| # | 步骤 | 动作 | 自动？ | 复用 / 产出 |
|---|---|---|---|---|
| 1 | 检测版本 | 比对 `pack/locale.zip` 的 sha256 与 `en/version` 是否变化 | ✅ 全自动 | 缓存上次 hash/版本，无变化直接退出 |
| 2 | 提取官方包 | 解包 `locale.zip`，只取 `en/*.json` | ✅ 全自动 | `zipfile` + `find_install_dir()` |
| 3 | diff 比对 | 新旧 `en/` 对照，定位 新增/变更/删除 key | ✅ 全自动 | 字典比较（词库是扁平 dict） |
| 4 | 搬运译文 | `en` 未变的 key 直接搬旧 `zh` 译文 | ✅ 全自动 | 零风险 |
| 5 | 新串翻译 | 新增/变值 key 出中文 | ⚠️ 半自动 | `translate_core` 出草稿 + **人工校订**（人工闸） |
| 6 | 打包 | 生成 `zh/` + `manifest.json`（sha256 清单） | ✅ 全自动 | `zhsync.build_manifest()` |
| 7 | 发布 | 开 PR / 预发布 | ✅ 全自动（人审核） | 留人工点合入 |
| 8 | 客户端同步 | 用户点「② 同步最新汉化」拉取 | ✅ 已自动化 | 现状，不改 |

**核心不变量（务必遵守）**：第 4 步只对「key 同名且 en 值完全相同」的条目搬运旧译文；
**key 同名但 en 值变了** → 旧译文可能过时，必须标 `TODO` 交人工复核，绝不能盲目搬运；
**en 里删除的 key** → 直接从 `zh` 丢弃（保持干净）。

---

## 4. 维护者侧脚本设计 `build/sync_upstream.py`

### 4.1 接口

```text
python build/sync_upstream.py [--install-dir D] [--dry-run] [--push]
  --install-dir D   覆盖游戏安装目录（默认用 find_install_dir 自动探测）
  --dry-run         只跑检测+diff+生成到缓存，不写基线、不开 PR
  --push            生成后自动提交分支并开 PR（默认只落地到 build/cache/zh_out/ 供你过目）
```

### 4.2 目录约定

```text
build/
  sync_upstream.py        # 本脚本
  cache/
    en_baseline/          # 上次成功同步时的官方 en 快照（gitignore）
    en_new/               # 本次解出的新 en（临时）
    zh_out/               # 本次生成的完整 zh 包（供人工/CI 校验）
    last_locale_zip.sha256
    last_game_version.txt
```

### 4.3 伪代码（评审用，函数名以实际 translate_core 入口为准）

```python
import os, json, zipfile, hashlib, shutil
import zhsync, patch_tool
from translate_core import translate_lexicons, apply_locale_extras  # 入口名以实际为准

CACHE   = os.path.join(here, "build", "cache")
BASE_EN = os.path.join(CACHE, "en_baseline")
LAST_ZIP = os.path.join(CACHE, "last_locale_zip.sha256")
LAST_VER = os.path.join(CACHE, "last_game_version.txt")

def game_version(install):
    with zipfile.ZipFile(os.path.join(install, "pack", "locale.zip")) as z:
        return json.loads(z.read("en/version"))["version"]

def extract_en(install, dest):
    os.makedirs(dest, exist_ok=True)
    with zipfile.ZipFile(os.path.join(install, "pack", "locale.zip")) as z:
        for n in z.namelist():
            if n.startswith("en/") and n.endswith(".json") and not n.endswith("/"):
                p = os.path.join(dest, n[len("en/"):])
                os.makedirs(os.path.dirname(p), exist_ok=True)
                open(p, "wb").write(z.read(n))

def diff_lexicon(old_f, new_f):
    """返回 (unchanged, changed, added, removed) 的 key 集合。"""
    o = json.load(open(old_f, encoding="utf-8"))
    n = json.load(open(new_f, encoding="utf-8"))
    ok = {k for k in n if k in o and o[k] == n[k]}
    ch = {k for k in n if k in o and o[k] != n[k]}
    ad = {k for k in n if k not in o}
    rm = {k for k in o if k not in n}
    return ok, ch, ad, rm

def main():
    install = patch_tool.find_install_dir()
    assert install and os.path.isfile(os.path.join(install, "pack", "locale.zip"))
    gv  = game_version(install)
    zhex = zhsync.sha256_file(os.path.join(install, "pack", "locale.zip"))

    # —— 闸门：上游无变化则跳过 ——
    if (os.path.isfile(LAST_ZIP) and open(LAST_ZIP).read() == zhex
            and os.path.isfile(LAST_VER) and open(LAST_VER).read() == str(gv)):
        print("上游无变化，跳过"); return

    new_en = os.path.join(CACHE, "en_new"); extract_en(install, new_en)
    zh   = resource_zh_dir()                       # 当前已发布 zh 包 = 搬运来源
    out  = os.path.join(CACHE, "zh_out")
    shutil.rmtree(out, ignore_errors=True); os.makedirs(out)

    for name in ("words", "UI", "nodes", "junctions"):
        old_en_f = os.path.join(BASE_EN, name + ".json")
        new_en_f = os.path.join(new_en, name + ".json")
        old_zh_f = os.path.join(zh, name + ".json")
        old_zh = json.load(open(old_zh_f, encoding="utf-8")) if os.path.isfile(old_zh_f) else {}
        if os.path.isfile(old_en_f):
            ok, ch, ad, _rm = diff_lexicon(old_en_f, new_en_f)
        else:
            ok, ch, ad = set(), set(), set(json.load(open(new_en_f)))   # 首次：全当新增
        new = {}
        for k in ok: new[k] = old_zh.get(k, "")
        for k in ch: new[k] = "TODO:" + old_zh.get(k, "")     # 变值 → 标 TODO 待人工
        draft = translate_lexicons({k: load_new(new_en_f, k) for k in ad})
        for k in ad: new[k] = draft.get(k, "TODO")            # 新增 → 引擎草稿
        write_json(os.path.join(out, name + ".json"), new)    # 删除的 key 自然丢弃

    # 非词库内容原样搬运（绝不能重翻/重生成，否则丢字体、丢示例）
    for keep in ("config.json", "fonts", "welcome", "notes"):
        src = os.path.join(zh, keep)
        if os.path.isdir(src): shutil.copytree(src, os.path.join(out, keep))
        elif os.path.isfile(src): shutil.copy2(src, os.path.join(out, keep))
    apply_locale_extras(out)                            # 注入手工维护的 LOCALE_ADD/LOCALE_OVERRIDE

    # 清单 + 版本（json 一律 newline="\n"，配合 .gitattributes 保证哈希稳定）
    ver = bump_version()                                # 见 §7 待确认
    man = zhsync.build_manifest(out, ver, game_version=gv)
    write_json(os.path.join(out, "manifest.json"), man)

    # 落盘基线 +（可选）提交 PR
    shutil.rmtree(BASE_EN, ignore_errors=True); shutil.copytree(new_en, BASE_EN)
    open(LAST_ZIP, "w").write(zhex); open(LAST_VER, "w").write(str(gv))
    if args.push:
        git_commit_and_open_pr(out)                    # 人审后合入
```

> 注：`write_json` 统一 `open(p, "w", encoding="utf-8", newline="\n")` + `json.dump(..., ensure_ascii=False, indent=1)`。

---

## 5. 三种落地形态

| 形态 | 触发点 | 能否读到游戏文件 | 复杂度 | 推荐度 |
|---|---|---|---|---|
| **A. 本地定时任务** | Windows 任务计划 / cron，定时跑 `sync_upstream.py` | ✅ 本机就装着游戏 | 低 | ⭐⭐⭐ 推荐起步 |
| **B. 常驻守护进程** | 后台常驻，监听 `pack/locale.zip` 改动即跑 | ✅ 同 A，但无需等排程 | 中（要处理崩溃/单次重复） | ⭐⭐ 适合电脑常开 |
| **C. GitHub Actions 自托管** | Actions 定时触发，自托管 runner 执行 | ⚠️ 仅当 runner 机器装有游戏/能 steamcmd 拉 depot | 高（凭证、EULA、付费游戏下载） | ⭐ 除非已有 runner |

**关键现实**：真正的云端 CI 很难拿到这份闭源游戏文件（需登录、接受 EULA、且是付费 app）。
所以**检测 + 提取**这一步天然落在「拥有游戏的维护者机器」上；只有**发布**（commit / PR / Release）
走 GitHub。形态 A 最务实，B/C 是 A 的变体。

---

## 6. 已知坑与对策

1. **key 同名但 en 值变了** → 旧译文可能语义过时。对策：第 4 步只搬「值完全相等」的条目，
   变值条目一律标 `TODO` 交人工，绝不强搬。
2. **`translate_core` 的手工 extras**（`LOCALE_ADD` / `LOCALE_OVERRIDE`，补的是 en 里根本没登记、任何语言包都覆盖不到的键）
   不来自 en diff，自动 `apply_locale_extras` 即可，无需参与 diff。
3. **不要重翻 `config.json` / `fonts/` / `welcome/` / `notes/`**：这些从上一版 `zh` 原样拷贝。
   重生成会丢字体（11 MB 中文字体）或丢已汉化的入门指南示例。
4. **清单哈希依赖 `.gitattributes` 统一换行**（v1.2.x 已修好）。脚本写 json 一律 `newline="\n"`，
   不依赖运行平台默认换行，避免 CRLF/LF 导致 sha256 对不上、`② 同步` 每次重下整包。
5. **welcome 是二进制 `.pxc`**，文本嵌在 `Node_Display_Text` / `Node_Slideshow` 节点里，
   不在初版自动范围（见 §7）。初版若重生成 `zh/`，务必把现有 `welcome/` 原样搬过去，别清空。

---

## 7. 范围边界（实测修正版）

> **【实测修正】** 直接解包装机的 `pack/locale.zip` 验证过：`en/` 里**只有 7 个文件** —
> `words.json`、`nodes.json`、`junctions.json`、`config.json`、`notes/*.md`（3 个）。
> **没有 `en/UI.json`**。UI 面板与对话框词条不在官方语言包里（历史做法是另从
> `data.win` 提取成 `ref/UI_en_*.json` 再生成），所以 **`zh/UI.json` 无法自动跟随上游同步**，
> 必须单独维护。这一点修正了初版方案里"words/UI/nodes/junctions 四个词库都能自动 diff"的说法。

- **能自动同步**：`words.json`、`nodes.json`（脚本当前处理的两个）；`junctions.json` /
  `config.json` / `notes/*.md` 也已随 `en/` 解出，暂未纳入改写（留作后续）。
- **无法自动同步**：`UI.json`（上游语言包里没有对应基准）。
- **不参与改写**：`fonts/`（11 MB 中文字体）、`welcome/`（`.pxc` 二进制教程容器）——
  同步脚本不会清空或重生成它们，只沿用既有汉化成果。
- **待办清单机制**：不管上游怎么变，翻不出来的条目走英文回退 + `build/todo_report.md`，
  不会出现带 "TODO" 字串的界面文本。

---

## 8. 怎么用 Usage

```bat
rem 一次性看看上游有没有新东西（不写 zh/、不推送）
python build\sync_upstream.py --dry-run

rem 同步到本地仓库（写 zh/ 与 manifest，不推送）
python build\sync_upstream.py

rem 同步并直推 main
python build\sync_upstream.py --push

rem 注册每月定时任务（默认每月 1 号 09:00）
powershell -ExecutionPolicy Bypass -File build\install_sync_task.ps1
rem 可执行文件位置可在 run_sync.bat 里改 PYTHON；日志落在 build\_sync_logs\sync.log
```

**周报流程 / Weekly loop**：任务触发 → 脚本比对上游 → 有变化就补翻、写包、写清单、直接推 `main`
→ `build/todo_report.md` 更新 → 你打开它看过一遍，把要永久修的加进
`translate_core.LOCALE_OVERRIDE` 即可（下一次同步自动继承，不会被引擎冲掉）。

## 9. 已完成的验证 Verification done

| 验证项 | 结果 |
|---|---|
| `--dry-run` 在真实安装上运行 | 正确定位安装/数据目录；上下游版本一致（122000）→ 判定「无需更新」；`zh/` 零改动 |
| 基线建立（解决首次运行死锁） | 修掉了"首次无基线直接早退、导致基线永远建不起来"的缺陷；现在首次即建立快照 |
| 模拟「官方改了措辞」 | 篡改基线 3 个 key → 正确检出 2 条报入待办清单（第 3 个 `2d` 属 `KEEP_KEYS`，被正确排除） |
| `plan_version` 单元行为 | 无变化→不 bump；内容变→`1.2.0→1.2.1`；上游推进→`1.2.0→1.2.1` 且日志写明原因；`1.2.9→1.2.10` 进位正确；`--version` 覆盖生效 |
| `diff_changed` / `is_untranslated` | 只报值有变化的 key（新增由另一条路径处理）；未译判定（英文回退）符合预期 |
| 推送凭据 | `read_token()` 能从 `~/.git-credentials` 读到 40 位 PAT；**未做任何实际 push** |

> 本次所有改动都**未提交、未推送**。要入库时再执行 commit/push。
