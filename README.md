# Emissões e Remoções de CO₂ — YbYrá-BR · v0.2.2

Plataforma do projeto **YbYrá-BR** (CNPq, processo 401741/2023-0) para explorar as emissões e remoções de CO₂ do modelo YbYrá-BR por recorte territorial: Brasil, estados, biomas e municípios.

> **Prévia com dados fictícios.** A estrutura, os cálculos e os formatos de arquivo são os definitivos; os números serão substituídos pelos resultados do modelo.

Site: https://ybyra-br.github.io/plataforma/

## Fluxo

```
GEE: emissions_removals_v1_2 (30 m, Mg CO₂ pixel⁻¹ ano⁻¹)
  └─ scripts/ybyra_estatisticas_gee.py      soma por município × bioma (padrão MapBiomas) → CSV no Drive
       └─ scripts/ybyra_estatisticas_agregar.py   UF, bioma, UF × bioma, Brasil; conferência; JSON estáticos
            └─ web/                                site estático (MapLibre + Chart.js) no GitHub Pages
```

1. No GEE (projeto `ee-redd-brazil`): `python scripts/ybyra_estatisticas_gee.py --inspecionar`, depois `--teste` e `--exportar`.
2. Baixe os CSV da pasta `YBYRA-ESTATISTICAS` do Drive para `csv/`.
3. `python scripts/ybyra_estatisticas_agregar.py --entrada csv --saida web/dados/v1_2 --modelo v1_2 --nomes nomes/`
4. Envie ao `main`: o GitHub Actions publica `web/` no Pages.

Dados fictícios (para desenvolvimento): `python scripts/gerar_dados_ficticios.py web/geo/municipios.geojson <repo-queimadas> dados_ficticios/csv dados_ficticios/nomes` e depois o passo 3 com `--entrada dados_ficticios/csv --nomes dados_ficticios/nomes`.

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
scripts/ybyra_estatisticas_gee.py      estatísticas por recorte no Earth Engine
scripts/ybyra_estatisticas_agregar.py  agregação hierárquica e arquivos do site
scripts/preparar_malhas.py             municípios simplificados e contornos de UF, bioma e Brasil
scripts/gerar_dados_ficticios.py       dados fictícios no formato do export do GEE
dados_ficticios/                       bioma predominante e nomes usados na prévia
web/index.html                         plataforma
web/dados/v1_2/                        catálogo, mapas (por variável) e séries (por UF)
web/geo/                               geometrias do mapa
```

## Como citar

Silva-Junior, C. H. L. (2026). Emissões e Remoções de CO₂ por recorte territorial — modelo YbYrá-BR (prévia). Projeto YbYrá-BR, CNPq 401741/2023-0. https://github.com/ybyra-br/plataforma
