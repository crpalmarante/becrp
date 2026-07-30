/*=========================================================
  LookupService — NCM / CEST / catálogos com create-in-context
=========================================================*/
(function (global) {
  const cache = new Map();
  const CACHE_TTL = 5 * 60 * 1000;

  async function apiGet(path) {
    return global.api(path);
  }

  function cacheGet(key) {
    const hit = cache.get(key);
    if (!hit) return null;
    if (Date.now() - hit.ts > CACHE_TTL) {
      cache.delete(key);
      return null;
    }
    return hit.data;
  }

  function cacheSet(key, data) {
    cache.set(key, { ts: Date.now(), data });
  }

  const NcmProvider = {
    async search(text) {
      const key = "ncm:" + text.toLowerCase();
      const cached = cacheGet(key);
      if (cached) return cached;
      const data = await apiGet("/api/lookup/ncm?q=" + encodeURIComponent(text) + "&limit=20");
      const items = data.items || [];
      cacheSet(key, items);
      return items;
    },
    async get(code) {
      const data = await apiGet("/api/lookup/ncm/" + encodeURIComponent(code));
      return data.item || null;
    },
    async resolveCest(ncmCode) {
      const data = await apiGet("/api/lookup/ncm/" + encodeURIComponent(ncmCode) + "/cest");
      return data;
    },
  };

  const CestProvider = {
    async search(text, ncm) {
      const key = "cest:" + (ncm || "") + ":" + text.toLowerCase();
      const cached = cacheGet(key);
      if (cached) return cached;
      let url = "/api/lookup/cest?q=" + encodeURIComponent(text) + "&limit=20";
      if (ncm) url += "&ncm=" + encodeURIComponent(ncm);
      const data = await apiGet(url);
      const items = data.items || [];
      cacheSet(key, items);
      return items;
    },
  };

  /** Provider genérico para CRUD JSON admin (categoria, marca, fabricante…). */
  function makeJsonCatalogProvider(opts) {
    const listPath = opts.listPath;
    const listKey = opts.listKey;
    let localCache = null;

    async function loadAll(force) {
      if (!force && localCache) return localCache;
      const data = await apiGet(listPath);
      const list = (data[listKey] || [])
        .filter((c) => c.ativo !== false)
        .map((c) => ({
          id: c.id,
          codigo: c.id,
          nome: c.nome,
          descricao: c.descricao || "",
          label: c.nome + (c.descricao ? " — " + c.descricao : ""),
          ativo: c.ativo !== false,
        }));
      localCache = list;
      return list;
    }

    return {
      async search(text) {
        const all = await loadAll(false);
        const q = (text || "").toLowerCase().trim();
        if (!q) return all.slice(0, 20);
        return all
          .filter(
            (c) =>
              c.nome.toLowerCase().includes(q) ||
              (c.descricao || "").toLowerCase().includes(q)
          )
          .slice(0, 20);
      },
      async create(payload) {
        const data = await global.api(listPath, {
          method: "POST",
          body: JSON.stringify(payload),
        });
        localCache = null;
        return data;
      },
      async update(id, payload) {
        const data = await global.api(listPath + "/" + id, {
          method: "POST",
          body: JSON.stringify({ action: "update", ...payload }),
        });
        localCache = null;
        return data;
      },
      invalidate() {
        localCache = null;
      },
    };
  }

  const CategoriaProvider = makeJsonCatalogProvider({
    listPath: "/api/admin/categorias",
    listKey: "categorias",
  });
  const MarcaProvider = makeJsonCatalogProvider({
    listPath: "/api/admin/marcas",
    listKey: "marcas",
  });
  const FabricanteProvider = makeJsonCatalogProvider({
    listPath: "/api/admin/fabricantes",
    listKey: "fabricantes",
  });

  function docNumber(docs, type) {
    const hit = (docs || []).find((d) => d.document_type === type);
    return hit ? hit.document_number : "";
  }

  function mapPartner(p) {
    const nome = p.display_name || p.trade_name || p.legal_name || "";
    const cnpj = docNumber(p.documents, "CNPJ");
    const cpf = docNumber(p.documents, "CPF");
    const documento = cnpj || cpf || "";
    const hq =
      (p.addresses || []).find((a) => a.address_type === "HEADQUARTERS") ||
      (p.addresses || [])[0] ||
      {};
    const prefContact =
      (p.contacts || []).find((c) => c.preferred) || (p.contacts || [])[0] || {};
    return {
      id: p.id,
      codigo: p.partner_code || String(p.id),
      nome,
      legal_name: p.legal_name || "",
      nome_fantasia: p.trade_name || "",
      descricao: documento,
      label: nome + (documento ? " — " + documento : ""),
      documento,
      cnpj,
      cpf,
      ie: docNumber(p.documents, "IE"),
      telefone: prefContact.phone || prefContact.mobile || "",
      email: prefContact.email || "",
      cidade: hq.city || "",
      uf: hq.state || "",
      endereco: [hq.street, hq.number].filter(Boolean).join(", "),
      roles: p.roles || [],
      addresses: p.addresses || [],
      contacts: p.contacts || [],
      bank_accounts: p.bank_accounts || [],
      regime: p.regime || "",
      contribuinte_icms: p.contribuinte_icms || "",
      person_type: p.person_type || "COMPANY",
    };
  }

  function makePartnerRoleProvider(role) {
    let cache = null;
    return {
      async search(text) {
        if (!cache) {
          const data = await apiGet("/api/admin/partners?role=" + encodeURIComponent(role));
          cache = (data.partners || [])
            .filter((p) => p.ativo !== false && p.status !== "INACTIVE")
            .map(mapPartner);
        }
        const q = (text || "").toLowerCase().trim();
        if (!q) return cache.slice(0, 20);
        return cache
          .filter(
            (p) =>
              p.nome.toLowerCase().includes(q) ||
              (p.legal_name || "").toLowerCase().includes(q) ||
              (p.nome_fantasia || "").toLowerCase().includes(q) ||
              String(p.codigo).toLowerCase().includes(q) ||
              (p.documento || "").includes(q)
          )
          .slice(0, 20);
      },
      async create(payload) {
        const data = await global.api("/api/admin/partners", {
          method: "POST",
          body: JSON.stringify({
            legal_name: payload.nome,
            display_name: payload.nome,
            trade_name: "",
            person_type: "COMPANY",
            roles: [role],
            documents: [],
            addresses: [],
            contacts: [],
            status: "ACTIVE",
            ativo: true,
          }),
        });
        cache = null;
        return data;
      },
      async update(id, payload) {
        const prev = (cache || []).find((p) => String(p.id) === String(id)) || {};
        const data = await global.api("/api/admin/partners/" + id, {
          method: "POST",
          body: JSON.stringify({
            action: "update",
            legal_name: payload.nome || prev.legal_name || prev.nome,
            display_name: payload.nome || prev.nome,
            trade_name: prev.nome_fantasia || "",
            person_type: prev.person_type || "COMPANY",
            roles: prev.roles && prev.roles.length ? prev.roles : [role],
            documents: prev.documents || [],
            addresses: prev.addresses || [],
            contacts: prev.contacts || [],
            regime: prev.regime || "SN",
            contribuinte_icms: prev.contribuinte_icms || "1",
            status: "ACTIVE",
            ativo: true,
          }),
        });
        cache = null;
        return data;
      },
      invalidate() {
        cache = null;
      },
    };
  }

  const ClienteProvider = makePartnerRoleProvider("CUSTOMER");
  const FornecedorProvider = makePartnerRoleProvider("SUPPLIER");
  const PartnerProvider = {
    _cache: null,
    async search(text) {
      if (!this._cache) {
        const data = await apiGet("/api/admin/partners");
        this._cache = (data.partners || [])
          .filter((p) => p.ativo !== false && p.status !== "INACTIVE")
          .map(mapPartner);
      }
      const q = (text || "").toLowerCase().trim();
      if (!q) return this._cache.slice(0, 20);
      return this._cache
        .filter(
          (p) =>
            p.nome.toLowerCase().includes(q) ||
            String(p.codigo).toLowerCase().includes(q) ||
            (p.documento || "").includes(q)
        )
        .slice(0, 20);
    },
    invalidate() {
      this._cache = null;
    },
  };

  global.LookupService = {
    NcmProvider,
    CestProvider,
    CategoriaProvider,
    MarcaProvider,
    FabricanteProvider,
    ClienteProvider,
    FornecedorProvider,
    PartnerProvider,
    makeJsonCatalogProvider,
    clearCache: () => {
      cache.clear();
      CategoriaProvider.invalidate();
      MarcaProvider.invalidate();
      FabricanteProvider.invalidate();
      ClienteProvider.invalidate();
      FornecedorProvider.invalidate();
      PartnerProvider.invalidate();
    },
  };
})(window);
