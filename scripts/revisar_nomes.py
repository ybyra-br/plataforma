#!/usr/bin/env python3
"""
revisar_nomes.py · v0.1.1
=========================
Revisão de acentuação de todos os nomes de web/geo/indice.json:
  1. letras acentuadas perdidas na origem ("?" ou "�", uma marca por letra) → reparar_acentos.py;
  2. pontuação perdida nas UCs (apóstrofo, aspas e travessão que viraram "?");
  3. palavras que vieram sem acento da base oficial ("Area", "Refugio", "Sitio", "Joao") → acentuadas
     só quando a forma sem acento não existe no vocabulário e há uma única forma acentuada (ou uma
     preferida em reparar_acentos.PREFERIR), com uma lista de exceções de nomes próprios.
Grava o índice revisado e um relatório de todas as trocas (dados/nomes/revisao_acentos.csv).

Uso: python scripts/revisar_nomes.py <palavras.txt> <municipios_idx.json>

Histórico de versões
  0.1.0 (2026-10-24) — versão inicial.
  0.1.1 (2026-10-24) — mantém a caixa original do nome (só as letras marcadas mudam); mais exceções.
"""
import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reparar_acentos as ra  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
INDICE = RAIZ / "web" / "geo" / "indice.json"
RELATORIO = RAIZ / "dados" / "nomes" / "revisao_acentos.csv"
REVISAR = ["unidade_conservacao", "terra_indigena", "territorio_quilombola", "bacia_nivel1", "bacia_nivel2",
           "amazonia_legal", "matopiba", "bioma"]
# nomes próprios que existem assim mesmo, sem acento (não acentuar)
NAO_ACENTUAR = {"sana", "sibara", "francio", "omer", "regua", "sio", "zes", "coris", "filo", "itaco", "curia",
                "cora", "ambe", "nia", "nio", "gua", "ara", "gra",
                # siglas e nomes que se escrevem sem acento (inclusive pela grafia atual)
                "arie", "nelson", "mater", "ronco", "acaba", "helico", "sos", "rocio", "goiana", "cananeia", "boe",
                "gurgueia", "eliezer", "parima", "amambai", "irara"}
# nomes que vieram com anotações da base de origem no lugar do nome (forma já sem marcas → nome)
NOMES_MANUAIS = {
    "Abui, Paraná do Abui, Tapagem, Sagrado Coração - essas são as comunidades integrantes do TQ Alto Trombetas 1, "
    "esse deve ser o nome do TQ que aparece.": "Alto Trombetas 1 (Abui, Paraná do Abui, Tapagem e Sagrado Coração)",
    "Cabeceiras - TQ Cabeceiras formado pelas comunidades São José, Silêncio, Mata, Cuecé, Apuí e Castanhaduba":
        "Cabeceiras (São José, Silêncio, Mata, Cuecé, Apuí e Castanhaduba)",
    "Centro Ouro - TQ Centro Ouro formado pelas comunidades Centro Ouro, Nossa Senhora das Graças e São Bernardino":
        "Centro Ouro (Centro Ouro, Nossa Senhora das Graças e São Bernardino)",
    "Balique (TQ BAILIQUE composto das comunidades Bailique Beira, Bailique Centro, Poção e São Bernardo)":
        "Bailique (Bailique Beira, Bailique Centro, Poção e São Bernardo)",
    "Rio dos Macacos ( Simões Filho)": "Rio dos Macacos (Simões Filho)",
}
PONTUACAO = [(re.compile(r"\?([^?]+)\?"), r"“\1”"),            # ?Walter Bessa? → “Walter Bessa”
             (re.compile(r"\s\?\s"), " – ")]                    # "Natural ? RPPN" → "Natural – RPPN"


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def vocabulario_acentuado(prior, geral):
    todos = set()
    for dic in (prior, geral):
        for cont in dic.values():
            todos.update(cont)
    acc = defaultdict(set)
    for w in todos:
        b = sem_acento(w)
        if b != w:
            acc[b].add(w)
    return todos, acc


