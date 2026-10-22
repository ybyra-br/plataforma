#!/usr/bin/env python3
"""
gerar_ficticios_extras.py · v0.1.0
==================================
Gera tabelas FICTÍCIAS dos recortes extras (terras indígenas, unidades de conservação, quilombos,
Amazônia Legal, MATOPIBA, bacias níveis 1 e 2) no formato do export do GEE, com os ids e as áreas
das malhas reais (shapefiles do GEE), para testar a plataforma antes dos dados do modelo.
Os valores NÃO representam resultados do modelo YbYrá-BR.

Uso: python gerar_ficticios_extras.py <pasta_shapefiles> <saida (dados/brutos/v1_2)>

Histórico de versões
  0.1.0 (2026-10-22) — versão inicial.
"""
import csv
import gzip
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ler_shp import ler, area_assinada  # noqa: E402

PASTA, SAIDA = Path(sys.argv[1]), Path(sys.argv[2])
ANOS = list(range(2001, 2025))
RECORTES = ["terra_indigena", "unidade_conservacao", "territorio_quilombola", "amazonia_legal",
            "matopiba", "bacia_nivel1", "bacia_nivel2"]
COLS = ["area_ha", "defor_co2", "fire_co2", "logging_co2", "defor_sf_co2", "removal_sf_co2", "edge_co2",
        "total_primary_co2", "agc_sf_co2", "agc_sf_mgc", "agc0_mgc"]
# intensidade nacional fictícia por ano (Mg CO2 ha-1 ano-1), mesmo desenho de gerar_dados_ficticios.py
DEFOR = np.array([700, 800, 900, 950, 750, 550, 450, 480, 300, 280, 250, 200, 230, 220, 260, 300, 280, 300,
                  400, 420, 480, 470, 350, 300]) * 1e6 / 851e6
FOGO = np.full(24, 150e6 / 851e6)
for a, f in {2005: 2.4, 2007: 1.8, 2010: 2.6, 2015: 2.2, 2016: 1.5, 2017: 1.4, 2019: 1.6, 2020: 2.5, 2024: 2.8}.items():
    FOGO[ANOS.index(a)] *= f
BORDA = np.linspace(80, 135, 24) * 1e6 / 851e6
MADEIRA = np.linspace(65, 38, 24) * 1e6 / 851e6
DSEC = np.linspace(95, 150, 24) * 1e6 / 851e6
REM = -np.linspace(85, 170, 24) * 1e6 / 851e6
# proteção: áreas protegidas emitem menos que a média (fictício)
FATOR = {"terra_indigena": 0.25, "unidade_conservacao": 0.4, "territorio_quilombola": 0.6}


def area_ha(polis):
    a = 0.0
    for pol in polis:
        for k, r in enumerate(pol):
            lat = math.radians(float(r[:, 1].mean()))
            s = abs(area_assinada(r)) * (111.32 ** 2) * math.cos(lat) * 100
            a += s if k == 0 else -s
    return max(a, 1.0)


rng = np.random.default_rng(401741)
SAIDA.mkdir(parents=True, exist_ok=True)
for rec in RECORTES:
    fs = ler(PASTA / f"ybyra_geometria_{rec}")
    linhas = []
    for attrs, polis in fs:
        if not polis:
            continue
        i = int(attrs["id"])
        A = area_ha(polis)
        lat = float(np.mean([r[:, 1].mean() for pol in polis for r in pol]))
        arco = math.exp(-((lat + 8.5) / 4.0) ** 2)
        f = FATOR.get(rec, 1.0) * (0.4 + 2.0 * arco) * rng.lognormal(0, 0.8)
        floresta = 0.85 if lat > -15 else 0.4
        estoque_sf = A * 0.06 * 55 * 44 / 12 * rng.lognormal(0, 0.3)
        perda = 0.0
        for k, ano in enumerate(ANOS):
            ru = lambda s=0.35: rng.lognormal(0, s)  # noqa: E731
            d = {"defor_co2": A * DEFOR[k] * f * ru(), "fire_co2": A * FOGO[k] * f * ru(0.6),
                 "logging_co2": A * MADEIRA[k] * f * arco * ru(), "defor_sf_co2": A * DSEC[k] * f * ru(),
                 "removal_sf_co2": A * REM[k] * ru(0.2), "edge_co2": A * BORDA[k] * f * ru()}
            d["total_primary_co2"] = d["defor_co2"] + d["fire_co2"] + d["logging_co2"] + d["edge_co2"]
            estoque_sf = max(estoque_sf * 1.02 - d["removal_sf_co2"] - 0.9 * d["defor_sf_co2"], 0)
            perda += d["defor_co2"] * 12 / 44
            d["agc_sf_co2"] = estoque_sf
            d["agc_sf_mgc"] = estoque_sf * 12 / 44
            d["agc0_mgc"] = max(A * floresta * 120 - perda, 0)
            d["area_ha"] = A
            linhas.append([i, ano] + [round(d[c], 3) for c in COLS])
    caminho = SAIDA / f"ybyra_v1_2_{rec}_{ANOS[0]}-{ANOS[-1]}.csv.gz"
    with gzip.open(caminho, "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["zona", "ano"] + COLS)
        w.writerows(linhas)
    print(f"{rec}: {len(fs)} feições → {caminho.name} ({caminho.stat().st_size / 1e6:.1f} MB)")
