# Emissões e Remoções de CO₂ — YbYrá-BR · v0.6.0

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
3. Substitua o conteúdo de `dados/brutos/v1_2/` pelos CSV reais (pelo site do GitHub: *Add file → Upload files*, ou por git). Apague os arquivos fictícios.
4. O envio dispara o workflow `pages`: o R agrega, confere o fechamento dos totais e publica o site. A tabela longa completa fica em `dados/v1_2/estatisticas.csv.gz` no site.

Local: `Rscript R/agregar.R dados/brutos/v1_2 web/dados/v1_2 v1_2 web/geo/municipios.geojson` e depois `python -m http.server -d web`.

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
scripts/ybyra_estatisticas_agregar.py  versão anterior em Python, mantida só para conferir o R
scripts/comparar_saidas.py             compara as saídas do R e do Python
scripts/preparar_malhas.py             municípios simplificados e contornos de UF, bioma e Brasil
scripts/gerar_dados_ficticios.py       dados fictícios no formato do export do GEE
dados_ficticios/                       bioma predominante e nomes usados na prévia
web/index.html                         plataforma
web/dados/v1_2/                        gerado no Actions: catálogo, mapas (por variável), séries (por UF), tabela longa
web/geo/                               geometrias do mapa
```

## Como citar

Silva-Junior, C. H. L. (2026). Emissões e Remoções de CO₂ por recorte territorial — modelo YbYrá-BR (prévia). Projeto YbYrá-BR, CNPq 401741/2023-0. https://github.com/ybyra-br/plataforma
