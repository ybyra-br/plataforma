#!/usr/bin/env python3
"""
ybyra_estatisticas_gee.py · v0.1.1
==================================
Estatísticas por recorte territorial dos assets de emissões e remoções do modelo
YbYrá-BR (projeto CNPq 401741/2023-0), para a plataforma de visualização v1
(somente dados pré-processados, sem login).

Método (adaptado do MapBiomas user-toolkit, mapbiomas-user-toolkit-calculate-area*.js):
  1. O recorte vira um RASTER de identificadores inteiros (ee.Image.paint).
  2. Empilha-se [área do pixel] + [bandas Mg CO₂ pixel⁻¹] + [densidades × área] + [identificador].
  3. Uma única reduceRegion com ee.Reducer.sum().repeat(n).group(...) devolve a soma
     de todas as bandas para todos os identificadores de uma vez.
  4. O resultado é achatado em tabela (uma linha por recorte × ano) e exportado.

Diferenças em relação ao MapBiomas:
  - O MapBiomas agrupa ÁREA por CLASSE (mapa categórico). Aqui as bandas são
    contínuas (fluxos e estoques de carbono) e já vêm por pixel; somamos cada uma.
  - Unidade territorial atômica município × bioma: UF, bioma, UF × bioma e Brasil
    são agregados depois, em Python (ybyra_estatisticas_agregar.py). A soma dos
    municípios fecha exatamente com a da UF e a do Brasil.
  - O Brasil é dividido numa grade de 4° × 4° (partição; cada pixel cai em uma só
    célula). As somas parciais de cada célula são adicionadas no pós-processamento.
    Isso evita estouro de memória com ~11 mil grupos × 25 bandas.
  - Recortes que se sobrepõem entre si (UCs, por exemplo) são calculados feição a
    feição, como no script "using-vector" do MapBiomas.

Uso:
  python ybyra_estatisticas_gee.py --inspecionar            # bandas, anos, unidades
  python ybyra_estatisticas_gee.py --teste                  # 1 célula pequena, getInfo
  python ybyra_estatisticas_gee.py --exportar               # todos os recortes e anos
  python ybyra_estatisticas_gee.py --exportar --recortes municipio_bioma --anos 2020 2021

Histórico de versões
  0.1.1 (2026-10-21) — unidades confirmadas do asset emissions_removals_v1_2:
                       bandas *_co2 já em Mg CO₂ pixel⁻¹ (ano⁻¹) → soma direta;
                       *_co2_ha (derivadas) excluídas por redundância; densidades
                       sem par por pixel (agc_sf_ha, agc0_state; Mg C ha⁻¹) × área
                       do pixel → estoques totais em Mg C (agc_sf_mgc, agc0_mgc).
                       Removida a opção DENSIDADE_POR_HA.
  0.1.0 (2026-10-21) — versão inicial: unidade atômica município × bioma em grade,
                       recortes sobrepostos feição a feição, exportação CSV por
                       recorte × ano para o Google Drive.
"""
import argparse
import sys

import ee

VERSAO_SCRIPT = "0.1.1"

# ----------------------------------------------------------------------------
# Configuração
# ----------------------------------------------------------------------------
PROJETO_GEE = "ee-redd-brazil"
ASSET_MODELO = "projects/ee-redd-brazil/assets/ybyra-br-model/emissions_removals_v1_2"
VERSAO_MODELO = "v1_2"

