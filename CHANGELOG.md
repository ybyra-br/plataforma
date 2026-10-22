# Histórico de versões

## 0.6.3 — 2026-10-22
- `gee/ybyra_estatisticas.js` v0.3.1: shapefiles só com as partes poligonais de cada feição; algumas feições das malhas do MapBiomas (estados, quilombos, bacias) misturam polígonos e linhas, e o shapefile não aceita os dois tipos juntos.

## 0.6.2 — 2026-10-22
- `gee/ybyra_estatisticas.js` v0.3.0: todos os recortes ligados (terras indígenas, unidades de conservação, quilombos, Amazônia Legal, MATOPIBA, bacias DHN250 níveis 1 e 2), além de município × bioma; novo modo `tudo`, que cria numa só execução as tarefas de estatística e as de shapefile; 13 anos por tarefa.

## 0.6.1 — 2026-10-22
- `gee/ybyra_estatisticas.js` v0.2.0: malhas territoriais públicas do MapBiomas (`projects/mapbiomas-territories`, as mesmas do user-toolkit) no lugar dos caminhos provisórios: municípios e estados IBGE 2025, biomas IBGE 2025, terras indígenas FUNAI 2026, unidades de conservação CNUC 2026, quilombos INCRA 2026, Amazônia Legal, MATOPIBA e bacias DHN250 níveis 1 e 2. Atributos detectados no próprio asset e listados no modo `inspecionar`.
- Novo modo `geometrias`: exporta todas as malhas em shapefile (colunas `id`, `nome` e, nos municípios, `sigla_uf`), com simplificação opcional, para o mapa da plataforma.

## 0.6.0 — 2026-10-22
- **Painéis recolhíveis**, como na plataforma de queimadas: botão de esconder no painel Explorar (‹) e no painel do recorte (›); com o painel escondido, aparecem os botões **Painel** e **Gráficos** no alto do mapa para reabrir. Zoom, camadas, escala e créditos acompanham, e o mapa se reenquadra no espaço livre. A escolha fica salva no navegador. No celular os painéis continuam empilhados sob o mapa.
- Painel esquerdo ganha o título "Explorar".

## 0.5.4 — 2026-10-22
- Correção do piscar da barra superior e dos painéis durante o zoom: o desfoque de fundo (`backdrop-filter`) era recalculado a cada quadro do mapa (WebGL). Desfoque removido de tudo que fica sobre o mapa, materiais quase opacos (97–98%) e camadas de composição próprias (`translateZ(0)`, `contain:paint`; mapa com `contain:strict`). Mesma correção da plataforma de queimadas (v0.14.1).
- Link **Alerta de Queimadas** na barra superior, que leva à plataforma Alerta de Queimadas por Município; no celular aparece como ícone.
- Correção dos tokens do tema escuro escolhido manualmente (fundo do espaço do globo ausente).

## 0.5.3 — 2026-10-21
- Correção: os comandos do botão de camadas tinham ido parar dentro da função que atualiza os controles (eram recriados a cada mudança e o Esc não fechava o painel).
- Correção: o painel de camadas ficava sempre aberto. Faltava a regra global `[hidden]{display:none!important}` (o ambiente de prévia a incluía, o GitHub Pages não); a caixa de ranking tinha o mesmo problema.

## 0.5.2 — 2026-10-21
- Mapa de fundo e projeção saem do painel lateral e vão para um **botão de camadas sobre o mapa**, junto ao zoom, que abre a lista de fundos (com marca de seleção) e a escolha entre globo e plano.
- Seta de norte removida; a barra de escala continua.

## 0.5.1 — 2026-10-21
- **Mapas de fundo em lista suspensa**, todos gratuitos e sem chave de API (testados em 21/10/2026):
  - Mapas: Cinza da Esri (claro ou escuro conforme o tema), OpenStreetMap, Topográfico da Esri, Relevo do OpenTopoMap;
  - Satélite: imagem de alta resolução da Esri (World Imagery) e Sentinel-2 sem nuvens 2024 da EOX, ambos com rótulos de limites e lugares por cima;
  - Nenhum.
- Créditos de cada fonte no rodapé do mapa, trocados junto com o fundo.

## 0.5.0 — 2026-10-21
- **Globo**: mapa em projeção de globo com atmosfera (MapLibre GL JS 5.6.0), com opção de mapa plano; a escolha fica salva no navegador.
- **Mapa de fundo**: Mapa (Esri cinza claro ou escuro conforme o tema, com rótulos por cima dos recortes; o CARTO passou a exigir chave de API), Satélite (Sentinel-2 cloudless, EOX) ou Nenhum.
- **Elementos cartográficos**: seta de norte e barra de escala que se ajusta ao zoom e à latitude.
- **Créditos no rodapé do mapa**: MapLibre, mapa de fundo (OpenStreetMap/CARTO ou EOX/Copernicus), malhas do IBGE e dados do modelo YbYrá-BR.
- **Variáveis em lista suspensa**, agrupada em Saldo, Emissões, Remoções e Estoques, com a cor da escala ao lado.
- **Marca do YbYrá-BR toda branca no tema escuro** (barra superior e relatório), como a do CNPq; na impressão, sempre a versão colorida.

