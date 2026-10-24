#!/usr/bin/env python3
"""
reparar_acentos.py · v0.1.1
===========================
Restaura os acentos perdidos ("�") nos nomes das malhas do MapBiomas exportadas do GEE.
Na origem, cada letra acentuada virou um único "�"; aqui cada palavra com "�" é comparada com um
vocabulário com acentos, nesta ordem:
  1. nomes próprios do IBGE (municípios e estados) e termos de áreas protegidas;
  2. lista de palavras do português (ex.: github.com/pythonprobr/palavras, palavras.txt);
  3. regras de terminação e de contexto (…�O → ÃO, ��O → ÇÃO, …�ES → ÕES, �+A/O/U → Ç, final → Á).
As palavras resolvidas só pelo passo 3 vão para um relatório de conferência.

Uso:
  python scripts/reparar_acentos.py <csv do GEE> <palavras.txt> <municipios_idx.json> <saída.csv> [coluna_nome]

Saída: CSV UTF-8 com id, nome, codigo, categoria, esfera (as três últimas se existirem no CSV).

Histórico de versões
  0.1.0 (2026-10-24) — versão inicial (unidades de conservação, CNUC 2026).
  0.1.1 (2026-10-24) — correções conferidas de etnônimos e nomes de terras indígenas e quilombos.
"""
import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

R = "�"
ACENTUADAS = "áàâãéêíóôõúüç"
MINUSC = {"de", "da", "do", "das", "dos", "e", "a", "o", "em", "na", "no", "nas", "nos", "à", "ao", "aos", "às"}
SIGLAS = {"APA", "ARIE", "RDS", "RPPN", "RESEX", "REBIO", "FLONA", "PARNA", "ESEC", "MONA", "REVIS", "RVS",
          "FLOTA", "PE", "PES", "PNM", "UC", "II", "III", "IV", "VI", "VII", "VIII", "IX", "XI", "XII", "SESC", "CEMIG",
          "CESP", "CHESF", "CPFL", "FURNAS", "RFFSA", "IBAMA", "ICMBIO", "TQ", "AC", "AL", "AM", "AP", "BA", "CE",
          "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SP", "TO"}
TERMOS = """estação ecológica biológica área proteção ambiental relevante interesse ecológico reserva particular
patrimônio natural floresta nacional estadual municipal parque monumento refúgio vida silvestre extrativista
desenvolvimento sustentável fauna jardim botânico lagoa ilha ilhas igarapé várzea cachoeira córrego ribeirão serra
chapada são joão josé antônio conceição tocantins pará amapá goiás piauí ceará paraná maranhão rondônia espírito
santa catarina paraíba pernambuco amazônia caatinga mata atlântica pantanal guaraná açaí jatobá jequitibá buriti
babaçu maracá niquiá jutaí xingu tapajós juruá purus içá tabatinga piraí itaúna mãe manguezal restinga mangue
ecossistema ecossistemas recuperação conservação preservação histórico cultural municipal""".split()


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def chave(w):
    """palavra com cada letra acentuada trocada por '�' (é exatamente o que sobrou na origem)."""
    return "".join(R if c in ACENTUADAS else c for c in w)


def carregar_vocabulario(arq_palavras, arq_mun):
    prior, geral = {}, {}

    def add(dic, w):
        w = w.strip().lower()
        if w and any(c in ACENTUADAS for c in w):
            dic.setdefault(chave(w), Counter())[w] += 1

    mun = json.loads(Path(arq_mun).read_text(encoding="utf-8"))
    for m in mun["m"]:
        for w in re.findall(r"[\wÀ-ÿ']+", m[1]):
            add(prior, w)
    for w in TERMOS:
        add(prior, w)
    for w in Path(arq_palavras).read_text(encoding="utf-8").split():
        add(geral, w)
    return prior, geral


# preferência quando o dicionário tem mais de uma forma (palavras comuns em nomes de UCs)
PREFERIR = {"cênico", "médio", "fóssil", "metálico", "gregório", "lázaro", "sílvia", "igapó", "sabiá", "gambá",
            "copaíba", "manacá", "camboatá", "jaguaretê", "vovó", "avó", "décio", "adélio", "cocó", "jurupará",
            "panapaná", "aricá", "juá", "jará", "toró", "pré", "iguapé", "taí", "japuí", "aruã", "badé", "tiê"}


