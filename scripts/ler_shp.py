"""
ler_shp.py · v0.1.0 — leitor mínimo de shapefile (polígonos, tipos 5/15/25) e dBASE, só com numpy.
ler(caminho_sem_ext) -> lista de (atributos: dict, poligonos: list[list[np.ndarray (n,2)]])
Os anéis vêm do shapefile (externos em sentido horário, buracos anti-horário); a separação em
polígonos usa o sentido do anel (anel horário abre polígono novo; anti-horário é buraco do último).
"""
import struct
from pathlib import Path

import numpy as np


def ler_dbf(caminho):
    b = Path(caminho).read_bytes()
    n, cab, tam = struct.unpack("<IHH", b[4:12])
    campos, pos = [], 32
    while b[pos] != 0x0D:
        nome = b[pos:pos + 11].split(b"\0")[0].decode("latin-1")
        tipo, largura, dec = chr(b[pos + 11]), b[pos + 16], b[pos + 17]
        campos.append((nome, tipo, largura, dec))
        pos += 32
    out, pos = [], cab
    cod = "utf-8"
    for _ in range(n):
        reg = b[pos:pos + tam]; pos += tam
        d, p = {}, 1
        for nome, tipo, largura, dec in campos:
            bruto = reg[p:p + largura]; p += largura
            try:
                s = bruto.decode(cod).strip()
            except UnicodeDecodeError:
                s = bruto.decode("latin-1").strip()
            if tipo in "NF":
                try:
                    v = float(s) if (dec or "." in s or "e" in s.lower()) else int(s)
                except ValueError:
                    v = None
                d[nome] = v
            else:
                d[nome] = s
        out.append(d)
    return out


def area_assinada(r):
    x, y = r[:, 0], r[:, 1]
    return 0.5 * float(np.dot(x[:-1], y[1:]) - np.dot(x[1:], y[:-1]))


def ler(base):
    base = str(base)
    attrs = ler_dbf(base + ".dbf")
    b = Path(base + ".shp").read_bytes()
    pos, feicoes = 100, []
    while pos < len(b):
        _, comp = struct.unpack(">II", b[pos:pos + 8]); pos += 8
        fim = pos + comp * 2
        tipo = struct.unpack("<i", b[pos:pos + 4])[0]
        polis = []
        if tipo in (5, 15, 25):
            npartes, npts = struct.unpack("<ii", b[pos + 36:pos + 44])
            partes = np.frombuffer(b, "<i4", npartes, pos + 44)
            pts = np.frombuffer(b, "<f8", npts * 2, pos + 44 + 4 * npartes).reshape(-1, 2)
            limites = list(partes) + [npts]
            for i in range(npartes):
                r = np.array(pts[limites[i]:limites[i + 1]])
                if len(r) < 4:
                    continue
                if area_assinada(r) < 0 or not polis:   # horário (área negativa) = anel externo
                    polis.append([r])
                else:
                    polis[-1].append(r)
        feicoes.append(polis)
        pos = fim
    return list(zip(attrs, feicoes))
