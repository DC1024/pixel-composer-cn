#!/usr/bin/env bash
# ==============================================================================
#  Pixel Composer 汉化工具 · Linux 一键脚本
#  仓库：https://github.com/DC1024/pixel-composer-cn
#
#  用法：
#     ./install.sh                    打开图形界面（没装 tkinter 时自动转命令行）
#     ./install.sh gui                同上
#     ./install.sh install            一键汉化（默认全部区域）
#     ./install.sh install --modules words,ui         只汉化「界面词条 + 面板与对话框」
#     ./install.sh sync               从 GitHub 同步维护者已翻好的最新汉化包
#     ./install.sh restore            恢复英文（含入门指南示例还原）
#     ./install.sh rollback           还原上一版汉化
#     ./install.sh status             查看状态（平台 / 安装目录 / 数据目录 / 包版本 / 汉化区域）
#     ./install.sh layouts            汉化工作区标签（连 pack/layouts.zip 一起改名）
#     ./install.sh layouts-restore    还原布局名
#     ./install.sh modules            列出可选汉化区域
#     ./install.sh leftovers          旧社区汉化包残留清点（只列出，不删除）
#     ./install.sh deps               查看本机还缺什么依赖（例如 tkinter 怎么装）
#
#  可选环境变量：
#     PIXELCOMPOSER_DIR=/path/to/Pixel\ Composer     手动指定游戏安装目录
#     STEAM_ROOT=/path/to/Steam                       手动指定 Steam 根目录
#
#  说明：本脚本只是个薄封装，真正干活的是同目录下的 patch_tool.py。
#       它只用 Python 标准库，不需要 pip install 任何东西。
# ==============================================================================
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL="$HERE/patch_tool.py"

# 强制 UTF-8，避免某些 SteamOS / 容器里 locale 是 POSIX 时中文打成乱码
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

if [ ! -f "$TOOL" ]; then
    echo "找不到 $TOOL —— 请把本脚本和 patch_tool.py 放在同一个目录里。" >&2
    exit 1
fi

# ---------- 找一个可用的 python3 (>= 3.7) ----------
find_python() {
    for c in python3 python; do
        if command -v "$c" >/dev/null 2>&1; then
            if "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 7) else 1)' 2>/dev/null; then
                command -v "$c"
                return 0
            fi
        fi
    done
    return 1
}

PY="$(find_python)" || {
    echo "未找到 Python 3.7+。" >&2
    echo "请先安装，例如：" >&2
    echo "  Debian/Ubuntu : sudo apt install python3" >&2
    echo "  Arch/Manjaro  : sudo pacman -S python" >&2
    echo "  Fedora        : sudo dnf install python3" >&2
    echo "  SteamOS/Deck  : python3 通常已自带；若缺少可在桌面模式的终端里用 pacman。" >&2
    exit 1
}

has_tk() { "$PY" -c 'import tkinter' >/dev/null 2>&1; }

# ---------- 依赖提示 ----------
deps() {
    echo "Python      : $PY（$("$PY" -c 'import sys;print(sys.version.split()[0])')）"
    if has_tk; then
        echo "tkinter     : 已安装 —— 可以用 ./install.sh 打开图形界面"
    else
        echo "tkinter     : 未安装 —— 会自动使用命令行界面（功能完全一样）"
        echo "              想用图形界面的话："
        echo "                Debian/Ubuntu : sudo apt install python3-tk"
        echo "                Arch/Manjaro  : sudo pacman -S tk"
        echo "                Fedora        : sudo dnf install python3-tkinter"
        echo "                openSUSE      : sudo zypper install python3-tk"
        echo "                SteamOS/Deck  : 系统根目录只读，装不上属正常，用命令行即可"
    fi
    if command -v zenity >/dev/null 2>&1; then
        echo "zenity      : 已安装（本脚本未依赖它）"
    fi
    echo
    echo "探测结果："
    PIXELCOMPOSER_DIR="${PIXELCOMPOSER_DIR:-}" "$PY" "$TOOL" status || true
}

usage() {
    sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'
}

cmd="${1:-gui}"
[ $# -gt 0 ] && shift

case "$cmd" in
    gui|"")
        if has_tk; then
            exec "$PY" "$TOOL" "$@"
        else
            echo "未检测到 tkinter，改用命令行界面（功能一致）。"
            echo "想用图形界面请看：./install.sh deps"
            echo
            exec "$PY" "$TOOL" cli "$@"
        fi
        ;;
    install|update|sync|restore|rollback|status|layouts|layouts-restore|leftovers|cli)
        exec "$PY" "$TOOL" "$cmd" "$@"
        ;;
    modules|list-modules)
        exec "$PY" "$TOOL" --list-modules
        ;;
    version|--version|-V)
        exec "$PY" "$TOOL" --version
        ;;
    deps)
        deps
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        echo "未知命令：$cmd" >&2
        echo >&2
        usage >&2
        exit 2
        ;;
esac
