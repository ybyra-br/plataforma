#!/usr/bin/env Rscript
# =============================================================================
# agregar.R · v0.1.1
# -----------------------------------------------------------------------------
# Agrega as tabelas exportadas pelo GEE (gee/ybyra_estatisticas.js) e grava os
# arquivos estáticos da plataforma https://ybyra-br.github.io/plataforma/.
# Roda no GitHub Actions a cada envio (.github/workflows/pages.yml).
#
# Entrada : pasta com  ybyra_<modelo>_<recorte>_<ano ou ano-ano>.csv[.gz]
#           (colunas zona, ano, area_ha e as bandas; uma linha por zona × ano × célula da grade)
# Saídas  : <saida>/catalogo.json                  tipos, ids, nomes, variáveis e unidades, anos
#           <saida>/mapa/<tipo>/<variavel>.json    todos os recortes × anos (mapa)
#           <saida>/serie/<tipo>/<lote>.json       séries por lote (UF nos tipos municipais)
#           <saida>/estatisticas.csv.gz            tabela longa (tipo, id, ano, variavel, valor)
#
# Recortes derivados de município × bioma (zona = código IBGE × 10 + bioma):
#   municipio_bioma, municipio, uf, bioma, uf_bioma, brasil.
# Recortes independentes (terra_indigena, unidade_conservacao, ...) entram como vierem.
#
# Uso: Rscript R/agregar.R <entrada> <saida> <modelo> <municipios.geojson>
#
# Histórico de versões
#   0.1.1 (2026-10-22) — catálogo indica dados fictícios (arquivo FICTICIOS.txt na pasta de entrada)
#                        e o período dos anos; nomes de arquivo com qualquer recorte do GEE v0.3.
#   0.1.0 (2026-10-21) — porte para R de ybyra_estatisticas_agregar.py v0.2.0 (mesmo
#                        formato de saída); lê .csv e .csv.gz e nomes de arquivo com
#                        lote de anos; nomes dos municípios vêm da malha do site.
# =============================================================================
suppressPackageStartupMessages({ library(data.table); library(jsonlite) })

VERSAO_SCRIPT <- "0.1.1"
arg <- commandArgs(trailingOnly = TRUE)
if (length(arg) < 4) stop("Uso: Rscript R/agregar.R <entrada> <saida> <modelo> <municipios.geojson>")
ENTRADA <- arg[1]; SAIDA <- arg[2]; MODELO <- arg[3]; GEO <- arg[4]

BIOMAS <- c("0" = "Sem bioma", "1" = "Amazônia", "2" = "Caatinga", "3" = "Cerrado",
            "4" = "Mata Atlântica", "5" = "Pampa", "6" = "Pantanal")
UFS <- c("11" = "RO", "12" = "AC", "13" = "AM", "14" = "RR", "15" = "PA", "16" = "AP", "17" = "TO",
         "21" = "MA", "22" = "PI", "23" = "CE", "24" = "RN", "25" = "PB", "26" = "PE", "27" = "AL",
         "28" = "SE", "29" = "BA", "31" = "MG", "32" = "ES", "33" = "RJ", "35" = "SP", "41" = "PR",
         "42" = "SC", "43" = "RS", "50" = "MS", "51" = "MT", "52" = "GO", "53" = "DF")
LOTE_UF <- list(municipio = function(i) i %/% 100000, municipio_bioma = function(i) i %/% 1000000)
SEM_MAPA <- c("municipio_bioma")
cat(sprintf("agregar.R v%s · modelo %s\n", VERSAO_SCRIPT, MODELO))

# ---------------- leitura ----------------
padrao <- sprintf("^ybyra_%s_(.+?)_(\\d{4})(-\\d{4})?\\.csv(\\.gz)?$", MODELO)
arqs <- list.files(ENTRADA, pattern = padrao, full.names = TRUE)
if (!length(arqs)) stop("Nenhum CSV do modelo ", MODELO, " em ", ENTRADA)
recorte_de <- sub(padrao, "\\1", basename(arqs))
tabelas <- lapply(split(arqs, recorte_de), function(fs) {
  dt <- rbindlist(lapply(fs, fread, showProgress = FALSE), use.names = TRUE, fill = TRUE)
  dt[, intersect(c("system:index", ".geo"), names(dt)) := NULL]
  dt
})
cat(sprintf("  %d arquivos; recortes: %s\n", length(arqs), paste(names(tabelas), collapse = ", ")))
if (!"municipio_bioma" %in% names(tabelas)) stop("Falta o recorte municipio_bioma (base dos níveis hierárquicos).")

variaveis <- setdiff(names(tabelas$municipio_bioma), c("zona", "ano", "area_ha"))
COLS <- c("area_ha", variaveis)

somar <- function(dt, chave) {
  out <- dt[, lapply(.SD, function(x) sum(as.numeric(x), na.rm = TRUE)), by = c(chave, "ano"), .SDcols = COLS]
  setnames(out, chave, "id"); setorder(out, id, ano); out
}

# ---------------- recortes ----------------
mb <- copy(tabelas$municipio_bioma)
mb[, zona := as.numeric(zona)]
mb[, `:=`(municipio = zona %/% 10, bioma = zona %% 10)]
mb[, `:=`(uf = municipio %/% 100000)]
mb[, `:=`(uf_bioma = uf * 10 + bioma, brasil = 1)]
rec <- list(municipio_bioma = somar(mb, "zona"))
for (t in c("municipio", "uf", "bioma", "uf_bioma", "brasil")) rec[[t]] <- somar(mb, t)
for (nm in setdiff(names(tabelas), "municipio_bioma")) {
  dt <- tabelas[[nm]]; dt[, zona := as.numeric(zona)]; rec[[nm]] <- somar(dt, "zona")
}

