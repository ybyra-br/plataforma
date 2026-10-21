#!/usr/bin/env python3
"""
preparar_malhas.py · v0.1.1
Gera as geometrias do mapa da plataforma de emissões YbYrá-BR sem bibliotecas de geometria:
  web/geo/municipios.geojson  polígonos simplificados (c = código IBGE, n = nome, u = UF, b = bioma)
  web/geo/contornos.geojson   linhas de contorno de Brasil, UF e bioma
Os contornos saem da malha completa rasterizada (0,008°, PIL) e traçados como isolinha
da máscara de cada grupo (contourpy); depois são simplificados (Douglas-Peucker). Assim
não dependem de a malha ser perfeitamente topológica. Bioma = bioma predominante do município (provisório; trocar pela malha
IBGE de biomas quando os dados reais forem processados).

Histórico de versões
  0.1.1 (2026-10-21) — contornos por rasterização + isolinha (a malha não é 100% topológica).
  0.1.0 (2026-10-21) — versão inicial.
"""
import gzip, json, sys, collections
from pathlib import Path

RAIZ = Path(sys.argv[1])            # repositório da plataforma de queimadas (malha + bioma por município)
SAIDA = Path(sys.argv[2])            # pasta web/geo
TOL = 0.01                           # tolerância Douglas-Peucker (graus, ~1,1 km)
BIOMA_COD = {"Amazônia": 1, "Caatinga": 2, "Cerrado": 3, "Mata Atlântica": 4, "Pampa": 5, "Pantanal": 6}

# bioma predominante por município (contagem histórica por município × bioma)
cont = collections.defaultdict(dict)
for i, l in enumerate(open(RAIZ / "data/bioma_municipio.csv", encoding="utf-8")):
    if i == 0: continue
    c, b, n = l.strip().split(",")
    cont[int(c)][b] = int(n)
pred = {c: BIOMA_COD[max(d, key=d.get)] for c, d in cont.items()}

full = json.load(gzip.open(RAIZ / "malha/municipios_juncao.geojson.gz"))["features"]
uf_de = {f["properties"]["cod_ibge"]: f["properties"]["cod_ibge"] // 100000 for f in full}
# municípios sem registro: bioma mais comum da UF
por_uf = collections.defaultdict(collections.Counter)
for c, b in pred.items(): por_uf[c // 100000][b] += 1
for c in uf_de:
    if c not in pred: pred[c] = por_uf[c // 100000].most_common(1)[0][0]

import numpy as np
from PIL import Image, ImageDraw
import contourpy

RES = 0.008                           # grau por pixel do raster de rótulos (~0,9 km)
X0, Y1, X1, Y0 = -74.2, 5.4, -28.6, -33.9
W, H = int((X1 - X0) / RES) + 1, int((Y1 - Y0) / RES) + 1

def aneis_externos(g):
    for poly in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]):
        yield poly[0]

def area_aprox(f):
    a = 0.0
    for r in aneis_externos(f["geometry"]):
        a += abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(r, r[1:])))
    return a

def rasterizar():
    """Rótulo = índice do município + 1. Maiores primeiro: enclaves pequenos ficam por cima."""
    img = Image.new("I", (W, H), 0); dr = ImageDraw.Draw(img)
    ordem = sorted(range(len(full)), key=lambda i: -area_aprox(full[i]))
    for i in ordem:
        for r in aneis_externos(full[i]["geometry"]):
            dr.polygon([((x - X0) / RES, (Y1 - y) / RES) for x, y in r], fill=i + 1)
    return np.array(img, dtype=np.int32)

def contornos_grupo(rot, grupo_por_indice):
    """Contorno (nível 0,5) da máscara binária de cada grupo, recortada no envelope do grupo."""
    grp = grupo_por_indice[rot]            # 0 = fora do Brasil
    out = {}
    for gid in np.unique(grp):
        if gid == 0: continue
        ys, xs = np.nonzero(grp == gid)
        y0, y1, x0, x1 = max(ys.min() - 2, 0), min(ys.max() + 3, H), max(xs.min() - 2, 0), min(xs.max() + 3, W)
        m = (grp[y0:y1, x0:x1] == gid).astype(np.float32)
        gen = contourpy.contour_generator(z=m, line_type="Separate")
        linhas = []
        for ln in gen.lines(0.5):
            if len(ln) < 5: continue          # ilhotas menores que alguns pixels
            linhas.append([(X0 + (x0 + c) * RES, Y1 - (y0 + r) * RES) for c, r in ln])
        out[int(gid)] = linhas
    return out

def dp(pts, tol):
    """Douglas-Peucker iterativo."""
    if len(pts) < 3: return pts
    manter = [False] * len(pts); manter[0] = manter[-1] = True; pilha = [(0, len(pts) - 1)]
    while pilha:
        i, j = pilha.pop(); (x1, y1), (x2, y2) = pts[i], pts[j]; dx, dy = x2 - x1, y2 - y1
        L = (dx * dx + dy * dy) ** .5; dmax, k = 0, -1
        for m in range(i + 1, j):
            x, y = pts[m]
            d = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / L if L else ((x - x1) ** 2 + (y - y1) ** 2) ** .5
            if d > dmax: dmax, k = d, m
        if dmax > tol: manter[k] = True; pilha += [(i, k), (k, j)]
    return [p for p, s in zip(pts, manter) if s]


rot = rasterizar()
codigos = [f["properties"]["cod_ibge"] for f in full]
feats = []
for tipo, fn in [("brasil", lambda c: 1), ("uf", lambda c: c // 100000), ("bioma", lambda c: pred[c])]:
    lut = np.array([0] + [fn(c) for c in codigos], dtype=np.int32)
    for gid, linhas in contornos_grupo(rot, lut).items():
        ls = [[[round(x, 3), round(y, 3)] for x, y in dp(l, TOL)] for l in linhas]
        ls = [l for l in ls if len(l) > 1 and not (len(l) == 2 and l[0] == l[1])]
        feats.append({"type": "Feature", "properties": {"t": tipo, "id": gid},
                      "geometry": {"type": "MultiLineString", "coordinates": ls}})
        print(f"  contorno {tipo:6} {gid}: {len(ls)} linhas, {sum(map(len, ls))} vértices")
json.dump({"type": "FeatureCollection", "features": feats}, open(SAIDA / "contornos.geojson", "w"), separators=(",", ":"))

simp = json.load(open(RAIZ / "web/geo/municipios.geojson"))
for f in simp["features"]:
    p = f["properties"]; p["b"] = pred.get(p["c"], 0)
json.dump(simp, open(SAIDA / "municipios.geojson", "w"), ensure_ascii=False, separators=(",", ":"))
json.dump({str(c): b for c, b in pred.items()}, open(SAIDA.parent.parent / "dados_ficticios/bioma_predominante.json", "w"))
print("ok", (SAIDA / "contornos.geojson").stat().st_size // 1024, "KB contornos;", (SAIDA / "municipios.geojson").stat().st_size // 1024, "KB municípios")
