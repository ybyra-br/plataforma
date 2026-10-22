# Emissões e Remoções de CO₂ — YbYrá-BR · v0.8.0

Plataforma do projeto **YbYrá-BR** (CNPq, processo 401741/2023-0) para explorar as emissões e remoções de CO₂ do modelo YbYrá-BR por recorte territorial: Brasil, estados, biomas e municípios.

> **Prévia com dados fictícios.** A estrutura, os cálculos e os formatos de arquivo são os definitivos; os números serão substituídos pelos resultados do modelo.

Site: https://ybyra-br.github.io/plataforma/

## Fluxo

```
GEE (Code Editor, projeto ee-redd-brazil)
  └─ gee/ybyra_estatisticas.js        soma por município × bioma (padrão MapBiomas) → CSV no Drive
       └─ dados/brutos/v1_2/*.csv[.gz]     você envia os CSV para esta pasta do repositório
            └─ R/agregar.R                  (GitHub Actions) UF, bioma, UF × bioma, Brasil; conferência; JSON
                 └─ web/                     site estático (MapLibre + Chart.js) no GitHub Pages
```

1. No Code Editor do GEE, abra `gee/ybyra_estatisticas.js` e rode com `MODO = 'inspecionar'`, depois `'teste'` e `'exportar'` (clique RUN em cada tarefa na aba Tasks).
2. Baixe os CSV da pasta `YBYRA-ESTATISTICAS` do Drive.
3. Em `dados/brutos/v1_2/`, **apague todos os arquivos** (os CSV fictícios e o `FICTICIOS.txt`) e envie os CSV reais (pelo site do GitHub: *Add file → Upload files*, ou por git). Arquivos acima de 25 MB não sobem pelo site: compacte em `.csv.gz` (o R lê os dois) ou use git. O aviso de dados fictícios some sozinho quando o `FICTICIOS.txt` sai.
4. O envio dispara o workflow `pages`: o R agrega, confere o fechamento dos totais e publica o site. A tabela longa completa fica em `dados/v1_2/estatisticas.csv.gz` no site.

Local: `Rscript R/agregar.R dados/brutos/v1_2 web/dados/v1_2 v1_2 web/geo/indice.json` e depois `python -m http.server -d web`.

Malhas do mapa: rode o GEE com `MODO = 'geometrias'`, baixe a pasta `YBYRA-GEOMETRIAS` e gere as camadas com `python scripts/gerar_pmtiles.py <pasta> [nomes_municipios.json] [recortes...]`.

Os dados fictícios atuais vêm de `scripts/gerar_dados_ficticios.py` (mesmo formato do export do GEE).

## Unidades

| Bandas | Tratamento | Resultado por recorte |
|---|---|---|
| `*_co2` (edge, fire, defor, logging, total_primary, defor_sf, removal_sf) | soma direta | Mg CO₂ ano⁻¹ |
| `agc_sf_co2` | soma direta | estoque, Mg CO₂ |
| `*_co2_ha` | não somadas (derivadas) | — |
| `agc_sf_ha`, `agc0_state` (Mg C ha⁻¹) | × área do pixel e soma | estoque, Mg C |

Somente CO₂ (sem CH₄ e N₂O).

## Estrutura

```
gee/ybyra_estatisticas.js              estatísticas por recorte no Earth Engine (Code Editor)
R/agregar.R                            agregação hierárquica e arquivos do site (roda no GitHub Actions)
dados/brutos/v1_2/                     CSV exportados do GEE (hoje: fictícios)
scripts/ler_shp.py                     leitor mínimo de shapefile (polígonos) e dbf
scripts/gerar_pmtiles.py               malhas do GEE (shapefiles) → web/geo/<recorte>.pmtiles + indice.json
scripts/gerar_ficticios_extras.py      dados fictícios dos recortes extras (TI, UC, quilombos, regiões, bacias)
scripts/gerar_dados_ficticios.py       dados fictícios no formato do export do GEE
dados_ficticios/                       bioma predominante e nomes usados na prévia
web/index.html                         plataforma
web/dados/v1_2/                        gerado no Actions: catálogo, mapas (por variável), séries (por UF), tabela longa
web/geo/                               malhas do mapa em PMTiles (uma por recorte) e indice.json (id, nome, extensão)
```

## Como citar

Silva-Junior, C. H. L. (2026). Emissões e Remoções de CO₂ por recorte territorial — modelo YbYrá-BR (prévia). Projeto YbYrá-BR, CNPq 401741/2023-0. https://github.com/ybyra-br/plataforma
