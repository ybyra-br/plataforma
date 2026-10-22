"""
gerar_pmtiles.py · v0.1.0
Malhas vetoriais do mapa da plataforma de emissões YbYrá-BR em PMTiles v3 (Mapbox Vector Tiles),
só com numpy, a partir dos shapefiles exportados pelo GEE (gee/ybyra_estatisticas.js, MODO 'geometrias').
Núcleo (MVT, recorte por bloco, PMTiles) copiado de alerta-queimadas-municipios/scripts/gerar_pmtiles.py
v0.1.0; aqui generalizado para vários recortes.

Entrada:  <pasta>/ybyra_geometria_<recorte>.shp/.dbf   (colunas id, nome[, sigla_uf])
Saídas:   web/geo/<recorte>.pmtiles   (camada "r", atributo c = id; zooms 2 a zmax do recorte)
          web/geo/indice.json         ({recorte: [[id, nome, x0, y0, x1, y1], ...]}: busca e enquadramento)

Antes do corte em blocos, cada anel é simplificado (Douglas–Peucker, ~0,0001° ≈ 11 m), como a malha
de junção da plataforma de queimadas. Nomes: municípios pela malha IBGE 2025 da plataforma de queimadas
(o shapefile do GEE trouxe "?" no lugar de letras acentuadas); estados por tabela fixa; bacias sem
colchetes; UCs sem nome recebem "Unidade de conservação nº <id>".

Uso: python scripts/gerar_pmtiles.py <pasta_shapefiles> <municipios_idx.json da plataforma de queimadas> [recortes...]

Histórico de versões
  0.1.0 (2026-10-22) — versão inicial.
"""
from __future__ import annotations

import gzip
import json
import math
import struct
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ler_shp import ler  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
EXT = 4096
BUF = 64
CAMADA = "r"
PRE_TOL = 1e-4   # graus

# recorte: zoom máximo dos blocos (acima disso o MapLibre amplia o último nível)
RECORTES = {"municipio": 10, "uf": 8, "bioma": 8, "amazonia_legal": 8, "matopiba": 8,
            "bacia_nivel1": 8, "bacia_nivel2": 9, "terra_indigena": 10,
            "unidade_conservacao": 10, "territorio_quilombola": 11}
UF_NOME = {11: "Rondônia", 12: "Acre", 13: "Amazonas", 14: "Roraima", 15: "Pará", 16: "Amapá", 17: "Tocantins",
           21: "Maranhão", 22: "Piauí", 23: "Ceará", 24: "Rio Grande do Norte", 25: "Paraíba", 26: "Pernambuco",
           27: "Alagoas", 28: "Sergipe", 29: "Bahia", 31: "Minas Gerais", 32: "Espírito Santo", 33: "Rio de Janeiro",
           35: "São Paulo", 41: "Paraná", 42: "Santa Catarina", 43: "Rio Grande do Sul", 50: "Mato Grosso do Sul",
           51: "Mato Grosso", 52: "Goiás", 53: "Distrito Federal"}
MINUSC = {"de", "do", "da", "dos", "das", "e"}


def titulo(s: str) -> str:
    s = s.strip().strip("[]").strip()
    if s.isupper():
        s = " ".join(p.lower() if p.lower() in MINUSC and k else p.capitalize() for k, p in enumerate(s.split()))
    return s


# ------------------------------------------------------------------ protobuf mínimo
def varint(v: int) -> bytes:
    out = bytearray()
    while True:
        b = v & 0x7F
        v >>= 7
        if v:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def zz(v: int) -> int:
    return (v << 1) ^ (v >> 63)


def campo(num: int, tipo: int, dado: bytes | int) -> bytes:
    chave = varint((num << 3) | tipo)
    if tipo == 0:
        return chave + varint(dado)
    return chave + varint(len(dado)) + dado


def empacotado(vals) -> bytes:
    return b"".join(varint(v) for v in vals)


# ------------------------------------------------------------------ geometria
def para_mercator(r: np.ndarray) -> np.ndarray:
    """lon/lat -> [0,1]² Web Mercator, y para baixo."""
    lat = np.clip(r[:, 1], -85.05, 85.05)
    x = (r[:, 0] + 180.0) / 360.0
    y = (1.0 - np.arcsinh(np.tan(np.radians(lat))) / math.pi) / 2.0
    return np.column_stack([x, y])


def area2(r: np.ndarray) -> float:
    x, y = r[:, 0], r[:, 1]
    return float(np.dot(x, np.roll(y, -1)) - np.dot(np.roll(x, -1), y))


