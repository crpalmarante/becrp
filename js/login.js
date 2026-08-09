/*=========================================================
  BECRP — Login (somente autenticação)
  Instalação de primeira vez: install.html
=========================================================*/

const loginForm = document.getElementById("login-form");
const loginUser = document.getElementById("login-user");
const loginPass = document.getElementById("login-pass");
const loginError = document.getElementById("login-error");
const loginBtn = document.getElementById("login-btn");
const loginLoading = document.getElementById("login-loading");
const subtitle = document.getElementById("login-subtitle");
const banner = document.getElementById("install-banner");

/*=========================================================
  Roteamento: sem admin → instalação; com admin → login
=========================================================*/

async function routeEntry() {
  const params = new URLSearchParams(window.location.search || "");
  if (params.get("installed") === "1" && banner) {
    banner.style.display = "block";
    banner.textContent = "Instalação concluída. Entre com o administrador criado.";
    subtitle.textContent = "Primeiro login";
  }

  try {
    const res = await fetch("/api/auth/check-setup");
    const data = await res.json();
    if (data.status === "ok" && data.setup === true) {
      // Sistema ainda não instalado → tela de instalação
      window.location.replace("install.html");
      return;
    }
  } catch (e) {}
}

routeEntry();

/*=========================================================
  LOGIN
=========================================================*/

loginForm.addEventListener("submit", async function (e) {
  e.preventDefault();
  const usuario = loginUser.value.trim();
  const senha = loginPass.value.trim();
  if (!usuario || !senha) {
    loginError.textContent = "Preencha usuário e senha";
    loginError.classList.add("visible");
    return;
  }
  loginError.classList.remove("visible");
  loginBtn.disabled = true;
  loginLoading.classList.add("visible");
  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ usuario, senha }),
    });
    const data = await res.json();
    if (data.status !== "ok") {
      loginError.textContent = data.message || "Usuário ou senha incorretos";
      loginError.classList.add("visible");
      loginBtn.disabled = false;
      loginLoading.classList.remove("visible");
      return;
    }
    localStorage.setItem("auth_token", data.token);
    localStorage.setItem("user_data", JSON.stringify(data));

    // RFC-0000 §10–11: após login → Business Setup se necessário
    try {
      const sr = await fetch("/api/platform/setup", {
        headers: { "X-Auth-Token": data.token },
      });
      const sd = await sr.json();
      if (sd.status === "ok" && sd.needs_wizard && data.role === "admin") {
        window.location.href = "pages/setup-wizard.html";
        return;
      }
    } catch (e) {}

    // Roteamento por função: vendedor→PDV, caixa→caixa da loja,
    // demais funções (admin/gerente/fiscal/contábil) → menu administrativo.
    const pos = data.pos;
    if (pos === "pdv") {
      window.location.href = "pages/pos.html?mode=pdv";
      return;
    }
    if (pos === "caixa") {
      window.location.href = "pages/pos.html?mode=caixa";
      return;
    }
    window.location.href = "index4.html";
  } catch (err) {
    loginError.textContent = "Erro de conexão com o servidor";
    loginError.classList.add("visible");
    loginBtn.disabled = false;
    loginLoading.classList.remove("visible");
  }
});
