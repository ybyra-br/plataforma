/**
 * ybyra_nomes_uc.js · v0.1.0
 * ==========================
 * Exporta a tabela de atributos das unidades de conservação (CNUC 2026, malha pública do MapBiomas),
 * sem geometria, em CSV UTF-8, com o mesmo identificador usado nas estatísticas e no mapa da
 * plataforma (coluna "id"). Todas as colunas do asset vão junto (nome, categoria, código CNUC…),
 * para ligar os nomes às UCs já exportadas.
 *
 * Code Editor do Earth Engine, projeto ee-redd-brazil.
 * Run → aba Tasks → RUN na tarefa "ybyra_nomes_unidade_conservacao" → pasta YBYRA-NOMES do Drive.
 *
 * Histórico de versões
 *   0.1.0 (2026-10-24) — versão inicial.
 */

var ASSET_UC = 'projects/mapbiomas-territories/assets/PLATFORM/demo/mapbiomas/brazil/territories/' +
               'UNIDADES_DE_CONSERVACAO_XNUC_2026_8DCD0C0B/ea04ccaf-0ff1-445a-9a29-a551015b0868';
var PASTA = 'YBYRA-NOMES';
var NOME_ARQUIVO = 'ybyra_nomes_unidade_conservacao';
// Mesmo critério de ybyra_estatisticas.js: primeiro campo presente desta lista vira o "id"
var CANDIDATOS_ID = ['FEATURE_ID', 'feature_id', 'ID', 'id'];

var uc = ee.FeatureCollection(ASSET_UC);
var cols = ee.Feature(uc.first()).propertyNames().getInfo();
var atribId = null;
for (var i = 0; i < CANDIDATOS_ID.length; i++) {
  if (cols.indexOf(CANDIDATOS_ID[i]) >= 0) { atribId = CANDIDATOS_ID[i]; break; }
}
if (!atribId) throw new Error('Nenhum campo de identificador encontrado. Colunas: ' + cols.join(', '));

// id numérico igual ao das estatísticas; geometria removida (só a tabela)
var tabela = uc.map(function (f) {
  var v = f.get(atribId);
  var n = ee.Algorithms.If(ee.Algorithms.IsEqual(ee.Algorithms.ObjectType(v), 'String'), ee.Number.parse(v), v);
  return ee.Feature(null, f.toDictionary()).set('id', ee.Number(n).toInt64());
});

// colunas: id primeiro, depois todas as do asset (sem as internas do sistema)
var outras = cols.filter(function (c) { return c !== 'id' && c.indexOf('system:') !== 0; });
var seletores = ['id'].concat(outras);

print('Identificador usado: ' + atribId + ' (deve ser o mesmo das estatísticas)');
print('Colunas exportadas:', seletores);
print('Nº de UCs:', uc.size());
print('Exemplo (1ª UC):', ee.Feature(tabela.first()).toDictionary());

Export.table.toDrive({
  collection: tabela,
  description: NOME_ARQUIVO,
  folder: PASTA,
  fileNamePrefix: NOME_ARQUIVO,
  fileFormat: 'CSV',
  selectors: seletores
});
print('Tarefa criada: aba Tasks → RUN. Arquivo: ' + PASTA + '/' + NOME_ARQUIVO + '.csv');
