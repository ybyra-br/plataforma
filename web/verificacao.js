/* verificacao.js · v0.1.0 — código de verificação dos relatórios da plataforma YbYrá-BR
   O código é o SHA-256 (primeiros 64 bits) de: versão dos dados | recorte | id | ano de referência |
   data e hora da geração (UTC) | série completa do recorte, tal como publicada para aquela versão.
   A página verificar.html recalcula o código a partir dos dados oficiais publicados: se o código
   confere, os números do relatório são os da plataforma para aquele recorte e versão; a página
   mostra os valores oficiais para comparação com o documento impresso.
   Histórico de versões
     0.1.0 (2026-10-24) — versão inicial. */
const YBV = (() => {
  const PREFIXO = "YBYRA-BR";
  // série canônica: variáveis em ordem alfabética, valores como publicados no JSON
  const canon = s => Object.keys(s).sort().map(k => k + ":" + s[k].map(v => String(v)).join(",")).join(";");
  async function sha256(txt){
    const b = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(txt));
    return [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, "0")).join("");
  }
  async function codigo(p, serie){
    const h = await sha256([PREFIXO, p.v, p.t, p.i, p.a, p.g, canon(serie)].join("|"));
    return h.slice(0, 16).toUpperCase();
  }
  const curto = c => c.match(/.{4}/g).join("-");
  const agora = () => new Date().toISOString().slice(0, 16) + "Z";            // AAAA-MM-DDTHH:MMZ
  // código completo, legível e digitável: versão/recorte/id/ano/geração/código
  const completo = p => `${p.v}/${p.t}/${p.i}/${p.a}/${p.g.replace(/[-:]/g, "")}/${curto(p.c)}`;
  function lerCompleto(txt){
    const m = String(txt).trim().match(/^v?([\d.]+)\/([a-z_]+)\/(\d+)\/(\d{4})\/(\d{8}T\d{4}Z)\/([0-9A-F-]{16,19})$/i);
    if(!m) return null;
    const g = m[5].replace(/^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})Z$/, "$1-$2-$3T$4:$5Z");
    return {v:m[1], t:m[2], i:+m[3], a:+m[4], g, c:m[6].replace(/-/g, "").toUpperCase()};
  }
  const paraURL = p => new URLSearchParams({v:p.v, t:p.t, i:String(p.i), a:String(p.a), g:p.g, c:p.c}).toString();
  function lerURL(hash){
    const q = new URLSearchParams(String(hash).replace(/^#/, ""));
    if(!q.get("c")) return null;
    return {v:q.get("v"), t:q.get("t"), i:+q.get("i"), a:+q.get("a"), g:q.get("g"), c:q.get("c").replace(/-/g, "").toUpperCase()};
  }
  // lote do arquivo de séries (mesma regra de R/agregar.R)
  function lote(cat, tipo, id){
    const l = cat.tipos[tipo].lote;
    if(l === "uf") return tipo === "municipio" ? Math.floor(id/100000) : Math.floor(id/1000000);
    if(l && l.startsWith("mod")) return id % (+l.slice(3));
    return 0;
  }
  return {codigo, curto, agora, completo, lerCompleto, paraURL, lerURL, lote, canon};
})();
