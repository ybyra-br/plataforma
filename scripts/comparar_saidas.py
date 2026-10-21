#!/usr/bin/env python3
"""comparar_saidas.py · v0.1.0 — confere se duas pastas de saída (R e Python) têm os mesmos
recortes, nomes e valores (tolerância de arredondamento). Uso: comparar_saidas.py <dir_a> <dir_b>"""
import json, sys
from pathlib import Path
A, B = Path(sys.argv[1]), Path(sys.argv[2])
erros = 0
def igual(x, y, onde):
    global erros
    if isinstance(x, (int, float)) and isinstance(y, (int, float)):
        if abs(x - y) > max(0.011, 1e-9 * max(abs(x), abs(y))):
            erros += 1
            if erros <= 20: print(f"  difere {onde}: {x} × {y}")
        return
    if isinstance(x, list) and isinstance(y, list):
        if len(x) != len(y):
            erros += 1; print(f"  tamanho difere {onde}: {len(x)} × {len(y)}"); return
        for k, (a, b) in enumerate(zip(x, y)): igual(a, b, f"{onde}[{k}]")
        return
    if isinstance(x, dict) and isinstance(y, dict):
        if set(x) != set(y):
            erros += 1; print(f"  chaves diferem {onde}: {sorted(set(x) ^ set(y))[:10]}"); return
        for k in x: igual(x[k], y[k], f"{onde}.{k}")
        return
    if x != y:
        erros += 1
        if erros <= 20: print(f"  difere {onde}: {x!r} × {y!r}")
ca, cb = json.load(open(A / "catalogo.json")), json.load(open(B / "catalogo.json"))
igual(ca["tipos"], cb["tipos"], "catalogo.tipos"); igual(ca["variaveis"], cb["variaveis"], "catalogo.variaveis")
fa = sorted(p.relative_to(A) for p in A.rglob("*.json")); fb = sorted(p.relative_to(B) for p in B.rglob("*.json"))
if fa != fb: erros += 1; print("  arquivos diferentes:", sorted(set(map(str, fa)) ^ set(map(str, fb)))[:10])
n = 0
for p in fa:
    if p.name == "catalogo.json" or not (B / p).exists(): continue
    igual(json.load(open(A / p)), json.load(open(B / p)), str(p)); n += 1
print(f"{n} arquivos comparados; {erros} diferenças")
sys.exit(1 if erros else 0)
