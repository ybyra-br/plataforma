# Emissões e Remoções de CO₂ — YbYrá-BR

Plataforma pública do projeto **YbYrá-BR** (CNPq, processo 401741/2023-0) para consultar as emissões e remoções de CO₂ da vegetação nativa brasileira, ano a ano, de 1986 a 2024, em diferentes recortes do território.

**Acesse:** https://ybyra-br.github.io/plataforma/

> Versão de prévia com os resultados do modelo YbYrá-BR v1.2. A descrição completa do método será publicada em breve na seção *Método* da plataforma.

## O que a plataforma mostra

- **Processos de emissão:** desmatamento de floresta primária, fogo em floresta, efeito de borda, exploração madeireira e desmatamento de vegetação secundária.
- **Remoção:** crescimento da vegetação secundária.
- **Saldos:** emissão bruta (soma dos processos) e emissão líquida (bruta − remoção).
- **Estoques de carbono acima do solo:** vegetação secundária e floresta primária.

Todos os valores podem ser vistos em total (Mg, kt, Mt ou Gt de CO₂ por ano) ou por hectare.

### Recortes territoriais

| Grupo | Recortes |
|---|---|
| Divisão político-administrativa | Brasil, estados, municípios |
| Regiões | Biomas, Amazônia Legal, MATOPIBA |
| Bacias hidrográficas | Divisão Hidrográfica Nacional (ANA), níveis 1 e 2 |
| Áreas protegidas e territórios | Terras indígenas, unidades de conservação, territórios quilombolas |

As estatísticas de estados, biomas e do Brasil são a soma exata das zonas município × bioma. Os recortes que se sobrepõem (terras indígenas, unidades de conservação e territórios quilombolas) são calculados feição a feição.

### Recursos

- Mapa em globo ou plano, com mapas de fundo e imagem de satélite.
- Busca por nome em todos os recortes.
- Série anual por processo, indicadores do ano, estoques e ranking dos sub-recortes.
- Relatório para impressão, cópia da série em CSV e citação pronta.
- Aparência clara, escura ou automática; uso por teclado e leitores de tela.

## Dados

- **Tabela completa:** [`dados/v1_2/estatisticas.csv.gz`](https://ybyra-br.github.io/plataforma/dados/v1_2/estatisticas.csv.gz), em formato longo (`tipo, id, ano, variavel, valor`), com todos os recortes, anos e variáveis.
- **Unidades:** fluxos em Mg CO₂ ano⁻¹; estoque da vegetação secundária em Mg CO₂; estoque da floresta primária em Mg C. Somente CO₂ (sem CH₄ e N₂O).
- **Identificadores:** códigos IBGE para municípios e estados, códigos IBGE de 1 a 6 para biomas e identificadores das bases de origem para os demais recortes.

### Limites territoriais

Malhas públicas disponibilizadas pelo [MapBiomas](https://brasil.mapbiomas.org): municípios, estados e biomas (IBGE), terras indígenas (FUNAI), unidades de conservação (CNUC/MMA), territórios quilombolas (INCRA), bacias hidrográficas (ANA), Amazônia Legal e MATOPIBA (EMBRAPA).

## Como o processamento funciona

1. As estatísticas zonais são calculadas no Google Earth Engine sobre os mapas anuais do modelo, em 30 m (`gee/`).
2. A agregação hierárquica e a conferência dos totais são feitas em R (`R/agregar.R`), a cada atualização dos dados, via GitHub Actions.
3. O site é estático (MapLibre GL, PMTiles e Chart.js) e publicado no GitHub Pages (`web/`).

O código é aberto. O histórico de versões está em [`CHANGELOG.md`](CHANGELOG.md).

## Como citar

Silva-Junior, C. H. L. (2026). *Emissões e Remoções de CO₂ por recorte territorial — modelo YbYrá-BR* (versão de prévia). Projeto YbYrá-BR, CNPq 401741/2023-0. https://ybyra-br.github.io/plataforma/

## Apoio

Conselho Nacional de Desenvolvimento Científico e Tecnológico (CNPq), processo 401741/2023-0.

Dúvidas, correções e sugestões: abra uma [issue](https://github.com/ybyra-br/plataforma/issues).
