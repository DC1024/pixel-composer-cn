# -*- coding: utf-8 -*-
"""生成完整 zh 汉化包：en 基准 + 人工种子 + 翻译引擎补全缺口"""
import json, os, shutil, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from translate_core import translate, PHRASE

B = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(os.path.dirname(B), "dist", "zh")
os.makedirs(DIST, exist_ok=True)
os.makedirs(os.path.join(DIST, "fonts"), exist_ok=True)
os.makedirs(os.path.join(DIST, "notes"), exist_ok=True)

def load(p):
    with open(p, "r", encoding="utf-8") as f:
        text = f.read()
    # 容忍社区文件中的 // 注释与尾逗号（非标准 JSON）
    out = []
    i, n, in_str, esc = 0, len(text), False, False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if esc: esc = False
            elif c == '\\': esc = True
            elif c == '"': in_str = False
            i += 1; continue
        if c == '"':
            in_str = True; out.append(c); i += 1; continue
        if c == '/' and i + 1 < n and text[i+1] == '/':
            while i < n and text[i] != '\n': i += 1
            continue
        out.append(c); i += 1
    text = ''.join(out)
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    return json.loads(text)

en_words = load(os.path.join(B, "en_words.json"))
zh_words_seed = load(os.path.join(B, "zh_words_seed.json"))
en_nodes = load(os.path.join(B, "en_nodes.json"))
zh_nodes_seed = load(os.path.join(B, "zh_nodes_seed.json"))
en_junc = load(os.path.join(B, "en_junctions.json"))
ui_en = load(os.path.join(B, "ref_UI_en.json") if os.path.exists(os.path.join(B,"ref_UI_en.json")) else os.path.join(os.path.dirname(B),"ref","UI_en_1.18.0.4.json"))

# 从种子重叠构建 英文值->中文值 复用表
val_dict = {}
for k, zv in zh_words_seed.items():
    ev = en_words.get(k)
    if ev:
        val_dict[ev] = zv

def is_untranslated(zh, en):
    if zh is None: return True
    if zh == en: return True
    # 若结果里仍含大量连续英文字母且无汉字，视为未译
    if re.search(r"[一-鿿]", zh): return False
    return True

import re

# ---------------- words.json ----------------
words_out = {}
unt_words = 0; tot_words = 0
for k, ev in en_words.items():
    tot_words += 1
    if k in zh_words_seed:
        words_out[k] = zh_words_seed[k]
        continue
    if ev in val_dict:
        words_out[k] = val_dict[ev]
        continue
    zh = translate(ev)
    words_out[k] = zh
    if is_untranslated(zh, ev):
        unt_words += 1

# ---------------- nodes.json ----------------
def tr_param(p):
    o = {}
    if "name" in p: o["name"] = translate(p["name"])
    if "tooltip" in p and p["tooltip"]:
        o["tooltip"] = translate(p["tooltip"])
    if "display_data" in p:
        o["display_data"] = [translate(x) if isinstance(x, str) else x for x in p["display_data"]]
    return o

def tr_node(en_node):
    out = {}
    if "name" in en_node: out["name"] = translate(en_node["name"])
    if "tooltip" in en_node:
        out["tooltip"] = translate(en_node["tooltip"]) if en_node["tooltip"] else en_node["tooltip"]
    if "inputs" in en_node:
        out["inputs"] = [tr_param(p) for p in en_node["inputs"]]
    if "outputs" in en_node:
        out["outputs"] = [tr_param(p) for p in en_node["outputs"]]
    return out

nodes_out = {}
tot_nodes = len(en_nodes); unt_node_names = 0; tot_params = 0; unt_params = 0
for nid, en_node in en_nodes.items():
    if nid in zh_nodes_seed and isinstance(zh_nodes_seed[nid], dict):
        # 优先用人工种子（已翻译）；但补全种子缺失的字段
        seed = dict(zh_nodes_seed[nid])
        en = en_node
        for fld in ("name", "tooltip"):
            if fld not in seed and fld in en and en[fld]:
                seed[fld] = translate(en[fld]) if isinstance(en[fld], str) else en[fld]
        for arr in ("inputs", "outputs"):
            if arr in en:
                seed_arr = seed.get(arr, [])
                # 按 index 对齐补全
                new_arr = []
                for i, ep in enumerate(en[arr]):
                    if i < len(seed_arr) and isinstance(seed_arr[i], dict) and seed_arr[i].get("name"):
                        new_arr.append(seed_arr[i])
                    else:
                        new_arr.append(tr_param(ep))
                seed[arr] = new_arr
        nodes_out[nid] = seed
    else:
        nodes_out[nid] = tr_node(en_node)
    # 统计
    nd = nodes_out[nid]
    nm = nd.get("name")
    if is_untranslated(nm, en_node.get("name","")): unt_node_names += 1
    for arr in ("inputs","outputs"):
        for p in nd.get(arr, []):
            tot_params += 1
            if is_untranslated(p.get("name"),""): unt_params += 1

# ---------------- UI.json ----------------
ui_out = {}
unt_ui = 0; tot_ui = 0
for k, ev in ui_en.items():
    if k == "": continue
    tot_ui += 1
    zh = translate(ev)
    ui_out[k] = zh
    if is_untranslated(zh, ev):
        unt_ui += 1

# ---------------- junctions.json ----------------
# 值为笔记文件名引用，直接沿用 en 结构（笔记文件名保持一致）
junc_out = en_junc

# ---------------- config.json ----------------
config_out = {"per_character_line_break": True}

# ---------------- 写出 ----------------
def dump(name, obj):
    with open(os.path.join(DIST, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)

dump("words.json", words_out)
dump("nodes.json", nodes_out)
dump("UI.json", ui_out)
dump("junctions.json", junc_out)
dump("config.json", config_out)

# fonts
src_fonts = os.path.join(B, "fonts_seed")
if os.path.isdir(src_fonts):
    for fn in os.listdir(src_fonts):
        shutil.copy(os.path.join(src_fonts, fn), os.path.join(DIST, "fonts", fn))

# ---------------- 覆盖率报告 ----------------
def pct(a, b): return f"{100.0*a/b:.1f}%" if b else "n/a"
print("=== 生成完成 ===")
print(f"words.json : {len(words_out)} 条 | 未译(回退英文) {unt_words} | 覆盖率 {pct(tot_words-unt_words, tot_words)}")
print(f"nodes.json : {len(nodes_out)} 节点 | 节点名未译 {unt_node_names} | 参数名总数 {tot_params} 未译 {unt_params}")
print(f"UI.json    : {tot_ui} 条 | 未译 {unt_ui} | 覆盖率 {pct(tot_ui-unt_ui, tot_ui)}")
print(f"junctions  : {len(junc_out)} 条")
print(f"输出目录   : {DIST}")
