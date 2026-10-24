#!/usr/bin/env python3
"""
aplicar_nomes.py · v0.1.0
=========================
Atualiza os nomes de web/geo/indice.json a partir dos CSV UTF-8 exportados pelo GEE
(gee/ybyra_estatisticas.js, MODO = 'nomes': ybyra_nomes_<recorte>.csv, colunas id,nome).
Só os nomes mudam; as camadas PMTiles e as extensões ficam como estão. O workflow do site
lê os nomes deste índice ao gerar o catálogo.

Uso: python scripts/aplicar_nomes.py <pasta com ybyra_nomes_*.csv>

Histórico de versões
  0.1.0 (2026-10-24) — versão inicial.
"""
import csv
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
INDICE = RAIZ / "web" / "geo" / "indice.json"
# municípios: o índice já traz "Nome (UF)" de fonte com acentos corretos; não sobrescrever
IGNORAR = {"municipio"}


def limpar(nome: str) -> str:
    nome = re.sub(r"\s+", " ", (nome or "").strip())
    nome = re.sub(r"\s*\[[^\]]*\]\s*$", "", nome)          # sufixos entre colchetes
    if nome.isupper() and len(nome) > 3:                      # TUDO MAIÚSCULO → título
        minus = {"de", "da", "do", "das", "dos", "e", "a", "o", "em"}
        nome = " ".join(p.lower() if i and p.lower() in minus else p.capitalize()
                        for i, p in enumerate(nome.split(" ")))
    return nome


def main():
    pasta = Path(sys.argv[1])
    indice = json.loads(INDICE.read_text(encoding="utf-8"))
    for arq in sorted(pasta.glob("ybyra_nomes_*.csv")):
        rec = arq.stem.replace("ybyra_nomes_", "")
        if rec in IGNORAR or rec not in indice:
            print(f"{rec}: ignorado")
            continue
        nomes = {}
        with open(arq, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                try:
                    nomes[int(float(r["id"]))] = limpar(r["nome"])
                except (ValueError, KeyError):
                    continue
        trocados = vazios = 0
        for e in indice[rec]:
            n = nomes.get(int(e[0]))
            if n:
                trocados += e[1] != n
                e[1] = n
            else:
                vazios += 1
        # nomes repetidos (ex.: duas UCs homônimas) ganham o id para diferenciar na busca
        cont = {}
        for e in indice[rec]:
            cont[e[1]] = cont.get(e[1], 0) + 1
        for e in indice[rec]:
            if cont[e[1]] > 1:
                e[1] = f"{e[1]} (nº {e[0]})"
        print(f"{rec}: {len(nomes)} nomes no CSV · {trocados} alterados · {vazios} sem nome no CSV")
    INDICE.write_text(json.dumps(indice, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    main()
