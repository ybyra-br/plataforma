/**
 * ybyra_estatisticas.js · v0.1.0
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
 *   0.1.0 (2026-10-21) — porte para JavaScript de ybyra_estatisticas_gee.py v0.1.1;
 *                        tarefas agrupadas por lotes de anos (ANOS_POR_TAREFA) para
 *                        reduzir os cliques em Run; recortes extras com chave "ativo".
 */

// ----------------------------------------------------------------------------
// Configuração
// ----------------------------------------------------------------------------
var MODO = 'inspecionar';           // 'inspecionar' | 'teste' | 'exportar'

var ASSET_MODELO = 'projects/ee-redd-brazil/assets/ybyra-br-model/emissions_removals_v1_2';
var VERSAO_MODELO = 'v1_2';
var PASTA_DRIVE = 'YBYRA-ESTATISTICAS';

var ANOS = null;                    // null = anos de system:time_start; ou ex.: [2020, 2021]
var ANOS_POR_TAREFA = 8;            // anos por tarefa de exportação (menos cliques; tarefas maiores)

var BANDAS_POR_PIXEL = null;        // null = todas as bandas terminadas em "_co2"
var BANDAS_DENSIDADE = {agc_sf_ha: 'agc_sf_mgc', agc0_state: 'agc0_mgc'};  // Mg C ha⁻¹ × área → Mg C
var BANDAS_EXCLUIR = [];

var TILE_SCALE = 4;
var MAX_PIXELS = 1e13;
var PASSO_GRADE = 4;                // graus
var BBOX_BRASIL = [-74.5, -34.5, -28.5, 5.5];   // oeste, sul, leste, norte

// Malhas (enviar como assets)  >>> CONFIRMAR caminhos e atributos <<<
var ASSET_MUNICIPIOS = 'projects/ee-redd-brazil/assets/territorios/BR_Municipios_2025';
var ATRIB_MUNICIPIO = 'CD_MUN';     // código IBGE de 7 dígitos (texto ou número)
var ASSET_BIOMAS = 'projects/ee-redd-brazil/assets/territorios/Biomas_250mil_2019';
var ATRIB_BIOMA = 'CD_Bioma';       // 1 Amazônia · 2 Caatinga · 3 Cerrado · 4 Mata Atlântica · 5 Pampa · 6 Pantanal

// Recortes independentes. sobrepoe = feições que se sobrepõem entre si (calcula feição a feição).
var RECORTES_EXTRA = {
  terra_indigena:        {asset: 'projects/ee-redd-brazil/assets/territorios/TI_FUNAI',            atributo: 'terrai_cod', sobrepoe: true,  ativo: false},
  unidade_conservacao:   {asset: 'projects/ee-redd-brazil/assets/territorios/UC_CNUC',             atributo: 'id_uc',      sobrepoe: true,  ativo: false},
  territorio_quilombola: {asset: 'projects/ee-redd-brazil/assets/territorios/Quilombolas_INCRA',   atributo: 'id_qui',     sobrepoe: true,  ativo: false},
  assentamento:          {asset: 'projects/ee-redd-brazil/assets/territorios/Assentamentos_INCRA', atributo: 'id_ass',     sobrepoe: false, ativo: false}
};

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
  var mun = rasterIds(comIdNumerico(ee.FeatureCollection(ASSET_MUNICIPIOS), ATRIB_MUNICIPIO));
  var bio = rasterIds(comIdNumerico(ee.FeatureCollection(ASSET_BIOMAS), ATRIB_BIOMA)).unmask(0);  // 0 = sem bioma
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
  var fc = comIdNumerico(ee.FeatureCollection(cfg.asset), cfg.atributo);
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
print('ybyra_estatisticas.js v0.1.0 · modelo ' + VERSAO_MODELO + ' · modo ' + MODO);

if (MODO === 'inspecionar') {
  print('Imagens:', col.size(), 'Anos:', anos);
  print('Projeção:', CRS, TRANSFORM);
  print('Somadas direto, Mg CO₂ pixel⁻¹ (' + porPixel.length + '):', porPixel);
  print('Densidade × área → Mg C:', densidade);
  print('Ignoradas (derivadas _ha ou não aditivas):', ignoradas);
  if (faltam.length) print('AVISO — bandas configuradas ausentes no asset:', faltam);
  print('Propriedades da 1ª imagem:', primeira.propertyNames());
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

if (MODO === 'exportar') {
  var grupos = lotes(anos, ANOS_POR_TAREFA);
  grupos.forEach(function (g) { exportar('municipio_bioma', tabelaMunicipioBioma(g), g); });
  Object.keys(RECORTES_EXTRA).forEach(function (nome) {
    if (!RECORTES_EXTRA[nome].ativo) return;
    grupos.forEach(function (g) { exportar(nome, tabelaRecorteExtra(nome, g), g); });
  });
  print('Tarefas criadas. Clique RUN em cada uma na aba Tasks (pasta do Drive: ' + PASTA_DRIVE + ').');
}
