/*=========================================================
  BECRP — Instalação do zero (RFC-0000)
  Instância → Admin → Localização → Init → Login
=========================================================*/

(async function () {
  const form = document.getElementById("install-form");
  const err = document.getElementById("install-error");
  const btn = document.getElementById("install-btn");
  const loading = document.getElementById("install-loading");
  let step = 1;

  try {
    const res = await fetch("/api/auth/check-setup");
    const data = await res.json();
    if (data.status === "ok" && data.setup === false) {
      window.location.replace("index.html");
      return;
    }
  } catch (e) {}

  function slug(s) {
    return String(s || "")
      .trim()
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/_+/g, "_")
      .replace(/^_|_$/g, "")
      .slice(0, 48) || "instance";
  }

  function showStep(n) {
    step = n;
    document.querySelectorAll(".panel-step").forEach((p) => {
      p.classList.toggle("on", Number(p.dataset.panel) === n);
    });
    document.querySelectorAll("#wiz-steps span").forEach((s) => {
      const sn = Number(s.dataset.s);
      s.classList.toggle("on", sn === n);
      s.classList.toggle("done", sn < n);
    });
    err.classList.remove("visible");
  }

  function showErr(t) {
    err.textContent = t || "";
    err.classList.add("visible");
  }

  document.getElementById("inst-name").addEventListener("input", function () {
    document.getElementById("inst-id").value = slug(this.value);
  });

  document.getElementById("btn-p1").onclick = function () {
    const name = document.getElementById("inst-name").value.trim();
    if (!name) return showErr("Informe o nome da Business Instance");
    document.getElementById("inst-id").value = slug(name);
    showStep(2);
  };
  document.getElementById("btn-back2").onclick = () => showStep(1);
  document.getElementById("btn-p2").onclick = function () {
    const nome = document.getElementById("setup-name").value.trim();
    const usuario = document.getElementById("setup-user").value.trim();
    const senha = document.getElementById("setup-pass").value.trim();
    const senha2 = document.getElementById("setup-pass2").value.trim();
    if (!nome || !usuario || !senha) return showErr("Preencha nome, usuário e senha");
    if (senha.length < 4) return showErr("Senha mínima: 4 caracteres");
    if (senha !== senha2) return showErr("Senhas não conferem");
    showStep(3);
  };
  document.getElementById("btn-back3").onclick = () => showStep(2);

  async function playProgress(items) {
    showStep(4);
    const list = document.getElementById("init-list");
    const defaults = [
      { id: "repository", label: "Repositório" },
      { id: "configuration", label: "Configuração" },
      { id: "administrator", label: "Administrador" },
      { id: "localization", label: "Localização" },
      { id: "services", label: "Serviços" },
      { id: "analytics", label: "Analytics" },
      { id: "documents", label: "Documentos" },
    ];
    const src = (items && items.length) ? items : defaults;
    list.innerHTML = src.map((x) =>
      `<li data-id="${x.id}">· ${x.label}</li>`
    ).join("");

    for (let i = 0; i < src.length; i++) {
      await new Promise((r) => setTimeout(r, 220));
      const li = list.children[i];
      if (!li) continue;
      li.classList.add("run");
      const ok = src[i].ok !== false;
      li.classList.toggle("ok", ok);
      li.textContent = (ok ? "✓ " : "× ") + (src[i].label || "");
    }
    document.getElementById("init-done").style.display = "block";
    await new Promise((r) => setTimeout(r, 700));
    localStorage.removeItem("auth_token");
    localStorage.removeItem("user_data");
    window.location.replace("index.html?installed=1");
  }

  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    const instance_name = document.getElementById("inst-name").value.trim();
    const instance_description = document.getElementById("inst-desc").value.trim();
    const nome = document.getElementById("setup-name").value.trim();
    const usuario = document.getElementById("setup-user").value.trim();
    const email = document.getElementById("setup-email").value.trim();
    const senha = document.getElementById("setup-pass").value.trim();
    const senha2 = document.getElementById("setup-pass2").value.trim();

    if (!instance_name || !nome || !usuario || !senha) {
      return showErr("Preencha instância, nome, usuário e senha");
    }
    if (senha !== senha2) return showErr("Senhas não conferem");

    err.classList.remove("visible");
    btn.disabled = true;
    loading.classList.add("visible");

    try {
      const res = await fetch("/api/auth/setup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          instance_name,
          instance_description,
          nome,
          usuario,
          email,
          senha,
          localization: {
            country: document.getElementById("loc-country").value.trim() || "BR",
            language: document.getElementById("loc-lang").value.trim() || "pt-BR",
            timezone: document.getElementById("loc-tz").value.trim() || "America/Sao_Paulo",
            currency: document.getElementById("loc-cur").value.trim() || "BRL",
          },
        }),
      });
      const data = await res.json();
      if (data.status !== "ok") {
        showErr(data.message || "Erro na instalação");
        btn.disabled = false;
        loading.classList.remove("visible");
        return;
      }
      loading.classList.remove("visible");
      await playProgress(data.init_progress || []);
    } catch (ex) {
      showErr("Erro de conexão com o servidor");
      btn.disabled = false;
      loading.classList.remove("visible");
    }
  });
})();