def contexto(geral_palavras):
    """frequência da letra acentuada por vizinhança (3, 2 e 1 letras de cada lado)."""
    ctx = Counter()
    for w in geral_palavras:
        w2 = f"^{w}$"
        for i, c in enumerate(w2):
            if c in ACENTUADAS:
                for k in (3, 2, 1):
                    ctx[(k, w2[max(0, i - k):i], w2[i + 1:i + 1 + k], c)] += 1
    return ctx


def por_contexto(w, ctx):
    w2 = list(f"^{w}$")
    for i, c in enumerate(w2):
        if c != R:
            continue
        esq, dir_ = "".join(w2[:i]), "".join(w2[i + 1:])
        escolha = None
        for k in (3, 2, 1):
            cont = {a: ctx.get((k, esq[-k:], dir_[:k], a), 0) for a in ACENTUADAS}
            if max(cont.values()) > 0:
                escolha = max(cont, key=cont.get)
                break
        w2[i] = escolha or "á"
    return "".join(w2)[1:-1]


# correções conferidas à mão (forma com "�" em minúsculas → forma correta)
CORRECOES = {
    "munic�pal": "municipal", "d�gua": "d'água", "d��gua": "d'água", "d'�ntas": "d'antas", "pur�s": "purus",
    "curia�": "curiaú", "jib�ia": "jibóia", "igarap�s": "igarapés", "bonif�cia": "bonifácia", "l�fgren": "löfgren",
    "p�cem": "pecém", "del�cias": "delícias", "�midos": "úmidos", "ber��rios": "berçários", "kayap�": "kayapó",
    "tupinamb�s": "tupinambás", "�rg�os": "órgãos", "jur�ia": "juréia", "corr�as": "corrêas", "igua��": "iguaçu",
    "tapirap�aquiri": "tapirapé-aquiri", "tinhar�": "tinharé", "tobog�": "tobogã", "guartel�": "guartelá",
    "cuni�": "cuniã", "catagu�s": "cataguás", "itangu�": "itanguá", "sui�a": "suíça", "vel�so": "velôso",
    "cam�lo": "camêlo", "l�bo": "lôbo", "c�do": "codó", "paran�": "paraná", "carna�ba": "carnaúba",
    "ita�ba": "itaúba", "timb�": "timbó", "jequi�": "jequiá", "itapu�": "itapuã", "apor�": "aporé",
    "karaj�": "karajá",
    "ka�aguy": "ka'aguy",
    "ofay�": "ofayé",
    "sawr�": "sawré",
    "trocar�": "trocará",
    "tur�": "turé",
    "xapec�": "xapecó",
    "acim�": "acimã",
    "amanay�": "amanayé",
    "apinay�": "apinayé",
    "arawet�": "araweté",
    "caxix�": "caxixó",
    "akr�tikat�j�": "akrãtikatêjê",
    "gavi�ozinho": "gaviãozinho",
    "geripanc�": "geripancó",
    "guyrarok�": "guyraroká",
    "herarek�": "herarekã",
    "kl�n�": "klãnõ",
    "jaguapir�": "jaguapiré",
    "kadiw�u": "kadiwéu",
    "memortumr�": "memortumré",
    "kap�t": "kapôt",
    "karara�": "kararaô",
    "krah�": "krahô",
    "krenreh�": "krenrehé",
    "kreny�": "krenyê",
    "menk�": "menkü",
    "panar�": "panará",
    "pankarar�": "pankararé",
    "parakan�": "parakanã",
    "naruv�tu": "naruvôtu",
    "ap�njekra": "apãnjekra",
    "sarar�": "sararé",
    "sissa�ma": "sissaíma",
    "tik�na": "tikúna",
    "wai�pi": "waiãpi",
    "wedez�": "wedezé",
    "�ande": "ñande",
    "guas�": "guasú",
    "itamar�": "itamarã",
    "enawen�": "enawenê",
    "naw�": "nawê",
    "itat�": "itatã",
    "kambiw�": "kambiwá",
    "manissu�": "manissuã",
    "itacuru��": "itacuruçá",
    "itaco�zinho": "itacoãzinho",
    "fid�lix": "fidélix",
    "anast�cia": "anastácia",
    "panpel�nia": "pampelônia",
    "guaru��": "guaruçá",
    "cajua�pe": "cajuaípe",
    "kond�": "kondá",
    "kor�": "korá",
    "h�m": "hãm",
    "y�xux": "yĩxux",
    "t�a": "téa",
    "rebu�": "rebuá",
    "�wa": "ãwa",
    "a�etete": "añetete",
    "ir�du": "iròdu",
    "ir�na": "iràna",
    "tup��i": "tupã'i",
    "kand�ia": "kandóia",
    "mimb�": "mimbó",
    "waiw�i": "waiwái",
    "guavir�": "guavirá",
    "teko�": "tekoá",
    "tekoh�": "tekohã",
    "am�nia": "amônia",
    "a��": "açu",
    "fl�": "flô",
    "iguatem�": "iguatemí",
    "tripu�": "tripuí",
}


