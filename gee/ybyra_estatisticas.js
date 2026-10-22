/**
 * ybyra_estatisticas.js · v0.3.1
 * =============================================================================
 * Estatísticas por recorte territorial dos assets de emissões e remoções do modelo
 * YbYrá-BR (projeto CNPq 401741/2023-0) para a plataforma
 * https://ybyra-br.github.io/plataforma/ — rodar no Code Editor do Earth Engine,
 * projeto ee-redd-brazil.
 *
 * Método (padrão das estatísticas do MapBiomas, user-toolkit calculate-area*.js):
 *   1. o recorte vira um RASTER de identificadores inteiros (ee.Image.paint);
 *   2. empilha-se [área do pixel] + [bandas Mg CO₂ pixel⁻¹] + [densidades × área] + [id];
 *   3. uma reduceRegion com ee.Reducer.sum().repeat(n).group() soma tudo por id de uma vez;
 *   4. o resultado vira tabela (zona, ano, área e bandas) e é exportado em CSV para o Drive.
 * Unidade atômica: município × bioma (zona = código IBGE × 10 + código do bioma).
 * UF, bioma, UF × bioma e Brasil são somados depois, em R (R/agregar.R), no GitHub.
 * O país é processado numa grade de 4° × 4° (cada pixel cai numa só célula); as
 * parciais das células são somadas no R.
 *
 * Como usar
 *   1. MODO = 'inspecionar' → Run: confere bandas, anos, unidades e o raster de zonas.
 *   2. MODO = 'teste'       → Run: uma célula pequena (Ilha do Maranhão), resultado no Console.
 *   3. MODO = 'exportar'    → Run: cria as tarefas; clique RUN em cada uma na aba Tasks.
 *   3b. MODO = 'geometrias' → Run: exporta as malhas em shapefile (pasta YBYRA-GEOMETRIAS)
 *      com colunas id (o mesmo da tabela) e nome, para o mapa da plataforma.
 *   3c. MODO = 'tudo'       → Run: 'exportar' + 'geometrias' numa só execução.
 *   4. Baixe os CSV da pasta YBYRA-ESTATISTICAS do Drive e envie para a pasta
 *      dados/brutos/v1_2/ do repositório ybyra-br/plataforma (pode ser pelo site do
 *      GitHub: Add file → Upload files). O GitHub Actions agrega e publica o site.
 *
 * Unidades do asset (só CO₂, sem CH₄ e N₂O)
 *   *_co2           Mg CO₂ pixel⁻¹ ano⁻¹ (fluxos)            → soma direta
 *   agc_sf_co2      Mg CO₂ pixel⁻¹ (estoque da secundária)     → soma direta
 *   *_co2_ha        Mg CO₂ ha⁻¹ ano⁻¹ (derivadas)               → não somadas
 *   agc_sf_ha, agc0_state  Mg C ha⁻¹                            → × área (ha) → Mg C
 *
 * Histórico de versões
 *   0.3.1 (2026-10-22) — shapefiles só com polígonos: algumas feições das malhas do MapBiomas são
 *                        coleções com pedaços de linha (erro "Shapefiles cannot contain multiple
 *                        geometry types"); feições sem parte poligonal são descartadas.
 *   0.3.0 (2026-10-22) — todos os recortes ligados (TI, UC, quilombos, Amazônia Legal, MATOPIBA,
 *                        bacias DHN250 níveis 1 e 2); modo 'tudo' cria de uma vez as tarefas de
 *                        estatística e de shapefile; 13 anos por tarefa (3 tarefas por recorte).
 *   0.2.0 (2026-10-22) — malhas públicas do MapBiomas (projects/mapbiomas-territories, as mesmas
 *                        do user-toolkit): municípios e estados IBGE 2025, biomas IBGE 2025, TI FUNAI
 *                        2026, UC CNUC 2026, quilombos INCRA 2026, Amazônia Legal, MATOPIBA e bacias
 *                        DHN250; atributos detectados automaticamente (código IBGE, código ou nome do
 *                        bioma, FEATURE_ID) e listados no modo inspecionar; modo 'geometrias'
 *                        exporta as malhas em shapefile (id + nome; simplificação opcional).
 *   0.1.0 (2026-10-21) — porte para JavaScript de ybyra_estatisticas_gee.py v0.1.1;
 *                        tarefas agrupadas por lotes de anos (ANOS_POR_TAREFA) para
 *                        reduzir os cliques em Run; recortes extras com chave "ativo".
 */