# Unidades do asset (confirmadas, só CO₂, sem CH₄/N₂O):
#   *_co2           Mg CO₂ pixel⁻¹ ano⁻¹ (fluxos: edge, fire, defor, logging, total_primary,
#                   defor_sf, removal_sf) — somar direto dá Mg CO₂ ano⁻¹ no recorte.
#   agc_sf_co2      Mg CO₂ pixel⁻¹ — ESTOQUE instantâneo da secundária (soma direta).
#   *_co2_ha        Mg CO₂ ha⁻¹ ano⁻¹ — derivadas (banda/pixelAreaHa): excluídas, redundantes.
#   agc_sf_ha       Mg C ha⁻¹ — densidade de estoque da secundária: × área (ha) → Mg C.
#   agc0_state      Mg C ha⁻¹ — estado do estoque primário: × área (ha) → Mg C.
# Bandas somadas direto (None = todas as que terminam em "_co2"):
BANDAS_POR_PIXEL = None
# Bandas em densidade por hectare: origem -> nome de saída (multiplicadas pela área do pixel)
BANDAS_DENSIDADE = {"agc_sf_ha": "agc_sf_mgc", "agc0_state": "agc0_mgc"}
BANDAS_EXCLUIR = []

# None = anos lidos de system:time_start da coleção.
ANOS = None

PASTA_DRIVE = "YBYRA-ESTATISTICAS"
TILE_SCALE = 4
MAX_PIXELS = 1e13
PASSO_GRADE = 4  # graus
BBOX_BRASIL = (-74.5, -34.5, -28.5, 5.5)  # oeste, sul, leste, norte (inclui ilhas oceânicas)

# Malhas territoriais (enviar como assets; atributos IBGE 2025 / IBGE 2019) >>> CONFIRMAR <<<
ASSET_MUNICIPIOS = "projects/ee-redd-brazil/assets/territorios/BR_Municipios_2025"
ATRIB_MUNICIPIO = "CD_MUN"        # código IBGE de 7 dígitos (texto na malha 2025)
ASSET_BIOMAS = "projects/ee-redd-brazil/assets/territorios/Biomas_250mil_2019"
ATRIB_BIOMA = "CD_Bioma"          # 1 Amazônia · 2 Caatinga · 3 Cerrado · 4 Mata Atlântica · 5 Pampa · 6 Pantanal

# Recortes independentes: nome -> (asset, atributo identificador numérico ou texto numérico, sobrepoe)
# sobrepoe=True: calcula feição a feição (as feições se sobrepõem entre si).
RECORTES_EXTRA = {
    "terra_indigena": ("projects/ee-redd-brazil/assets/territorios/TI_FUNAI", "terrai_cod", True),
    "unidade_conservacao": ("projects/ee-redd-brazil/assets/territorios/UC_CNUC", "id_uc", True),
    "territorio_quilombola": ("projects/ee-redd-brazil/assets/territorios/Quilombolas_INCRA", "id_qui", True),
    "assentamento": ("projects/ee-redd-brazil/assets/territorios/Assentamentos_INCRA", "id_ass", False),
}


# ----------------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------------
def inicializar():
    ee.Initialize(project=PROJETO_GEE)


def colecao():
    return ee.ImageCollection(ASSET_MODELO)


def resolver_bandas():
    """Plano de bandas: (somadas direto, {densidade: nome de saída}), validado contra o asset."""
    nomes = colecao().first().bandNames().getInfo()
    por_pixel = BANDAS_POR_PIXEL or [b for b in nomes if b.endswith("_co2")]
    por_pixel = [b for b in por_pixel if b not in BANDAS_EXCLUIR]
    dens = {o: d for o, d in BANDAS_DENSIDADE.items() if o in nomes and o not in BANDAS_EXCLUIR}
    faltam = [b for b in por_pixel if b not in nomes] + [o for o in BANDAS_DENSIDADE if o not in nomes]
    if faltam:
        print(f"AVISO: bandas configuradas ausentes no asset: {faltam}")
    ignoradas = [b for b in nomes if b not in por_pixel and b not in dens]
    return por_pixel, dens, ignoradas


def nomes_saida(plano):
    por_pixel, dens = plano
    return por_pixel + list(dens.values())


def resolver_anos():
    if ANOS:
        return list(ANOS)
    anos = (colecao().aggregate_array("system:time_start")
            .map(lambda t: ee.Date(t).get("year")).distinct().sort().getInfo())
    if not anos:
        sys.exit("Imagens sem system:time_start: defina ANOS manualmente.")
    return [int(x) for x in anos]