def resolver(palavra, prior, geral, desconhecidas, ambiguas, ctx):
    w = palavra.lower()
    if w in CORRECOES:
        return CORRECOES[w]
    # apóstrofo perdido: D'Água, D'Ouro, D'Ostra
    m = re.match("^d" + R + "+(.*)$", w)
    if m and m.group(1)[:1] in "aeiou" + R:
        resto = m.group(1)
        if resto == "gua":
            resto = "água"
        elif R in resto:
            resto = resolver(resto, prior, geral, desconhecidas, ambiguas, ctx)
        return "d'" + resto
    for dic in (prior, geral):
        if w in dic:
            c = dic[w]
            if len(c) > 1:
                pref = [x for x in c if x in PREFERIR]
                if pref:
                    return pref[0]
                ambiguas[palavra] = list(c)
            return c.most_common(1)[0][0]
    s = w
    s = re.sub(R + R + "o$", "ção", s)
    s = re.sub(R + R + "es$", "ções", s)
    s = re.sub(R + "o$", "ão", s)
    s = re.sub(R + "es$", "ões", s)
    if R in s:
        s = por_contexto(s, ctx)
    desconhecidas[(palavra, s)] += 1
    return s


def caixa(palavra_original, corrigida, primeira):
    if palavra_original.upper().replace(R, "") in SIGLAS and R not in palavra_original:
        return palavra_original.upper()
    if not primeira and corrigida in MINUSC:
        return corrigida
    return corrigida[:1].upper() + corrigida[1:]


def reparar_nome(nome, prior, geral, desconhecidas, ambiguas, ctx):
    nome = re.sub(r"\s+", " ", nome.strip())
    partes = re.split(r"([\wÀ-ÿ" + R + r"']+)", nome)
    out, primeira = [], True
    for p in partes:
        if not re.match(r"[\wÀ-ÿ" + R + r"']", p or " "):
            out.append(p)
            continue
        if R in p:
            corr = resolver(p, prior, geral, desconhecidas, ambiguas, ctx)
        else:
            corr = p.lower()
        # partes com hífen ou apóstrofo seguem a mesma regra
        c = caixa(p, corr, primeira)
        if c.lower().startswith("d'") and len(c) > 2:
            c = c[:2] + c[2].upper() + c[3:]
        if "-" in c:
            c = "-".join(x[:1].upper() + x[1:] for x in c.split("-"))
        out.append(c)
        primeira = False
    return "".join(out)


def main():
    arq_csv, arq_pal, arq_mun, saida = sys.argv[1:5]
    col_nome = sys.argv[5] if len(sys.argv) > 5 else "NOME_UC"
    prior, geral = carregar_vocabulario(arq_pal, arq_mun)
    ctx = contexto(w for cont in geral.values() for w in cont)
    linhas = list(csv.DictReader(open(arq_csv, encoding="utf-8-sig", newline="")))
    desconhecidas, ambiguas = Counter(), {}
    rep = lambda s: reparar_nome(s or "", prior, geral, desconhecidas, ambiguas, ctx)  # noqa: E731
    with open(saida, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "nome", "codigo", "categoria", "esfera"])
        for r in sorted(linhas, key=lambda r: int(float(r["id"]))):
            w.writerow([int(float(r["id"])), rep(r[col_nome]), r.get("CD_CNUC", ""),
                        rep(r.get("CATEGORIA", "")), rep(r.get("ESFERA", ""))])
    print(f"{len(linhas)} nomes gravados em {saida}")
    print(f"palavras resolvidas só por regra (conferir): {len(desconhecidas)} distintas")
    for (p, r), n in desconhecidas.most_common(200):
        print(f"  {n:3d}  {p} → {r}")
    print(f"palavras ambíguas no dicionário: {len(ambiguas)}")
    for p, c in list(ambiguas.items())[:40]:
        print(f"  {p}: {c}")


if __name__ == "__main__":
    main()