// ----------------------------------------------------------------------------
// Configuração
// ----------------------------------------------------------------------------
var MODO = 'inspecionar';           // 'inspecionar' | 'teste' | 'exportar' | 'geometrias' | 'tudo'

var ASSET_MODELO = 'projects/ee-redd-brazil/assets/ybyra-br-model/emissions_removals_v1_2';
var VERSAO_MODELO = 'v1_2';
var PASTA_DRIVE = 'YBYRA-ESTATISTICAS';

var ANOS = null;                    // null = anos de system:time_start; ou ex.: [2020, 2021]
var ANOS_POR_TAREFA = 13;           // anos por tarefa (39 anos → 3 tarefas por recorte); se uma tarefa falhar
                                    // por memória ou tempo, reduza (ex.: 5) e rode de novo só aquele recorte

var BANDAS_POR_PIXEL = null;        // null = todas as bandas terminadas em "_co2"
var BANDAS_DENSIDADE = {agc_sf_ha: 'agc_sf_mgc', agc0_state: 'agc0_mgc'};  // Mg C ha⁻¹ × área → Mg C
var BANDAS_EXCLUIR = [];

var TILE_SCALE = 4;
var MAX_PIXELS = 1e13;
var PASSO_GRADE = 4;                // graus
var BBOX_BRASIL = [-74.5, -34.5, -28.5, 5.5];   // oeste, sul, leste, norte

// Malhas territoriais públicas do MapBiomas (mesmas do user-toolkit, data/territories.js).
// Os atributos são detectados no próprio asset (primeiro candidato encontrado); use
// MODO = 'inspecionar' para ver as colunas de cada malha e, se preciso, fixe o atributo.
var MB = 'projects/mapbiomas-territories/assets/';
var ASSET_MUNICIPIOS = MB + 'PLATFORM/demo/mapbiomas/brazil/territories/MUNICIPIOS_IBGE_2025_637F97E6/0afdffeb-2a5b-4b93-8163-d52f92f555e5';
var ATRIB_MUNICIPIO = null;         // null = detectar entre CANDIDATOS_MUNICIPIO (código IBGE de 7 dígitos)
var ASSET_BIOMAS = MB + 'TERRITORIES/BRAZIL/WORKSPACE/BIOMES/BIOMES_v4';            // Biomas (IBGE, 2025)
var ATRIB_BIOMA = null;             // null = detectar: código (1–6) ou nome do bioma

var CANDIDATOS_MUNICIPIO = ['CD_MUN', 'CD_MUNICIPIO', 'GEOCODIGO', 'geocodigo', 'CD_GEOCMU', 'cod_ibge', 'COD_IBGE'];
var CANDIDATOS_BIOMA_COD = ['CD_Bioma', 'CD_BIOMA', 'cd_bioma', 'COD_BIOMA', 'cod_bioma'];
var CANDIDATOS_BIOMA_NOME = ['Bioma', 'BIOMA', 'bioma', 'NM_BIOMA', 'nm_bioma', 'NAME', 'name', 'NAME_PT', 'name_pt'];
var CANDIDATOS_ID = ['FEATURE_ID', 'feature_id', 'ID', 'id'];
// nome normalizado (minúsculas, sem acento) → código IBGE do bioma
var CODIGO_BIOMA = {amazonia: 1, amazon: 1, caatinga: 2, cerrado: 3, 'mata atlantica': 4, 'atlantic forest': 4, pampa: 5, pantanal: 6};