def projecao_nativa():
    """CRS e transformação do asset: reduz sem reamostrar."""
    info = colecao().first().select(0).projection().getInfo()
    return info["crs"], info["transform"]


def imagem_ano(ano, plano):
    """[área (ha)] + [bandas por pixel] + [densidades × área]; pixel sem dado = 0."""
    por_pixel, dens = plano
    img = ee.Image(colecao().filter(ee.Filter.calendarRange(ano, ano, "year")).first()).unmask(0)
    area_ha = ee.Image.pixelArea().divide(1e4).rename("area_ha")
    out = area_ha.addBands(img.select(por_pixel))  # Mg CO₂ pixel⁻¹: soma direta
    for origem, destino in dens.items():           # Mg C ha⁻¹ × ha = Mg C
        out = out.addBands(img.select(origem).multiply(area_ha).rename(destino))
    return out  # 1ª banda = área (controle de qualidade e intensidade)


def com_id_numerico(fc, atributo):
    return fc.map(lambda f: f.set("id_num", ee.Number.parse(ee.String(f.get(atributo)))))


def raster_ids(fc):
    return ee.Image().int64().paint(fc, "id_num").rename("zona")


def grade_brasil():
    o, s, l, n = BBOX_BRASIL
    celulas = []
    x = o
    while x < l:
        y = s
        while y < n:
            celulas.append(ee.Feature(ee.Geometry.Rectangle([x, y, x + PASSO_GRADE, y + PASSO_GRADE],
                                                            "EPSG:4326", False)))
            y += PASSO_GRADE
        x += PASSO_GRADE
    return ee.FeatureCollection(celulas)


def reduzir(empilhado, zona, geometria, nomes_saida, crs, transform):
    """Soma todas as bandas por identificador de zona dentro da geometria."""
    n = len(nomes_saida)
    redutor = ee.Reducer.sum().repeat(n).group(groupField=n, groupName="zona")
    out = empilhado.addBands(zona).updateMask(zona.mask()).reduceRegion(
        reducer=redutor, geometry=geometria, crs=crs, crsTransform=transform,
        maxPixels=MAX_PIXELS, tileScale=TILE_SCALE)
    grupos = ee.List(ee.Dictionary(out).get("groups", ee.List([])))

    def linha(g):
        g = ee.Dictionary(g)
        props = ee.Dictionary.fromLists(nomes_saida, ee.List(g.get("sum"))).set("zona", g.get("zona"))
        return ee.Feature(None, props)

    return ee.FeatureCollection(grupos.map(linha))


# ----------------------------------------------------------------------------
# Recortes
# ----------------------------------------------------------------------------
def zona_municipio_bioma():
    """Identificador atômico = código IBGE do município × 10 + código do bioma (0 = sem bioma)."""
    mun = raster_ids(com_id_numerico(ee.FeatureCollection(ASSET_MUNICIPIOS), ATRIB_MUNICIPIO))
    bio = raster_ids(com_id_numerico(ee.FeatureCollection(ASSET_BIOMAS), ATRIB_BIOMA)).unmask(0)
    return mun.multiply(10).add(bio).rename("zona")


def tabela_municipio_bioma(ano, plano, crs, transform, celulas=None):
    nomes = ["area_ha"] + nomes_saida(plano)
    emp = imagem_ano(ano, plano)
    zona = zona_municipio_bioma()
    celulas = celulas or grade_brasil()
    fc = celulas.map(lambda c: reduzir(emp, zona, c.geometry(), nomes, crs, transform)).flatten()
    return fc.map(lambda f: f.set("ano", ano))