# ---------------- conferência ----------------
cat("Conferência:\n")
br <- rec$brasil
for (t in c("municipio", "uf", "bioma", "municipio_bioma")) {
  s <- rec[[t]][, lapply(.SD, sum), by = ano, .SDcols = COLS][order(ano)]
  dif <- max(abs(as.matrix(s[, ..COLS]) - as.matrix(br[order(ano), ..COLS])))
  cat(sprintf("  fechamento %16s × brasil: maior diferença absoluta = %.3g\n", t, dif))
}
area_mha <- br$area_ha[1] / 1e6
cat(sprintf("  área total coberta: %.1f Mha (Brasil ≈ 851 Mha)\n", area_mha))
if (area_mha < 840 || area_mha > 860) cat("  ATENÇÃO: área fora do esperado — confira malhas, máscara e projeção.\n")

# ---------------- nomes ----------------
geo <- fromJSON(GEO, simplifyVector = TRUE)$features$properties
nome_mun <- setNames(sprintf("%s (%s)", geo$n, geo$u), as.character(geo$c))
nomes_de <- function(tipo, ids) {
  k <- as.character(ids)
  out <- switch(tipo,
    brasil = rep("Brasil", length(ids)),
    uf = unname(UFS[k]),
    bioma = unname(BIOMAS[k]),
    uf_bioma = sprintf("%s · %s", UFS[as.character(ids %/% 10)], BIOMAS[as.character(ids %% 10)]),
    municipio = unname(nome_mun[k]),
    municipio_bioma = sprintf("%s · %s", nome_mun[as.character(ids %/% 10)], BIOMAS[as.character(ids %% 10)]),
    k)
  out[is.na(out)] <- k[is.na(out)]
  out
}
unidade <- function(v) {
  if (v == "area_ha") return(list(unidade = "ha", natureza = "área"))
  if (v == "agc_sf_co2") return(list(unidade = "Mg CO₂", natureza = "estoque"))
  if (grepl("_mgc$", v)) return(list(unidade = "Mg C", natureza = "estoque"))
  if (grepl("_co2$", v)) return(list(unidade = "Mg CO₂ ano⁻¹", natureza = "fluxo"))
  list(unidade = "?", natureza = "?")
}

# ---------------- gravação ----------------
compacto <- function(x) ifelse(abs(x) >= 100, round(x), round(x, 2))
gravar_json <- function(obj, caminho) {
  dir.create(dirname(caminho), recursive = TRUE, showWarnings = FALSE)
  writeLines(toJSON(obj, auto_unbox = TRUE, digits = NA, null = "null"), caminho, useBytes = TRUE)
}
dir.create(SAIDA, recursive = TRUE, showWarnings = FALSE)

catalogo <- list(versao_script = paste0("R ", VERSAO_SCRIPT), versao_modelo = MODELO,
                 gerado_em = format(Sys.Date()), gases = "somente CO₂ (sem CH₄ e N₂O)",
                 ficticio = file.exists(file.path(ENTRADA, "FICTICIOS.txt")),
                 variaveis = setNames(lapply(COLS, unidade), COLS), tipos = list())
longa <- list()
for (tipo in names(rec)) {
  dt <- rec[[tipo]]
  anos <- sort(unique(dt$ano)); ids <- sort(unique(dt$id)); nomes <- nomes_de(tipo, ids)
  catalogo$tipos[[tipo]] <- list(anos = I(anos), n = length(ids),
    ids = lapply(seq_along(ids), function(k) list(id = ids[k], nome = nomes[k])),
    lote = if (tipo %in% names(LOTE_UF)) "uf" else "unico")
  # completa anos ausentes com zero
  grade <- CJ(id = ids, ano = anos)
  dt <- dt[grade, on = c("id", "ano")]
  for (v in COLS) set(dt, which(is.na(dt[[v]])), v, 0)
  setorder(dt, id, ano)
  # séries em lotes
  lote <- if (tipo %in% names(LOTE_UF)) LOTE_UF[[tipo]](dt$id) else rep(0, nrow(dt))
  for (l in unique(lote)) {
    sub <- dt[lote == l]
    series <- lapply(split(sub, by = "id", keep.by = FALSE), function(g)
      setNames(lapply(COLS, function(v) I(compacto(g[[v]]))), COLS))
    names(series) <- as.character(unique(sub$id))
    gravar_json(list(tipo = tipo, anos = I(anos), series = series),
                file.path(SAIDA, "serie", tipo, sprintf("%d.json", as.integer(l))))
  }
  # mapas
  if (!tipo %in% SEM_MAPA) for (v in COLS) {
    vals <- setNames(lapply(anos, function(a) I(compacto(dt[ano == a][order(id)][[v]]))), as.character(anos))
    gravar_json(list(tipo = tipo, variavel = v, anos = I(anos), ids = I(ids), valores = vals),
                file.path(SAIDA, "mapa", tipo, sprintf("%s.json", v)))
  }
  longa[[tipo]] <- melt(dt, id.vars = c("id", "ano"), measure.vars = COLS,
                        variable.name = "variavel", value.name = "valor")[, tipo := tipo]
}
gravar_json(catalogo, file.path(SAIDA, "catalogo.json"))
longa <- rbindlist(longa)[, .(tipo, id, ano, variavel, valor)]
fwrite(longa, file.path(SAIDA, "estatisticas.csv.gz"))
cat(sprintf("Dados fictícios: %s\n", if (file.exists(file.path(ENTRADA, "FICTICIOS.txt"))) "sim" else "não"))
cat(sprintf("Gravado em %s: %s linhas na tabela longa; tipos = %s\n", SAIDA,
            format(nrow(longa), big.mark = "."), paste(names(rec), collapse = ", ")))
