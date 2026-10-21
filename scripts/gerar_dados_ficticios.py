#!/usr/bin/env python3
"""
gerar_dados_ficticios.py · v0.1.0
=================================
Gera tabelas FICTÍCIAS no mesmo formato que ybyra_estatisticas_gee.py exporta do GEE
(uma linha por município × bioma × ano, colunas zona, ano, area_ha e as bandas), para
desenvolver a plataforma antes de os dados reais existirem.

Os números imitam a ordem de grandeza e os padrões gerais esperados (arco do
desmatamento, picos de fogo em anos secos, remoção crescente em secundárias), mas
NÃO representam nenhum resultado do modelo YbYrá-BR.

Uso: python gerar_dados_ficticios.py <web/geo/municipios.geojson> <repo-queimadas> <saida_csv> <saida_nomes>

Histórico de versões
  0.1.0 (2026-10-21) — versão inicial.
"""
import collections, json, math, sys
from pathlib import Path

import numpy as np
import pandas as pd

VERSAO = "0.1.0"
MUN, RAIZ, SAIDA, NOMES = map(Path, sys.argv[1:5])
SAIDA.mkdir(parents=True, exist_ok=True); NOMES.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(401741)  # processo CNPq, só como semente
ANOS = list(range(2001, 2025))
BIOMA_COD = {"Amazônia": 1, "Caatinga": 2, "Cerrado": 3, "Mata Atlântica": 4, "Pampa": 5, "Pantanal": 6}
NOME_BIOMA = {v: k for k, v in BIOMA_COD.items()}

# ---------------- municípios: área e partição por bioma ----------------
g = json.load(open(MUN))["features"]
def area_ha(geom):
    a = 0.0
    for poly in (geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]):
        for k, r in enumerate(poly):
            lat = math.radians(sum(y for _, y in r) / len(r))
            s = abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(r, r[1:]))) / 2
            a += (1 if k == 0 else -1) * s * (111.32 ** 2) * math.cos(lat) * 100
    return max(a, 100.0)

mun = pd.DataFrame([{"cod": f["properties"]["c"], "nome": f["properties"]["n"], "uf": f["properties"]["u"],
                     "b": f["properties"]["b"], "area": area_ha(f["geometry"]),
                     "lon": np.mean([x for poly in (f["geometry"]["coordinates"] if f["geometry"]["type"] == "MultiPolygon" else [f["geometry"]["coordinates"]]) for x, _ in poly[0]]),
                     "lat": np.mean([y for poly in (f["geometry"]["coordinates"] if f["geometry"]["type"] == "MultiPolygon" else [f["geometry"]["coordinates"]]) for _, y in poly[0]])}
                    for f in g])
cont = pd.read_csv(RAIZ / "data/bioma_municipio.csv")
cont["b"] = cont["bioma"].map(BIOMA_COD)
partes = []
for cod, d in cont.groupby("cod_ibge"):
    tot = d["n"].sum()
    for _, r in d.iterrows():
        if r["n"] / tot >= 0.03:
            partes.append((cod, int(r["b"]), r["n"] / tot))
pt = pd.DataFrame(partes, columns=["cod", "b", "frac"])
pt["frac"] = pt["frac"] / pt.groupby("cod")["frac"].transform("sum")
sem = mun.loc[~mun["cod"].isin(pt["cod"]), ["cod", "b"]].assign(frac=1.0)
pt = pd.concat([pt, sem], ignore_index=True)
z = pt.merge(mun.drop(columns="b"), on="cod")
z["area_ha"] = z["area"] * z["frac"]
z["zona"] = z["cod"] * 10 + z["b"]
n = len(z)