def tabela_recorte_extra(nome, ano, plano, crs, transform):
    asset, atributo, sobrepoe = RECORTES_EXTRA[nome]
    fc = com_id_numerico(ee.FeatureCollection(asset), atributo)
    nomes = ["area_ha"] + nomes_saida(plano)
    emp = imagem_ano(ano, plano)
    if sobrepoe:
        def por_feicao(f):
            zona = raster_ids(ee.FeatureCollection([f]))
            return reduzir(emp, zona, f.geometry(), nomes, crs, transform)
        out = fc.map(por_feicao).flatten()
    else:
        zona = raster_ids(fc)
        out = grade_brasil().map(lambda c: reduzir(emp, zona, c.geometry(), nomes, crs, transform)).flatten()
    return out.map(lambda f: f.set("ano", ano))


def exportar(nome, fc, ano, bandas):
    desc = f"ybyra_{VERSAO_MODELO}_{nome}_{ano}"
    tarefa = ee.batch.Export.table.toDrive(
        collection=fc, description=desc, folder=PASTA_DRIVE, fileNamePrefix=desc,
        fileFormat="CSV", selectors=["zona", "ano", "area_ha"] + bandas)
    tarefa.start()
    print(f"  tarefa iniciada: {desc}")


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inspecionar", action="store_true", help="mostra bandas, anos e projeção")
    ap.add_argument("--teste", action="store_true", help="roda 1 célula pequena com getInfo")
    ap.add_argument("--exportar", action="store_true", help="inicia as tarefas de exportação")
    ap.add_argument("--recortes", nargs="*", default=None, help="municipio_bioma e/ou chaves de RECORTES_EXTRA")
    ap.add_argument("--anos", nargs="*", type=int, default=None)
    a = ap.parse_args()

    inicializar()
    print(f"ybyra_estatisticas_gee v{VERSAO_SCRIPT} · modelo {VERSAO_MODELO}")
    por_pixel, dens, ignoradas = resolver_bandas()
    plano = (por_pixel, dens)
    bandas = nomes_saida(plano)
    anos = a.anos or resolver_anos()
    crs, transform = projecao_nativa()

    if a.inspecionar or not (a.teste or a.exportar):
        primeira = colecao().first()
        print(f"Imagens: {colecao().size().getInfo()} · anos: {anos[0]}–{anos[-1]} ({len(anos)})")
        print(f"Projeção: {crs} {transform}")
        print(f"Somadas direto, Mg CO₂ pixel⁻¹ ({len(por_pixel)}): {por_pixel}")
        print(f"Densidade × área → Mg C: {dens}")
        print(f"Ignoradas (derivadas _ha ou não aditivas): {ignoradas}")
        print("Propriedades da 1ª imagem:", primeira.propertyNames().getInfo())
        return

    if a.teste:
        # célula de 0,5° no Maranhão (Ilha do Maranhão e entorno)
        celula = ee.FeatureCollection([ee.Feature(ee.Geometry.Rectangle([-44.5, -3.0, -44.0, -2.5], "EPSG:4326", False))])
        ano = anos[-1]
        fc = tabela_municipio_bioma(ano, plano, crs, transform, celulas=celula)
        linhas = fc.limit(20).getInfo()["features"]
        print(f"Teste {ano}: {len(linhas)} zonas (município×bioma) na célula")
        for f in linhas:
            p = f["properties"]
            print(f"  zona {p['zona']}: área {p['area_ha']:.0f} ha · "
                  + ", ".join(f"{b}={p.get(b, 0):.4g}" for b in bandas[:4]) + (" …" if len(bandas) > 4 else ""))
        return

    recortes = a.recortes or (["municipio_bioma"] + list(RECORTES_EXTRA))
    for nome in recortes:
        print(f"Recorte: {nome}")
        for ano in anos:
            if nome == "municipio_bioma":
                fc = tabela_municipio_bioma(ano, plano, crs, transform)
            elif nome in RECORTES_EXTRA:
                fc = tabela_recorte_extra(nome, ano, plano, crs, transform)
            else:
                sys.exit(f"Recorte desconhecido: {nome}")
            exportar(nome, fc, ano, bandas)
    print("Acompanhe em https://code.earthengine.google.com/tasks")


if __name__ == "__main__":
    main()