def acentuar_faltantes(nome, todos, acc, palavras_pt, trocas):
    def troca(m):
        w = m.group(0)
        wl = w.lower()
        if len(wl) < 3 or wl in NAO_ACENTUAR or wl != sem_acento(wl) or wl in palavras_pt or wl not in acc:
            return w
        cands = sorted(acc[wl])
        if len(cands) > 1:
            pref = [c for c in cands if c in ra.PREFERIR or c in {"mário", "corrêa", "tarumã", "paraná"}]
            if len(pref) != 1:
                return w
            cands = pref
        novo = cands[0]
        novo = novo.upper() if w.isupper() else (novo[:1].upper() + novo[1:] if w[:1].isupper() else novo)
        trocas[(w, novo)] += 1
        return novo
    return re.sub(r"[A-Za-zÀ-ÿ]+", troca, nome)


def com_caixa(orig, corr):
    """aplica a caixa da palavra original à corrigida (mesmo comprimento: uma marca por letra)."""
    if len(orig) != len(corr):
        return corr[:1].upper() + corr[1:] if orig[:1].isupper() else corr
    letras = [c for c in orig if c.isalpha()]
    tudo_maius = bool(letras) and all(c.isupper() for c in letras)
    out = []
    for i, (o, c) in enumerate(zip(orig, corr)):
        if o == ra.R:
            viz = [x for x in (orig[i - 1] if i else "", orig[i + 1] if i + 1 < len(orig) else "") if x.isalpha()]
            maius = tudo_maius or (i == 0 and (not viz or viz[0].islower()) and False) or (i == 0 and len(orig) > 1 and orig[1].islower() and True)
            out.append(c.upper() if maius else c)
        else:
            out.append(c.upper() if o.isupper() else c)
    return "".join(out)


def reparar_preservando(nome, prior, geral, desconhecidas, ambiguas, ctx):
    def troca(m):
        w = m.group(0)
        if ra.R not in w:
            return w
        return com_caixa(w, ra.resolver(w, prior, geral, desconhecidas, ambiguas, ctx))
    return re.sub(r"[\wÀ-ÿ" + ra.R + r"']+", troca, nome)


def main():
    arq_pal, arq_mun = sys.argv[1:3]
    prior, geral = ra.carregar_vocabulario(arq_pal, arq_mun)
    ctx = ra.contexto(w for cont in geral.values() for w in cont)
    todos, acc = vocabulario_acentuado(prior, geral)
    palavras_pt = set(Path(arq_pal).read_text(encoding="utf-8").split())
    indice = json.loads(INDICE.read_text(encoding="utf-8"))
    linhas_rel, resumo = [], []
    for rec in REVISAR:
        if rec not in indice:
            continue
        desconhecidas, ambiguas, trocas_falt = Counter(), {}, Counter()
        n_alt = 0
        for e in indice[rec]:
            antes = e[1]
            nome = antes
            if rec == "unidade_conservacao" and "?" in nome:
                nome = re.sub(r"(?i)\bd\?(?=[a-zà-ÿ])", "D'", nome)       # D?Agua → D'Agua
                for rx, sub in PONTUACAO:
                    nome = rx.sub(sub, nome)
            nome = nome.replace("?", ra.R)
            if ra.R in nome:
                nome = reparar_preservando(nome, prior, geral, desconhecidas, ambiguas, ctx)
            # apóstrofo: acentua a parte depois de D'
            nome = re.sub(r"(D')([A-Za-zÀ-ÿ]+)",
                          lambda m: m.group(1) + acentuar_faltantes(m.group(2), todos, acc, palavras_pt, trocas_falt), nome)
            nome = acentuar_faltantes(nome, todos, acc, palavras_pt, trocas_falt)
            nome = NOMES_MANUAIS.get(nome, nome)
            if nome != antes:
                n_alt += 1
                linhas_rel.append([rec, e[0], antes, nome])
                e[1] = nome
        resumo.append((rec, n_alt, len(desconhecidas)))
        print(f"\n{rec}: {n_alt} nomes alterados")
        if desconhecidas:
            print(f"  palavras acentuadas por regra (conferir): " +
                  ", ".join(f"{p}→{r}" for (p, r), _ in desconhecidas.most_common(400)))
        if trocas_falt:
            print("  acentos acrescentados: " + ", ".join(f"{a}→{b} ({n})" for (a, b), n in trocas_falt.most_common(80)))
    RELATORIO.parent.mkdir(parents=True, exist_ok=True)
    with open(RELATORIO, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["recorte", "id", "antes", "depois"])
        w.writerows(linhas_rel)
    INDICE.write_text(json.dumps(indice, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"\nrelatório: {RELATORIO.relative_to(RAIZ)} ({len(linhas_rel)} trocas)")


if __name__ == "__main__":
    main()
