#!/usr/bin/env python3
"""
ybyra_estatisticas_agregar.py · v0.2.0
======================================
Pós-processamento das tabelas exportadas por ybyra_estatisticas_gee.py:
soma as parciais da grade, deriva os recortes hierárquicos a partir da unidade
atômica município × bioma, confere a consistência e grava os arquivos estáticos
da plataforma (v1, sem servidor).

Entrada : pasta com os CSVs  ybyra_<modelo>_<recorte>_<ano>.csv  (baixados do Drive)
Saídas  : <saida>/estatisticas.parquet   tabela longa: tipo, id, ano, variavel, valor
          <saida>/serie/<tipo>/<lote>.json  séries de um lote de recortes (lote = UF para
                                           município e município × bioma; "0" nos demais)
          <saida>/mapa/<tipo>/<variavel>.json  valor de todos os recortes por ano (mapa coroplético;
                                           não gerado para município × bioma, que não tem mapa)
          <saida>/catalogo.json            tipos, ids, nomes, variáveis, anos, versões

Recortes derivados de município × bioma: brasil, uf, bioma, uf_bioma, municipio, municipio_bioma.

Uso:
  python ybyra_estatisticas_agregar.py --entrada csv/ --saida web/dados/v1_2 --modelo v1_2 \
      [--nomes nomes/]   # opcional: nomes/<tipo>.csv com colunas id,nome

Histórico de versões
  0.2.0 (2026-10-21) — séries em lotes por UF (de ~5,6 mil arquivos para dezenas) e números
                       compactos (inteiros acima de 100); sem mapa para município × bioma;
                       catálogo indica o lote de cada tipo.
  0.1.1 (2026-10-21) — unidade e natureza (fluxo/estoque) de cada variável no catálogo.
  0.1.0 (2026-10-21) — versão inicial.
"""
import argparse
import json
import re
from datetime import date
from pathlib import Path

import pandas as pd

