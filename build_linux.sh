#!/usr/bin/env bash
# ==============================================================================
#  Pixel Composer 汉化工具 · Linux 发行包构建脚本
#
#  产出：PixelComposer-CN-Linux.tar.gz
#       解压后目录里就有 install.sh，用户最多三条命令即可用。
#
#  用法：
#     bash build_linux.sh              打包
#
#  说明：Linux 版是纯 Python 标准库实现，**不需要编译**，所以这里只是把
#       需要的文件挑出来、设好可执行位、压成一个 tar.gz。
#       11 MB 的中文字体也会打进包里 —— 这是「装完即可离线使用」的前提，
#       少了它中文会变成方块（除非用户先点一次「② 同步最新汉化」去下载）。
# ==============================================================================
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

NAME="PixelComposer-CN-Linux"
OUT="$HERE/$NAME.tar.gz"
STAGE="$HERE/.pkg/$NAME"

VERSION="$(sed -n 's/^VERSION = "\(.*\)"/\1/p' patch_tool.py | head -1)"
echo "============================================================"
echo " 构建 $NAME.tar.gz  （工具版本 v${VERSION:-?}）"
echo "============================================================"

# ---------- 必需文件 ----------
FILES=(
    install.sh
    patch_tool.py
    zhsync.py
    translate_core.py
    README.md
    LICENSE
)
for f in "${FILES[@]}"; do
    [ -f "$f" ] || { echo "[错误] 缺少 $f" >&2; exit 1; }
done

# ---------- 暂存 ----------
rm -rf "$HERE/.pkg"
mkdir -p "$STAGE"

for f in "${FILES[@]}"; do
    cp -p "$f" "$STAGE/"
done

# 汉化包：整目录带过去（含 welcome/ 教程与 fonts/ 字体）
mkdir -p "$STAGE/zh"
( cd zh && tar cf - . ) | ( cd "$STAGE/zh" && tar xf - )

# 清掉可能混进来的缓存
find "$STAGE" -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
find "$STAGE" -type f -name "*.pyc" -delete 2>/dev/null || true
find "$STAGE" -type f -name "Thumbs.db" -delete 2>/dev/null || true

# ---------- 换行与权限 ----------
# 文本统一 LF：Windows 工作区检出的是 CRLF，而 sha256 比对按原始字节，
# 带上 CR 会让「按区域同步」永远认为文件变了（详见 .gitattributes 的注释）。
LF_TARGETS=(install.sh patch_tool.py zhsync.py translate_core.py README.md LICENSE)
find "$STAGE/zh" -type f \( -name "*.json" -o -name "*.md" \) -print0 \
    | xargs -0 -r sed -i 's/\r$//'
for f in "${LF_TARGETS[@]}"; do
    [ -f "$STAGE/$f" ] && sed -i 's/\r$//' "$STAGE/$f"
done

chmod +x "$STAGE/install.sh"

# ---------- 打包 ----------
rm -f "$OUT"
( cd "$HERE/.pkg" && tar czf "$OUT" "$NAME" )
rm -rf "$HERE/.pkg"

echo
echo "文件数 / 体积："
tar tzf "$OUT" | wc -l
du -h "$OUT" | cut -f1

echo
echo "包内结构："
tar tzf "$OUT" | grep -v '/$' | sed 's|^|  |' | head -20
echo "  …（zh/ 共 $(tar tzf "$OUT" | grep -c "zh/") 项）"

echo
echo "============================================================"
echo " 完成：$OUT"
echo "============================================================"
echo "自测："
echo "  tar -xzf $NAME.tar.gz && cd $NAME && ./install.sh deps"
