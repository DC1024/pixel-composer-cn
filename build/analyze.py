# -*- coding: utf-8 -*-
"""分析未翻译项里的高频未知英文词，指导扩充 WORD 词典"""
import json, os, re, sys
from collections import Counter
B = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, B)
from translate_core import WORD, KEEP, translate

def load(p):
    with open(p, "r", encoding="utf-8") as f:
        text = f.read()
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

en_words = load(os.path.join(B, 'en_words.json'))
zh_seed = load(os.path.join(B, 'zh_words_seed.json'))
en_nodes = load(os.path.join(B, 'en_nodes.json'))

def is_unt(zh, en):
    if zh is None or zh == en: return True
    return not re.search(r'[一-鿿]', zh)

# words 高频未知词
miss = Counter()
for k, ev in en_words.items():
    if k in zh_seed: continue
    if is_unt(translate(ev), ev):
        for w in re.findall(r"[A-Za-z][A-Za-z]+", ev):
            if w.lower() not in WORD and w.lower() not in KEEP:
                miss[w.lower()] += 1
print("=== 未译 words 高频未知词 (top 80) ===")
for w, c in miss.most_common(80):
    print(f"{c:4} {w}")

# 节点参数名未知词
miss2 = Counter()
for nid, nd in en_nodes.items():
    for arr in ('inputs', 'outputs'):
        for p in nd.get(arr, []):
            nm = p.get('name', '')
            if is_unt(translate(nm), nm):
                for w in re.findall(r"[A-Za-z][A-Za-z]+", nm):
                    if w.lower() not in WORD and w.lower() not in KEEP:
                        miss2[w.lower()] += 1
print("\n=== 未译 节点参数名 高频未知词 (top 80) ===")
for w, c in miss2.most_common(80):
    print(f"{c:4} {w}")
