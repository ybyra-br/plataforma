# Histórico de versões

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