// Recortes independentes. sobrepoe = feições que se sobrepõem entre si (calcula feição a feição).
// atributo null = detectar entre CANDIDATOS_ID. ativo: false pula o recorte nos modos exportar/tudo.
var RECORTES_EXTRA = {
  terra_indigena:        {asset: MB + 'PLATFORM/demo/mapbiomas/brazil/territories/TERRAS_INDIGENAS_FUNAI_2026_F7F13F79/8b94c232-c551-4dd1-ac0c-2b40145db021', atributo: null, sobrepoe: true,  ativo: true},
  unidade_conservacao:   {asset: MB + 'PLATFORM/demo/mapbiomas/brazil/territories/UNIDADES_DE_CONSERVACAO_XNUC_2026_8DCD0C0B/ea04ccaf-0ff1-445a-9a29-a551015b0868', atributo: null, sobrepoe: true, ativo: true},
  territorio_quilombola: {asset: MB + 'PLATFORM/demo/mapbiomas/brazil/territories/QUILOMBOS_INCRA_2026_C57B5884/ff433ee4-7137-4845-aa3d-42f66d2b7823', atributo: null, sobrepoe: true, ativo: true},
  amazonia_legal:        {asset: MB + 'TERRITORIES-STAGING/BRAZIL/WORKSPACE/LEGAL_AMAZON/LEGAL_AMAZON_v3', atributo: null, sobrepoe: false, ativo: true},
  matopiba:              {asset: MB + 'TERRITORIES-STAGING/BRAZIL/WORKSPACE/MATOPIBA/MATOPIBA_v3', atributo: null, sobrepoe: false, ativo: true},
  bacia_nivel1:          {asset: MB + 'TERRITORIES-STAGING/BRAZIL/WORKSPACE/DHN250_LEVEL_1/DHN250_LEVEL_1_v2', atributo: null, sobrepoe: false, ativo: true},
  bacia_nivel2:          {asset: MB + 'TERRITORIES-STAGING/BRAZIL/WORKSPACE/DHN250_LEVEL_2/DHN250_LEVEL_2_v3', atributo: null, sobrepoe: false, ativo: true}
};
// Exportação das geometrias (MODO = 'geometrias')
var PASTA_GEOMETRIAS = 'YBYRA-GEOMETRIAS';
var SIMPLIFICAR_M = 0;              // 0 = geometria original; ex.: 100 simplifica com erro máx. de 100 m (arquivos bem menores)
var CANDIDATOS_NOME = ['NM_MUN', 'NM_UF', 'NM_BIOMA', 'Bioma', 'NAME', 'name', 'NOME', 'nome', 'NM_TI', 'terrai_nom', 'nome_uc', 'NOME_UC1', 'nm_comunid', 'NM_COMUNID'];
var CANDIDATOS_UF = ['CD_UF', 'cd_uf', 'COD_UF'];
// Estados: conferência no modo inspecionar e shapefile no modo geometrias (as estatísticas
// de estado e do Brasil saem da soma dos municípios)
var ASSET_ESTADOS = MB + 'PLATFORM/demo/mapbiomas/brazil/territories/ESTADOS_IBGE_2025_F7EAF953/3f95fd9d-4b26-4243-8612-37b9d5b12a55';

// ----------------------------------------------------------------------------
// Bandas, anos e projeção (lidos do asset)
// ----------------------------------------------------------------------------
var col = ee.ImageCollection(ASSET_MODELO);
var primeira = ee.Image(col.first());
var nomesAsset = primeira.bandNames().getInfo();

var porPixel = (BANDAS_POR_PIXEL || nomesAsset.filter(function (b) { return /_co2$/.test(b); }))
  .filter(function (b) { return BANDAS_EXCLUIR.indexOf(b) < 0; });
var densidade = {};
Object.keys(BANDAS_DENSIDADE).forEach(function (o) {
  if (nomesAsset.indexOf(o) >= 0 && BANDAS_EXCLUIR.indexOf(o) < 0) densidade[o] = BANDAS_DENSIDADE[o];
});
var NOMES_SAIDA = ['area_ha'].concat(porPixel, Object.keys(densidade).map(function (o) { return densidade[o]; }));
var ignoradas = nomesAsset.filter(function (b) { return porPixel.indexOf(b) < 0 && !(b in densidade); });
var faltam = porPixel.concat(Object.keys(BANDAS_DENSIDADE)).filter(function (b) { return nomesAsset.indexOf(b) < 0; });

var proj = primeira.select(0).projection().getInfo();
var CRS = proj.crs, TRANSFORM = proj.transform;

var anos = ANOS || col.aggregate_array('system:time_start')
  .map(function (t) { return ee.Date(t).get('year'); }).distinct().sort().getInfo();

// ----------------------------------------------------------------------------
// Atributos das malhas (detectados no primeiro registro)
// ----------------------------------------------------------------------------
function colunas(asset) {
  return ee.Feature(ee.FeatureCollection(asset).first()).propertyNames().getInfo();
}
function primeiroPresente(cols, candidatos) {
  for (var i = 0; i < candidatos.length; i++) if (cols.indexOf(candidatos[i]) >= 0) return candidatos[i];
  return null;
}
var colsMun = colunas(ASSET_MUNICIPIOS);
var atribMun = ATRIB_MUNICIPIO || primeiroPresente(colsMun, CANDIDATOS_MUNICIPIO);
var colsBio = colunas(ASSET_BIOMAS);
var atribBioCod = ATRIB_BIOMA || primeiroPresente(colsBio, CANDIDATOS_BIOMA_COD);
var atribBioNome = atribBioCod ? null : primeiroPresente(colsBio, CANDIDATOS_BIOMA_NOME);
if (!atribMun) print('ERRO — nenhum atributo de código IBGE encontrado nos municípios. Colunas:', colsMun);
if (!atribBioCod && !atribBioNome) print('ERRO — nenhum atributo de código ou nome encontrado nos biomas. Colunas:', colsBio);