# ---------------- pesos espaciais (fictícios) ----------------
floresta = z["b"].map({1: .85, 2: .45, 3: .45, 4: .25, 5: .20, 6: .40}).to_numpy()
densidade = z["b"].map({1: 120, 2: 15, 3: 25, 4: 60, 5: 10, 6: 30}).to_numpy()   # Mg C ha⁻¹
secund = z["b"].map({1: .07, 2: .04, 3: .06, 4: .10, 5: .03, 6: .04}).to_numpy()
fogo_b = z["b"].map({1: 1.0, 2: .3, 3: 1.6, 4: .15, 5: .05, 6: 2.2}).to_numpy()
lat, lon, A = z["lat"].to_numpy(), z["lon"].to_numpy(), z["area_ha"].to_numpy()
arco = np.exp(-((lat + 8.5) / 3.5) ** 2) * (lon > -68) * (z["b"].to_numpy() == 1)
matopiba = np.exp(-((lat + 9) / 3) ** 2 - ((lon + 46) / 3) ** 2) * (z["b"].to_numpy() == 3)
pressao = 0.05 + 3.0 * arco + 1.2 * matopiba + 0.2 * (z["b"].to_numpy() == 3)
ruido = lambda s: rng.lognormal(0, s, n)
w = {
    "defor_co2": A * floresta * densidade * pressao * ruido(1.0),
    "fire_co2": A * floresta * fogo_b * (0.3 + pressao) * ruido(0.9),
    "logging_co2": A * floresta * arco * ((lat > -14) & (lat < -2)) * ruido(1.1),
    "defor_sf_co2": A * secund * (0.2 + pressao) ** .7 * ruido(0.8),
    "removal_sf_co2": A * secund * ruido(0.5),
}
w["edge_co2"] = (w["defor_co2"] + 1) ** .7 * A ** .3 * floresta * ruido(0.5)

# ---------------- totais nacionais por ano (Mg CO₂ ano⁻¹; fictícios) ----------------
T = {
    "defor_co2": [700, 800, 900, 950, 750, 550, 450, 480, 300, 280, 250, 200, 230, 220, 260, 300, 280, 300, 400, 420, 480, 470, 350, 300],
    "fire_co2": [150] * 24,
    "edge_co2": list(np.linspace(80, 135, 24)),
    "logging_co2": list(np.linspace(65, 38, 24)),
    "defor_sf_co2": list(np.linspace(95, 150, 24)),
    "removal_sf_co2": list(-np.linspace(85, 170, 24)),
}
for a, f in {2005: 2.4, 2007: 1.8, 2010: 2.6, 2015: 2.2, 2016: 1.5, 2017: 1.4, 2019: 1.6, 2020: 2.5, 2024: 2.8}.items():
    T["fire_co2"][ANOS.index(a)] *= f
T = {k: np.array(v) * 1e6 for k, v in T.items()}
pant = (z["b"].to_numpy() == 6)

linhas = []
estoque_sf = A * secund * 55 * 44 / 12 * ruido(0.3)       # Mg CO₂ na secundária em 2001
perda_acum = np.zeros(n)
for k, ano in enumerate(ANOS):
    d = {"zona": z["zona"].to_numpy(), "ano": ano, "area_ha": A}
    for v, peso in w.items():
        p = peso * rng.lognormal(0, 0.35, n)
        if v == "fire_co2" and ano in (2020, 2024):
            p = p * np.where(pant, 6.0, 1.0)
        d[v] = T[v][k] * p / p.sum()
    d["total_primary_co2"] = d["edge_co2"] + d["fire_co2"] + d["defor_co2"] + d["logging_co2"]
    estoque_sf = estoque_sf * 1.02 - d["removal_sf_co2"] - d["defor_sf_co2"] * 0.9
    estoque_sf = np.maximum(estoque_sf, 0)
    d["agc_sf_co2"] = estoque_sf
    d["agc_sf_mgc"] = estoque_sf * 12 / 44
    perda_acum += d["defor_co2"] * 12 / 44
    d["agc0_mgc"] = np.maximum(A * floresta * densidade - perda_acum, 0)
    linhas.append(pd.DataFrame(d))
    pd.DataFrame(d).to_csv(SAIDA / f"ybyra_v1_2_municipio_bioma_{ano}.csv", index=False)

# nomes para o catálogo
mun[["cod", "nome", "uf"]].assign(nome=lambda x: x["nome"] + " (" + x["uf"] + ")").rename(
    columns={"cod": "id"})[["id", "nome"]].to_csv(NOMES / "municipio.csv", index=False)
zz = z[["zona", "nome", "uf", "b"]].copy()
zz["nome"] = zz["nome"] + " (" + zz["uf"] + ") · " + zz["b"].map(NOME_BIOMA)
zz.rename(columns={"zona": "id"})[["id", "nome"]].to_csv(NOMES / "municipio_bioma.csv", index=False)

tot = pd.concat(linhas).groupby("ano")[["defor_co2", "fire_co2", "total_primary_co2", "removal_sf_co2"]].sum() / 1e6
print(f"gerar_dados_ficticios v{VERSAO}: {n} zonas município × bioma, {len(ANOS)} anos")
print(tot.round(0).iloc[[0, 3, 11, 19, 23]])
