#!/usr/bin/env python3
"""
aplicar_nomes.py · v0.1.1
=========================
Atualiza os nomes de web/geo/indice.json a partir dos CSV UTF-8 exportados pelo GEE
(gee/ybyra_estatisticas.js, MODO = 'nomes', ou gee/ybyra_nomes_uc.js: ybyra_nomes_<recorte>.csv).
O CSV precisa da coluna id; a de nome é "nome" ou, se não houver, a coluna cujo título lembra
nome (nome, name, nm_…) com mais valores preenchidos. Use --coluna NOME para fixá-la.
Só os nomes mudam; as camadas PMTiles e as extensões ficam como estão. O workflow do site
lê os nomes deste índice ao gerar o catálogo.

Uso: python scripts/aplicar_nomes.py <pasta com ybyra_nomes_*.csv>

Histórico de versões
  0.1.0 (2026-10-24) — versão inicial.
  0.1.1 (2026-10-24) — aceita a tabela completa de atributos (detecta a coluna de nome; --coluna fixa).
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


def coluna_nome(linhas, cabecalho, fixa=None):
    if fixa:
        return fixa
    if "nome" in cabecalho and any((r.get("nome") or "").strip() for r in linhas):
        return "nome"
    padrao = re.compile(r"nome|name|(^|_)(nm|no|nom)(_|$)|denomina", re.I)
    cand = [c for c in cabecalho if padrao.search(c) and not re.search(r"(^|_)(id|cod|cd)(_|$)", c, re.I)]
    cand.sort(key=lambda c: -sum(1 for r in linhas if (r.get(c) or "").strip()))
    return cand[0] if cand else None


def main():
    args = sys.argv[1:]
    fixa = None
    if "--coluna" in args:
        k = args.index("--coluna"); fixa = args[k + 1]; del args[k:k + 2]
    pasta = Path(args[0])
    indice = json.loads(INDICE.read_text(encoding="utf-8"))
    for arq in sorted(pasta.glob("ybyra_nomes_*.csv")):
        rec = arq.stem.replace("ybyra_nomes_", "")
        if rec in IGNORAR or rec not in indice:
            print(f"{rec}: ignorado")
            continue
        with open(arq, encoding="utf-8-sig", newline="") as fh:
            leitor = csv.DictReader(fh)
            linhas, cab = list(leitor), leitor.fieldnames or []
        col = coluna_nome(linhas, cab, fixa)
        if not col:
            print(f"{rec}: nenhuma coluna de nome encontrada; colunas: {cab}")
            continue
        print(f"{rec}: coluna de nome = {col}")
        nomes = {}
        for r in linhas:
            try:
                nomes[int(float(r["id"]))] = limpar(r[col])
            except (ValueError, KeyError, TypeError):
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