// ----------------------------------------------------------------------------
// Funções
// ----------------------------------------------------------------------------
function imagemAno(ano) {
  var img = ee.Image(col.filter(ee.Filter.calendarRange(ano, ano, 'year')).first()).unmask(0);
  var areaHa = ee.Image.pixelArea().divide(1e4).rename('area_ha');
  var out = areaHa.addBands(img.select(porPixel));            // Mg CO₂ pixel⁻¹: soma direta
  Object.keys(densidade).forEach(function (o) {                // Mg C ha⁻¹ × ha = Mg C
    out = out.addBands(img.select(o).multiply(areaHa).rename(densidade[o]));
  });
  return out;
}

function comIdNumerico(fc, atributo) {
  return fc.map(function (f) {
    var v = f.get(atributo);
    var n = ee.Algorithms.If(ee.Algorithms.IsEqual(ee.Algorithms.ObjectType(v), 'String'), ee.Number.parse(v), v);
    return f.set('id_num', ee.Number(n).toInt64());
  });
}

function semAcento(s) {
  return ee.String(s).toLowerCase().trim()
    .replace('[áàâã]', 'a', 'g').replace('[éê]', 'e', 'g').replace('[í]', 'i', 'g')
    .replace('[óôõ]', 'o', 'g').replace('[ú]', 'u', 'g').replace('ç', 'c', 'g');
}

function comIdBioma(fc) {
  if (atribBioCod) return comIdNumerico(fc, atribBioCod);
  var tabela = ee.Dictionary(CODIGO_BIOMA);
  return fc.map(function (f) {
    return f.set('id_num', ee.Number(tabela.get(semAcento(f.get(atribBioNome)), 0)).toInt64());
  });
}

// Mantém só as partes poligonais (Polygon/MultiPolygon) de uma geometria, como MultiPolygon.
function soPoligonos(g) {
  g = ee.Geometry(g);
  var tipos = ee.List(['Polygon', 'MultiPolygon']);
  var partes = g.geometries().map(function (p) {
    p = ee.Geometry(p);
    return ee.Algorithms.If(tipos.contains(p.type()), p, null);
  }, true);
  var coords = ee.List(partes.iterate(function (p, acc) {
    p = ee.Geometry(p);
    var c = ee.Algorithms.If(ee.String(p.type()).equals('Polygon'), ee.List([p.coordinates()]), p.coordinates());
    return ee.List(acc).cat(ee.List(c));
  }, ee.List([])));
  return ee.Geometry.MultiPolygon(coords, g.projection(), false);
}

function rasterIds(fc) {
  return ee.Image().int64().paint(fc, 'id_num').rename('zona');
}

function gradeBrasil() {
  var cel = [];
  for (var x = BBOX_BRASIL[0]; x < BBOX_BRASIL[2]; x += PASSO_GRADE) {
    for (var y = BBOX_BRASIL[1]; y < BBOX_BRASIL[3]; y += PASSO_GRADE) {
      cel.push(ee.Feature(ee.Geometry.Rectangle([x, y, x + PASSO_GRADE, y + PASSO_GRADE], 'EPSG:4326', false)));
    }
  }
  return ee.FeatureCollection(cel);
}

function reduzir(empilhado, zona, geometria) {
  var n = NOMES_SAIDA.length;
  var redutor = ee.Reducer.sum().repeat(n).group({groupField: n, groupName: 'zona'});
  var out = empilhado.addBands(zona).updateMask(zona.mask()).reduceRegion({
    reducer: redutor, geometry: geometria, crs: CRS, crsTransform: TRANSFORM,
    maxPixels: MAX_PIXELS, tileScale: TILE_SCALE});
  var grupos = ee.List(ee.Dictionary(out).get('groups', ee.List([])));
  return ee.FeatureCollection(grupos.map(function (g) {
    g = ee.Dictionary(g);
    return ee.Feature(null, ee.Dictionary.fromLists(NOMES_SAIDA, ee.List(g.get('sum'))).set('zona', g.get('zona')));
  }));
}

