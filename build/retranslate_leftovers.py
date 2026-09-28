# -*- coding: utf-8 -*-
"""用改进后的引擎，仅重译 zh 包中仍残留英文的条目（不动已正确的中文）。
用法：python build/retranslate_leftovers.py
"""
import json, os, re, sys

B = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(B)
sys.path.insert(0, ROOT)
from translate_core import translate


def load(p):
    text = open(p, "r", encoding="utf-8").read()
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
        if c == '/' and i + 1 < n and text[i + 1] == '/':
            while i < n and text[i] != '\n': i += 1
            continue
        out.append(c); i += 1
    text = ''.join(out)
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    return json.loads(text)


LAT = re.compile(r'[A-Za-z]{2,}')


def fix_flat(path, en_map, label):
    d = json.load(open(path, encoding="utf-8"))
    changed = 0
    for k, v in list(d.items()):
        if not isinstance(v, str) or not LAT.search(v):
            continue
        ev = en_map.get(k)
        if not isinstance(ev, str) or not ev:
            continue
        nv = translate(ev)
        if nv and nv != v:
            d[k] = nv; changed += 1
    json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{label}: 重译 {changed} 条")
    return changed


def fix_nodes(path, en_nodes, label):
    d = json.load(open(path, encoding="utf-8"))
    nc = pc = tc = 0
    for nid, node in d.items():
        if not isinstance(node, dict): continue
        en = en_nodes.get(nid, {}) if isinstance(en_nodes.get(nid, {}), dict) else {}
        nm = node.get("name")
        if isinstance(nm, str) and LAT.search(nm) and isinstance(en.get("name"), str):
            t = translate(en["name"])
            if t and t != nm: node["name"] = t; nc += 1
        tp = node.get("tooltip")
        if isinstance(tp, str) and LAT.search(tp) and isinstance(en.get("tooltip"), str) and en.get("tooltip"):
            t = translate(en["tooltip"])
            if t and t != tp: node["tooltip"] = t; tc += 1
        for arr in ("inputs", "outputs"):
            arr_en = en.get(arr) or []
            for i, pp in enumerate(node.get(arr, []) or []):
                if not isinstance(pp, dict): continue
                enpp = arr_en[i] if i < len(arr_en) and isinstance(arr_en[i], dict) else {}
                n2 = pp.get("name")
                if isinstance(n2, str) and LAT.search(n2) and isinstance(enpp.get("name"), str):
                    t = translate(enpp["name"])
                    if t and t != n2: pp["name"] = t; pc += 1
    json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{label}: 节点名 {nc} / 提示 {tc} / 参数 {pc}")


en_words = load(os.path.join(B, "en_words.json"))
en_nodes = load(os.path.join(B, "en_nodes.json"))
ui_en = load(os.path.join(ROOT, "ref", "UI_en_1.18.0.4.json"))

fix_flat(os.path.join(ROOT, "zh", "words.json"), en_words, "words.json")
fix_flat(os.path.join(ROOT, "zh", "UI.json"), ui_en, "UI.json")
fix_nodes(os.path.join(ROOT, "zh", "nodes.json"), en_nodes, "nodes.json")