## 0.4.1 — 2026-10-21
- Documento HTML completo (`<!doctype>`, `lang="pt-BR"`, `charset`, `viewport`, `theme-color`, ícone): sem a meta viewport o celular desenhava a página com 980 px de largura e o mapa ficava escondido atrás dos painéis.

## 0.4.0 — 2026-10-21
Revisão da interface pelas Apple Human Interface Guidelines:
- **Camadas**: o mapa passa por baixo da barra superior em vidro; o painel de controles (Explorar) é vidro e o painel de conteúdo (recorte) usa material regular, mais opaco, para leitura de gráficos e números.
- **Alvos e estados**: 44 px em telas de toque (segmentos, variáveis, ranking, botões, zoom, busca); estado pressionado em todos os botões.
- **Tipografia**: tamanhos em rem, que acompanham o tamanho de texto do navegador; 17 px de base em telas de toque; nada abaixo de 11 px (legenda e eixos dos gráficos).
- **Cor e acessibilidade**: emissão líquida em escala verde-azulado ↔ vermelho (sem o par vermelho-verde); remoções em verde-azulado; modos de alto contraste e de transparência reduzida; movimento reduzido também nas animações do mapa; descrição textual dos gráficos para leitores de tela; busca como combobox acessível.
- **Componentes**: cantos concêntricos (painel 22 px com margem de 12 px → cartões de 10 px); símbolos no zoom e no fechar; relatório e método como folhas, com fechar no início e ação principal no fim; marca de seleção na lista de variáveis; setas de navegação no ranking e na trilha; atalhos `/` e ⌘K para a busca; indicador de carregamento.

## 0.3.0 — 2026-10-21
- **GEE em JavaScript**: `gee/ybyra_estatisticas.js` v0.1.0 (Code Editor) substitui o script em Python; modos inspecionar, teste e exportar; tarefas por lotes de anos.
- **Agregação em R no GitHub Actions**: `R/agregar.R` v0.1.0 lê `dados/brutos/v1_2/*.csv[.gz]`, agrega, confere e grava os arquivos do site a cada envio; `web/dados/` deixa de ser versionado.
- Tabela longa completa publicada no site (`dados/v1_2/estatisticas.csv.gz`).
- Workflow `conferir-r-python` e `scripts/comparar_saidas.py` para validar o R contra a versão em Python.
- README e CHANGELOG restaurados (tinham sido esvaziados por engano na 0.2.4).

## 0.2.4 — 2026-10-21
- Relatório: concordância "no Brasil" no resumo automático.

## 0.2.3 — 2026-10-21
- Mapa: linha da mesma cor do preenchimento veda as frestas entre polígonos municipais simplificados; contornos municipais só no recorte Municípios.
- Emissão líquida: escala divergente com três classes por lado (terços dos valores absolutos) e faixa neutra perto de zero.

## 0.2.2 — 2026-10-21
- Repositório na organização do projeto: `ybyra-br/plataforma`, site em https://ybyra-br.github.io/plataforma/.

## 0.2.1 — 2026-10-21
- Repositório no GitHub com publicação automática da pasta `web/` no GitHub Pages (`.github/workflows/pages.yml`).
- Link "Código aberto" na barra superior.

## 0.2.0 — 2026-10-21
- **Relatório do recorte**: resumo escrito automaticamente, indicadores do ano, gráficos de processos e estoques, série anual em tabela, ranking dos sub-recortes e citação; imprimível ou salvável em PDF no site publicado.
- Página de Método em branco ("Em preparação").

## 0.1.0 — 2026-10-21
- Primeira versão da plataforma com **dados fictícios**: mapa MapLibre por Brasil, estado, bioma e município; variáveis de emissão, remoção, saldo e estoques; total ou por hectare; seletor e animação de anos; busca; painel do recorte com indicadores, barras por processo (Okabe-Ito), estoques e ranking de sub-recortes; cópia da série em CSV.
- Pipeline: `ybyra_estatisticas_gee.py` v0.1.1 (estatísticas por recorte no GEE, padrão MapBiomas), `ybyra_estatisticas_agregar.py` v0.2.0 (agregação e arquivos estáticos), `preparar_malhas.py` v0.1.1 (malhas e contornos), `gerar_dados_ficticios.py` v0.1.0.