def recortar_lado(p: np.ndarray, eixo: int, lim: float, maior: bool) -> np.ndarray:
    """Um passo de Sutherland–Hodgman (anel aberto, sem ponto repetido)."""
    if len(p) == 0:
        return p
    v = p[:, eixo]
    dentro = v >= lim if maior else v <= lim
    if dentro.all():
        return p
    if not dentro.any():
        return p[:0]
    q = np.roll(p, -1, axis=0)
    dq = np.roll(dentro, -1)
    vq = q[:, eixo]
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        t = (lim - v) / (vq - v)
        inter = p + (q - p) * t[:, None]
    inter[:, eixo] = lim
    # para cada aresta i->i+1: até dois pontos de saída
    s1 = np.where((dentro & ~dq)[:, None] | (~dentro & dq)[:, None], inter, q)
    m1 = (dentro & dq) | (dentro & ~dq) | (~dentro & dq)
    m2 = ~dentro & dq
    pares = np.stack([s1, q], axis=1)
    mascara = np.stack([m1, m2], axis=1)
    return pares[mascara]


def recortar(p: np.ndarray, x0, y0, x1, y1) -> np.ndarray:
    p = recortar_lado(p, 0, x0, True)
    p = recortar_lado(p, 0, x1, False)
    p = recortar_lado(p, 1, y0, True)
    p = recortar_lado(p, 1, y1, False)
    return p


def limpar(r: np.ndarray) -> np.ndarray | None:
    """Arredonda, remove pontos repetidos consecutivos; None se degenerou."""
    r = np.round(r).astype(np.int64)
    if len(r) < 3:
        return None
    d = np.any(r != np.roll(r, 1, axis=0), axis=1)
    r = r[d]
    if len(r) < 3 or area2(r.astype(float)) == 0:
        return None
    return r


def geometria_mvt(poligonos: list[list[np.ndarray]]) -> list[int]:
    cmd, cx, cy = [], 0, 0
    for aneis in poligonos:
        for k, r in enumerate(aneis):
            a = area2(r.astype(float))
            if (k == 0) != (a > 0):  # exterior positivo, buracos negativos (coordenadas do bloco, y para baixo)
                r = r[::-1]
            x, y = int(r[0, 0]), int(r[0, 1])
            cmd += [(1 & 7) | (1 << 3), zz(x - cx), zz(y - cy)]
            cx, cy = x, y
            cmd.append((2 & 7) | ((len(r) - 1) << 3))
            for x, y in r[1:]:
                x, y = int(x), int(y)
                cmd += [zz(x - cx), zz(y - cy)]
                cx, cy = x, y
            cmd.append((7 & 7) | (1 << 3))
    return cmd


def bloco_mvt(feicoes: dict[int, list[list[np.ndarray]]]) -> bytes:
    valores, idx_val, fs = [], {}, []
    for cod in sorted(feicoes):
        g = geometria_mvt(feicoes[cod])
        if not g:
            continue
        if cod not in idx_val:
            idx_val[cod] = len(valores)
            valores.append(cod)
        f = (campo(1, 0, cod) + campo(2, 2, empacotado([0, idx_val[cod]])) + campo(3, 0, 3)
             + campo(4, 2, empacotado(g)))
        fs.append(campo(2, 2, f))
    if not fs:
        return b""
    camada = campo(15, 0, 2) + campo(1, 2, CAMADA.encode()) + b"".join(fs) + campo(3, 2, b"c")
    camada += b"".join(campo(4, 2, campo(5, 0, v)) for v in valores) + campo(5, 0, EXT)
    return campo(3, 2, camada)


# ------------------------------------------------------------------ PMTiles v3
def zxy_id(z: int, x: int, y: int) -> int:
    acc = ((1 << (2 * z)) - 1) // 3
    n = 1 << z
    s = n >> 1
    d = 0
    while s > 0:
        rx = 1 if x & s else 0
        ry = 1 if y & s else 0
        d += s * s * ((3 * rx) ^ ry)
        if ry == 0:
            if rx == 1:
                x, y = n - 1 - x, n - 1 - y
            x, y = y, x
        s >>= 1
    return acc + d


def diretorio(entradas) -> bytes:
    out = bytearray(varint(len(entradas)))
    ult = 0
    for e in entradas:
        out += varint(e[0] - ult)
        ult = e[0]
    for e in entradas:
        out += varint(e[3])
    for e in entradas:
        out += varint(e[2])
    for i, e in enumerate(entradas):
        if i > 0 and e[1] == entradas[i - 1][1] + entradas[i - 1][2]:
            out += varint(0)
        else:
            out += varint(e[1] + 1)
    return gzip.compress(bytes(out), mtime=0)


