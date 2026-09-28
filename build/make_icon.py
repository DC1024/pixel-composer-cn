# -*- coding: utf-8 -*-
"""生成主题图标（配色取自 Pixel Composer 官方 default 主题 values.json）。
产出：仓库根目录 app_icon.ico 与 assets/logo.png
用法：python build/make_icon.py
"""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# —— Pixel Composer 官方调色板（Themes/default/values.json）——
BG      = "#1c1c23"   # main_bg
PANEL   = "#1e1e2c"   # main_mdblack
BORDER  = "#3b3b4e"   # main_dkgrey
ORANGE  = "#ff9166"   # orange（主强调色 _main_accent）
CYAN    = "#88ffe9"   # cyan
TEXT    = "#d6d6e8"   # main_white

FONT_PATH = os.path.join(ROOT, "zh", "fonts", "LXGWWenKaiMonoLite-Bold.ttf")


def rounded(size, radius, fill, outline=None, width=0):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius,
                        fill=fill, outline=outline, width=width)
    return img


def make(size):
    img = rounded(size, int(size * 0.22), PANEL, BORDER, max(2, size // 64))
    d = ImageDraw.Draw(img)
    # 中央「汉」字（橙色主强调）
    glyph = "汉"
    fs = int(size * 0.62)
    try:
        font = ImageFont.truetype(FONT_PATH, fs)
    except Exception:
        font = ImageFont.load_default()
    bbox = d.textbbox((0, 0), glyph, font=font)
    gw, gh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((size - gw) / 2 - bbox[0], (size - gh) / 2 - bbox[1] - size * 0.04),
           glyph, font=font, fill=ORANGE)
    # 底部主强调条（橙）+ 青色小点，呼应节点图配色
    bar_w, bar_h = int(size * 0.42), max(3, size // 40)
    bx = (size - bar_w) // 2
    by = int(size * 0.80)
    d.rounded_rectangle([bx, by, bx + bar_w, by + bar_h], radius=bar_h // 2, fill=ORANGE)
    r = max(3, size // 26)
    d.ellipse([size - r * 2 - int(size * 0.10), int(size * 0.10),
               size - int(size * 0.10), int(size * 0.10) + r * 2], fill=CYAN)
    return img


def main():
    base = make(256)
    ico = os.path.join(ROOT, "app_icon.ico")
    base.save(ico, sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                          (64, 64), (128, 128), (256, 256)])
    print("written", ico)
    assets = os.path.join(ROOT, "assets")
    os.makedirs(assets, exist_ok=True)
    png = os.path.join(assets, "logo.png")
    base.save(png)
    print("written", png)


if __name__ == "__main__":
    main()
