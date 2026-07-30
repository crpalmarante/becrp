/*=========================================================
  ProdutoCadastro — ponto único de cadastro/consulta de produtos
  Tela canônica: /pages/produtos.html

  Uso de qualquer módulo:
    ProdutoCadastro.abrir()              // lista
    ProdutoCadastro.novo()               // formulário novo
    ProdutoCadastro.consultar(id)        // formulário do produto
    ProdutoCadastro.url({ id, novo })    // só monta a URL

  Query params suportados pela tela:
    ?novo=1
    ?id=123
    ?retorno=/pages/vendas.html#pedidos   (volta ao Cancelar)
=========================================================*/
(function (global) {
  const PAGE = "/pages/produtos.html";

  function url(opts = {}) {
    const q = new URLSearchParams();
    if (opts.novo) q.set("novo", "1");
    if (opts.id != null && opts.id !== "") q.set("id", String(opts.id));
    if (opts.retorno) q.set("retorno", opts.retorno);
    const qs = q.toString();
    return PAGE + (qs ? "?" + qs : "");
  }

  function go(opts) {
    location.href = url(opts);
  }

  global.ProdutoCadastro = {
    PAGE,
    url,
    abrir: (retorno) => go(retorno ? { retorno } : {}),
    novo: (retorno) => go({ novo: true, retorno }),
    consultar: (id, retorno) => go({ id, retorno }),
  };
})(window);