def gravar_pmtiles(caminho: Path, blocos: dict[tuple, bytes], zmin, zmax, caixa, meta: dict):
    itens = sorted(((zxy_id(*k), v) for k, v in blocos.items()), key=lambda t: t[0])
    dados, entradas, vistos = bytearray(), [], {}
    for tid, b in itens:
        if b in vistos:
            off, ln = vistos[b]
        else:
            off, ln = len(dados), len(b)
            dados += b
            vistos[b] = (off, ln)
        if entradas and entradas[-1][0] + entradas[-1][3] == tid and entradas[-1][1] == off:
            entradas[-1][3] += 1
        else:
            entradas.append([tid, off, ln, 1])
    raiz = diretorio(entradas)
    folhas = b""
    if 127 + len(raiz) > 16384:
        tam = 4096
        while True:
            folhas, r_ent = bytearray(), []
            for i in range(0, len(entradas), tam):
                parte = entradas[i:i + tam]
                bl = diretorio(parte)
                r_ent.append([parte[0][0], len(folhas), len(bl), 0])
                folhas += bl
            raiz = diretorio(r_ent)
            if 127 + len(raiz) <= 16384:
                break
            tam *= 2
        folhas = bytes(folhas)
    meta_b = gzip.compress(json.dumps(meta, ensure_ascii=False).encode(), mtime=0)
    o_raiz = 127
    o_meta = o_raiz + len(raiz)
    o_folha = o_meta + len(meta_b)
    o_dados = o_folha + len(folhas)
    e7 = lambda v: int(round(v * 1e7))  # noqa: E731
    cab = b"PMTiles" + bytes([3]) + struct.pack(
        "<QQQQQQQQQQQBBBBBBiiiiBii",
        o_raiz, len(raiz), o_meta, len(meta_b), o_folha, len(folhas), o_dados, len(dados),
        len(itens), len(entradas), len(vistos), 1, 2, 2, 1, zmin, zmax,
        e7(caixa[0]), e7(caixa[1]), e7(caixa[2]), e7(caixa[3]),
        5, e7((caixa[0] + caixa[2]) / 2), e7((caixa[1] + caixa[3]) / 2))
    assert len(cab) == 127, len(cab)
    caminho.write_bytes(cab + raiz + meta_b + folhas + bytes(dados))



def dp(p: np.ndarray, tol: float) -> np.ndarray:
    """Douglas–Peucker iterativo; preserva o primeiro e o último ponto."""
    n = len(p)
    if n < 5 or tol <= 0:
        return p
    manter = np.zeros(n, bool)
    manter[[0, n - 1]] = True
    pilha = [(0, n - 1)]
    while pilha:
        i, j = pilha.pop()
        if j <= i + 1:
            continue
        a, b = p[i], p[j]
        seg = p[i + 1:j]
        ab = b - a
        L = np.hypot(*ab)
        if L == 0:
            d = np.hypot(*(seg - a).T)
        else:
            d = np.abs(ab[0] * (seg[:, 1] - a[1]) - ab[1] * (seg[:, 0] - a[0])) / L
        k = int(np.argmax(d))
        if d[k] > tol:
            m = i + 1 + k
            manter[m] = True
            pilha += [(i, m), (m, j)]
    return p[manter]


# ------------------------------------------------------------------ principal
def nomes_de(recorte, attrs, mun_idx):
    i, n = int(attrs["id"]), str(attrs.get("nome") or "").strip()
    if recorte == "municipio":
        m = mun_idx.get(i)
        return f"{m[0]} ({m[1]})" if m else f"{n} ({attrs.get('sigla_uf', '')})"
    if recorte == "uf":
        return UF_NOME.get(i, n)
    if recorte == "amazonia_legal":
        return "Amazônia Legal"
    if recorte == "matopiba":
        return "MATOPIBA"
    if recorte == "unidade_conservacao" and not n:
        return f"Unidade de conservação nº {i}"
    return titulo(n) if recorte.startswith("bacia") else n