VERSAO_SCRIPT = "0.2.0"
LOTE_POR_UF = {"municipio": lambda i: int(i) // 100000, "municipio_bioma": lambda i: int(i) // 1000000}
SEM_MAPA = {"municipio_bioma"}


def compacto(x):
    x = float(x)
    return int(round(x)) if abs(x) >= 100 else round(x, 2)


def unidade(v):
    """Unidade e natureza das variáveis exportadas por ybyra_estatisticas_gee.py (≥ v0.1.1)."""
    if v == "area_ha":
        return {"unidade": "ha", "natureza": "área"}
    if v == "agc_sf_co2":
        return {"unidade": "Mg CO₂", "natureza": "estoque"}
    if v.endswith("_mgc"):
        return {"unidade": "Mg C", "natureza": "estoque"}
    if v.endswith("_co2"):
        return {"unidade": "Mg CO₂ ano⁻¹", "natureza": "fluxo"}
    return {"unidade": "?", "natureza": "?"}
BIOMAS = {0: "Sem bioma", 1: "Amazônia", 2: "Caatinga", 3: "Cerrado",
          4: "Mata Atlântica", 5: "Pampa", 6: "Pantanal"}
UFS = {11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO", 21: "MA", 22: "PI",
       23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL", 28: "SE", 29: "BA", 31: "MG", 32: "ES",
       33: "RJ", 35: "SP", 41: "PR", 42: "SC", 43: "RS", 50: "MS", 51: "MT", 52: "GO", 53: "DF"}
PADRAO = re.compile(r"ybyra_(?P<modelo>[^_]+_[^_]+)_(?P<recorte>.+)_(?P<ano>\d{4})\.csv$")


def ler(entrada, modelo):
    tabelas = {}
    for arq in sorted(Path(entrada).glob("*.csv")):
        m = PADRAO.search(arq.name)
        if not m or m["modelo"] != modelo:
            continue
        df = pd.read_csv(arq).drop(columns=["system:index", ".geo"], errors="ignore")
        tabelas.setdefault(m["recorte"], []).append(df)
    if not tabelas:
        raise SystemExit(f"Nenhum CSV do modelo {modelo} em {entrada}")
    return {k: pd.concat(v, ignore_index=True) for k, v in tabelas.items()}


def somar(df, chaves):
    """Soma parciais (células da grade, biomas, municípios) por chave × ano."""
    return df.groupby(chaves + ["ano"], as_index=False).sum(numeric_only=True)


def derivar(mb, variaveis):
    """A partir de município × bioma, gera todos os recortes hierárquicos."""
    mb = somar(mb, ["zona"])
    mb["municipio"] = mb["zona"] // 10
    mb["bioma"] = mb["zona"] % 10
    mb["uf"] = mb["municipio"] // 100000
    mb["uf_bioma"] = mb["uf"] * 10 + mb["bioma"]
    mb["brasil"] = 1
    cols = ["area_ha"] + variaveis
    saida = {"municipio_bioma": mb.rename(columns={"zona": "id"})[["id", "ano"] + cols]}
    for tipo in ["municipio", "uf", "bioma", "uf_bioma", "brasil"]:
        saida[tipo] = somar(mb[[tipo, "ano"] + cols], [tipo]).rename(columns={tipo: "id"})
    return saida


def conferir(rec, variaveis):
    """Fechamento: a soma de cada nível deve bater com o Brasil (diferença só de arredondamento)."""
    br = rec["brasil"].set_index("ano")
    ok = True
    for tipo in ["municipio", "uf", "bioma", "municipio_bioma"]:
        s = rec[tipo].groupby("ano")[["area_ha"] + variaveis].sum()
        dif = (s - br[["area_ha"] + variaveis]).abs().max().max()
        print(f"  fechamento {tipo:>16} × brasil: maior diferença absoluta = {dif:.3g}")
        ok &= dif < 1e-3 * max(1.0, br[["area_ha"] + variaveis].abs().max().max())
    area_mha = br["area_ha"].iloc[0] / 1e6
    print(f"  área total coberta: {area_mha:,.1f} Mha (Brasil ≈ 851 Mha)")
    if not 840 < area_mha < 860:
        print("  ATENÇÃO: área fora do esperado — confira malhas, máscara e projeção.")
    return ok


def nomes_padrao(tipo, ids):
    if tipo == "brasil":
        return {1: "Brasil"}
    if tipo == "uf":
        return {i: UFS.get(int(i), str(i)) for i in ids}
    if tipo == "bioma":
        return {i: BIOMAS.get(int(i), str(i)) for i in ids}
    if tipo == "uf_bioma":
        return {i: f"{UFS.get(int(i) // 10, '?')} · {BIOMAS.get(int(i) % 10, '?')}" for i in ids}
    return {}


def carregar_nomes(pasta, tipo, ids):
    nomes = nomes_padrao(tipo, ids)
    if pasta and (Path(pasta) / f"{tipo}.csv").exists():
        df = pd.read_csv(Path(pasta) / f"{tipo}.csv")
        nomes.update(dict(zip(df["id"].astype("int64"), df["nome"])))
    return nomes


def gravar(rec, variaveis, saida, modelo, nomes_dir):
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    cols = ["area_ha"] + variaveis

    longa = pd.concat([df.melt(id_vars=["id", "ano"], value_vars=cols, var_name="variavel", value_name="valor")
                       .assign(tipo=tipo) for tipo, df in rec.items()], ignore_index=True)
    longa = longa[["tipo", "id", "ano", "variavel", "valor"]].sort_values(["tipo", "id", "ano", "variavel"])
    try:
        longa.to_parquet(saida / "estatisticas.parquet", index=False)
    except ImportError:
        longa.to_csv(saida / "estatisticas.csv.gz", index=False)

    catalogo = {"versao_script": VERSAO_SCRIPT, "versao_modelo": modelo, "gerado_em": date.today().isoformat(),
                "gases": "somente CO₂ (sem CH₄ e N₂O)",
                "variaveis": {v: unidade(v) for v in cols}, "tipos": {}}
    for tipo, df in rec.items():
        df = df.sort_values(["id", "ano"])
        anos = sorted(df["ano"].unique().tolist())
        ids = sorted(df["id"].unique().tolist())
        nomes = carregar_nomes(nomes_dir, tipo, ids)
        catalogo["tipos"][tipo] = {"anos": anos, "n": len(ids),
                                   "ids": [{"id": int(i), "nome": nomes.get(i, str(i))} for i in ids]}
        catalogo["tipos"][tipo]["lote"] = "uf" if tipo in LOTE_POR_UF else "unico"
        # séries em lotes (um arquivo por UF nos tipos municipais; um só nos demais)
        d = saida / "serie" / tipo
        d.mkdir(parents=True, exist_ok=True)
        lote = LOTE_POR_UF.get(tipo, lambda i: 0)
        df = df.assign(_lote=df["id"].map(lote))
        for nlote, gl in df.groupby("_lote"):
            series = {}
            for i, g in gl.groupby("id"):
                g = g.set_index("ano").reindex(anos, fill_value=0)
                series[str(int(i))] = {v: [compacto(x) for x in g[v]] for v in cols}
            (d / f"{int(nlote)}.json").write_text(json.dumps(
                {"tipo": tipo, "anos": anos, "series": series}, separators=(",", ":")))
        # mapas (um arquivo por variável: todos os recortes × anos)
        if tipo in SEM_MAPA:
            continue
        d = saida / "mapa" / tipo
        d.mkdir(parents=True, exist_ok=True)
        for v in cols:
            piv = df.pivot(index="id", columns="ano", values=v).reindex(index=ids, columns=anos).fillna(0)
            (d / f"{v}.json").write_text(json.dumps(
                {"tipo": tipo, "variavel": v, "anos": anos, "ids": [int(i) for i in ids],
                 "valores": {str(a): [compacto(x) for x in piv[a]] for a in anos}},
                separators=(",", ":")))
    (saida / "catalogo.json").write_text(json.dumps(catalogo, ensure_ascii=False, indent=1))
    print(f"Gravado em {saida}: {len(longa):,} linhas na tabela longa; tipos = {list(rec)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--entrada", required=True)
    ap.add_argument("--saida", required=True)
    ap.add_argument("--modelo", default="v1_2")
    ap.add_argument("--nomes", default=None)
    a = ap.parse_args()
    print(f"ybyra_estatisticas_agregar v{VERSAO_SCRIPT} · modelo {a.modelo}")

    tabelas = ler(a.entrada, a.modelo)
    if "municipio_bioma" not in tabelas:
        raise SystemExit("Falta o recorte municipio_bioma (base de todos os níveis hierárquicos).")
    variaveis = [c for c in tabelas["municipio_bioma"].columns if c not in ("zona", "ano", "area_ha")]

    rec = derivar(tabelas.pop("municipio_bioma"), variaveis)
    for nome, df in tabelas.items():  # recortes independentes (TI, UC, quilombolas, assentamentos)
        rec[nome] = somar(df, ["zona"]).rename(columns={"zona": "id"})[["id", "ano", "area_ha"] + variaveis]

    print("Conferência:")
    if not conferir(rec, variaveis):
        print("  ATENÇÃO: os níveis não fecham com o total do Brasil.")
    gravar(rec, variaveis, a.saida, a.modelo, a.nomes)


if __name__ == "__main__":
    main()