function zonaMunicipioBioma() {
  var mun = rasterIds(comIdNumerico(ee.FeatureCollection(ASSET_MUNICIPIOS), atribMun));
  var bio = rasterIds(comIdBioma(ee.FeatureCollection(ASSET_BIOMAS))).unmask(0);  // 0 = sem bioma
  return mun.multiply(10).add(bio).rename('zona');
}

function tabelaMunicipioBioma(anosLote, celulas) {
  var zona = zonaMunicipioBioma();
  celulas = celulas || gradeBrasil();
  return ee.FeatureCollection(anosLote.map(function (ano) {
    var emp = imagemAno(ano);
    return celulas.map(function (c) { return reduzir(emp, zona, c.geometry()); }).flatten()
      .map(function (f) { return f.set('ano', ano); });
  })).flatten();
}

function tabelaRecorteExtra(nome, anosLote) {
  var cfg = RECORTES_EXTRA[nome];
  var atrib = cfg.atributo || primeiroPresente(colunas(cfg.asset), CANDIDATOS_ID);
  var fc = comIdNumerico(ee.FeatureCollection(cfg.asset), atrib);
  return ee.FeatureCollection(anosLote.map(function (ano) {
    var emp = imagemAno(ano), out;
    if (cfg.sobrepoe) {
      out = fc.map(function (f) { return reduzir(emp, rasterIds(ee.FeatureCollection([f])), f.geometry()); }).flatten();
    } else {
      var zona = rasterIds(fc);
      out = gradeBrasil().map(function (c) { return reduzir(emp, zona, c.geometry()); }).flatten();
    }
    return out.map(function (f) { return f.set('ano', ano); });
  })).flatten();
}

function exportar(nome, fc, anosLote) {
  var periodo = anosLote.length > 1 ? anosLote[0] + '-' + anosLote[anosLote.length - 1] : String(anosLote[0]);
  var desc = 'ybyra_' + VERSAO_MODELO + '_' + nome + '_' + periodo;
  Export.table.toDrive({collection: fc, description: desc, folder: PASTA_DRIVE, fileNamePrefix: desc,
                        fileFormat: 'CSV', selectors: ['zona', 'ano'].concat(NOMES_SAIDA)});
}

function lotes(xs, k) {
  var out = [];
  for (var i = 0; i < xs.length; i += k) out.push(xs.slice(i, i + k));
  return out;
}

// ----------------------------------------------------------------------------
// Execução
// ----------------------------------------------------------------------------
print('ybyra_estatisticas.js v0.3.1 · modelo ' + VERSAO_MODELO + ' · modo ' + MODO);

if (MODO === 'inspecionar') {
  print('Imagens:', col.size(), 'Anos:', anos);
  print('Projeção:', CRS, TRANSFORM);
  print('Somadas direto, Mg CO₂ pixel⁻¹ (' + porPixel.length + '):', porPixel);
  print('Densidade × área → Mg C:', densidade);
  print('Ignoradas (derivadas _ha ou não aditivas):', ignoradas);
  if (faltam.length) print('AVISO — bandas configuradas ausentes no asset:', faltam);
  print('Propriedades da 1ª imagem:', primeira.propertyNames());
  print('Municípios — atributo usado: ' + atribMun + ' · nº de feições:', ee.FeatureCollection(ASSET_MUNICIPIOS).size(), 'Colunas:', colsMun);
  print('Biomas — ' + (atribBioCod ? 'código: ' + atribBioCod : 'nome: ' + atribBioNome) + '; códigos obtidos:',
        comIdBioma(ee.FeatureCollection(ASSET_BIOMAS)).aggregate_array('id_num'), 'Colunas:', colsBio);
  print('Estados (conferência) — nº de feições:', ee.FeatureCollection(ASSET_ESTADOS).size());
  Object.keys(RECORTES_EXTRA).forEach(function (nome) {
    var cfg = RECORTES_EXTRA[nome], cols = colunas(cfg.asset);
    print(nome + ' — atributo: ' + (cfg.atributo || primeiroPresente(cols, CANDIDATOS_ID)) + (cfg.ativo ? ' (ativo)' : ' (desligado)') + ' · nº de feições:',
          ee.FeatureCollection(cfg.asset).size(), 'Colunas:', cols);
  });
  Map.setCenter(-52, -12, 4);
  Map.addLayer(zonaMunicipioBioma().randomVisualizer(), {}, 'Zonas município × bioma');
  Map.addLayer(ee.Image(col.sort('system:time_start', false).first()).select(porPixel[0]),
               {min: 0, max: 50, palette: ['ffffcc', 'fd8d3c', 'bd0026']}, porPixel[0] + ' (último ano)');
  Map.addLayer(gradeBrasil().style({color: '444444', fillColor: '00000000', width: 1}), {}, 'Grade 4°');
}

