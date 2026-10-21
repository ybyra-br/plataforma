# Histórico de versões

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