def gerar(recorte, pasta, mun_idx, zmin=2):
    zmax = RECORTES[recorte]
    t0 = time.time()
    fs = ler(Path(pasta) / f"ybyra_geometria_{recorte}")
    feicoes, idx = [], []
    lon0 = lat0 = 999.0
    lon1 = lat1 = -999.0
    for attrs, polis in fs:
        if not polis:
            continue
        cod = int(attrs["id"])
        polis = [[dp(r, PRE_TOL)[:-1] for r in pol] for pol in polis]   # anel fechado -> aberto
        polis = [[r for r in pol if len(r) >= 3] for pol in polis]
        polis = [pol for pol in polis if pol and len(pol[0]) >= 3]
        if not polis:
            continue
        tudo = np.vstack([r for pol in polis for r in pol])
        bb = [float(tudo[:, 0].min()), float(tudo[:, 1].min()), float(tudo[:, 0].max()), float(tudo[:, 1].max())]
        lon0, lat0, lon1, lat1 = min(lon0, bb[0]), min(lat0, bb[1]), max(lon1, bb[2]), max(lat1, bb[3])
        idx.append([cod, nomes_de(recorte, attrs, mun_idx)] + [round(v, 4) for v in bb])
        feicoes.append((cod, [[para_mercator(r) for r in pol] for pol in polis]))
    print(f"{recorte}: {len(feicoes)} feições lidas em {time.time() - t0:.0f}s", flush=True)

    blocos = {}
    for z in range(zmin, zmax + 1):
        S = EXT * (1 << z)
        tol = 1.0 / S
        por_bloco = defaultdict(lambda: defaultdict(list))
        for cod, polis in feicoes:
            for pol in polis:
                ext = dp(np.vstack([pol[0], pol[0][:1]]), tol)[:-1] * S
                if len(ext) < 3:
                    continue
                aneis = [ext] + [dp(np.vstack([h, h[:1]]), tol)[:-1] * S for h in pol[1:]]
                aneis = [aneis[0]] + [h for h in aneis[1:] if len(h) >= 3 and abs(area2(h)) > 4]
                tx0 = int((ext[:, 0].min() - BUF) // EXT)
                tx1 = int((ext[:, 0].max() + BUF) // EXT)
                ty0 = int((ext[:, 1].min() - BUF) // EXT)
                ty1 = int((ext[:, 1].max() + BUF) // EXT)
                inteiro = tx0 == tx1 and ty0 == ty1
                for tx in range(tx0, tx1 + 1):
                    for ty in range(ty0, ty1 + 1):
                        ox, oy = tx * EXT, ty * EXT
                        saida = []
                        for k, r in enumerate(aneis):
                            q = r - (ox, oy)
                            if not inteiro:
                                q = recortar(q, -BUF, -BUF, EXT + BUF, EXT + BUF)
                            q = limpar(q) if len(q) >= 3 else None
                            if q is None:
                                if k == 0:
                                    break
                                continue
                            saida.append(q)
                        if saida:
                            por_bloco[(tx, ty)][cod].append(saida)
        n0 = len(blocos)
        for (tx, ty), fz in por_bloco.items():
            b = bloco_mvt(fz)
            if b:
                blocos[(z, tx, ty)] = gzip.compress(b, compresslevel=9, mtime=0)
        tam = sum(len(v) for k, v in blocos.items() if k[0] == z)
        print(f"  z{z}: {len(blocos) - n0} blocos, {tam / 1e6:.1f} MB", flush=True)

    meta = {"name": recorte, "description": f"Recorte {recorte} — plataforma de emissões YbYrá-BR",
            "attribution": "Malhas © IBGE, FUNAI, ICMBio/MMA, INCRA, ANA, EMBRAPA (via MapBiomas)", "format": "pbf",
            "vector_layers": [{"id": CAMADA, "fields": {"c": "Number"}, "minzoom": zmin, "maxzoom": zmax}]}
    destino = RAIZ / "web" / "geo" / f"{recorte}.pmtiles"
    gravar_pmtiles(destino, blocos, zmin, zmax, (lon0, lat0, lon1, lat1), meta)
    print(f"  {destino.name}: {destino.stat().st_size / 1e6:.1f} MB em {time.time() - t0:.0f}s", flush=True)
    return sorted(idx)


def main():
    pasta, mun_json = sys.argv[1], sys.argv[2]
    quais = sys.argv[3:] or list(RECORTES)
    mi = json.load(open(mun_json, encoding="utf-8"))
    mun_idx = {int(m[0]): (m[1], m[2]) for m in mi["m"]}
    caminho_idx = RAIZ / "web" / "geo" / "indice.json"
    indice = json.loads(caminho_idx.read_text(encoding="utf-8")) if caminho_idx.exists() else {}
    for r in quais:
        indice[r] = gerar(r, pasta, mun_idx)
        caminho_idx.write_text(json.dumps(indice, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("indice.json:", {k: len(v) for k, v in indice.items()})


if __name__ == "__main__":
    main()