if (MODO === 'teste') {
  var celula = ee.FeatureCollection([ee.Feature(ee.Geometry.Rectangle([-44.5, -3.0, -44.0, -2.5], 'EPSG:4326', false))]);
  var anoTeste = anos[anos.length - 1];
  var fcTeste = tabelaMunicipioBioma([anoTeste], celula);
  print('Teste ' + anoTeste + ' — zonas município × bioma na célula da Ilha do Maranhão:', fcTeste.size());
  print(fcTeste.limit(20));
  Map.centerObject(celula, 9);
  Map.addLayer(celula, {color: 'red'}, 'Célula de teste');
}

if (MODO === 'geometrias' || MODO === 'tudo') {
  // Cada malha sai como shapefile com: id (mesmo identificador das tabelas de estatística), nome
  // e, nos municípios, sigla_uf. Nomes de coluna curtos (limite de 10 caracteres do shapefile).
  var exportarGeo = function (nome, fc, cols) {
    var atrNome = primeiroPresente(cols, CANDIDATOS_NOME);
    var atrUf = primeiroPresente(cols, ['SIGLA_UF', 'sigla_uf', 'SG_UF']);
    var saida = fc.map(function (f) {
      var g = soPoligonos(f.geometry());
      g = SIMPLIFICAR_M > 0 ? g.simplify(SIMPLIFICAR_M) : g;
      var props = {id: f.get('id_num'), nome: atrNome ? f.get(atrNome) : '',
                   n_partes: ee.List(g.coordinates()).length()};
      if (atrUf) props.sigla_uf = f.get(atrUf);
      return ee.Feature(g, props);
    }).filter(ee.Filter.gt('n_partes', 0));
    var desc = 'ybyra_geometria_' + nome;
    Export.table.toDrive({collection: saida, description: desc, folder: PASTA_GEOMETRIAS,
                          fileNamePrefix: desc, fileFormat: 'SHP'});
    print(nome + ' — id: ' + (nome === 'municipio' ? atribMun : nome === 'bioma' ? (atribBioCod || atribBioNome + ' → código') : 'ver acima') +
          ' · nome: ' + atrNome + (atrUf ? ' · UF: ' + atrUf : ''));
  };
  exportarGeo('municipio', comIdNumerico(ee.FeatureCollection(ASSET_MUNICIPIOS), atribMun), colsMun);
  exportarGeo('bioma', comIdBioma(ee.FeatureCollection(ASSET_BIOMAS)), colsBio);
  var colsUf = colunas(ASSET_ESTADOS), atribUf = primeiroPresente(colsUf, CANDIDATOS_UF);
  if (atribUf) exportarGeo('uf', comIdNumerico(ee.FeatureCollection(ASSET_ESTADOS), atribUf), colsUf);
  else print('Estados: nenhum atributo de código da UF encontrado. Colunas:', colsUf);
  Object.keys(RECORTES_EXTRA).forEach(function (nome) {
    var cfg = RECORTES_EXTRA[nome], cols = colunas(cfg.asset);
    var atrib = cfg.atributo || primeiroPresente(cols, CANDIDATOS_ID);
    if (cfg.ativo) exportarGeo(nome, comIdNumerico(ee.FeatureCollection(cfg.asset), atrib), cols);
  });
  print('Tarefas de geometria criadas (pasta do Drive: ' + PASTA_GEOMETRIAS + '). Clique RUN em cada uma na aba Tasks.');
}

if (MODO === 'exportar' || MODO === 'tudo') {
  var grupos = lotes(anos, ANOS_POR_TAREFA);
  grupos.forEach(function (g) { exportar('municipio_bioma', tabelaMunicipioBioma(g), g); });
  Object.keys(RECORTES_EXTRA).forEach(function (nome) {
    if (!RECORTES_EXTRA[nome].ativo) return;
    grupos.forEach(function (g) { exportar(nome, tabelaRecorteExtra(nome, g), g); });
  });
  var nExtras = Object.keys(RECORTES_EXTRA).filter(function (k) { return RECORTES_EXTRA[k].ativo; }).length;
  print('Tarefas de estatística criadas: ' + grupos.length * (1 + nExtras) + ' (pasta do Drive: ' + PASTA_DRIVE + '). Clique RUN em cada uma na aba Tasks.');
}
