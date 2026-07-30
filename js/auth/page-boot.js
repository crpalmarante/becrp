/*=========================================================
  page-boot — auth guard + user display for module pages
=========================================================*/
(function () {
  const auth = window.AuthService && window.AuthService.requireAuth("../index.html");
  if (!auth) return;

  const user = auth.user;
  const name = user.nome || user.usuario || "Usuário";

  const nameEl = document.getElementById("user-name-display");
  if (nameEl) nameEl.textContent = name;

  const statusEl = document.getElementById("status-user-info");
  if (statusEl) statusEl.textContent = "Usuário: " + name;

  document.querySelectorAll("[data-logout]").forEach((btn) => {
    btn.addEventListener("click", () => window.AuthService.logout());
  });

  // Defer so inline page scripts can register listeners first
  window.__authReady = auth;
  setTimeout(() => {
    document.dispatchEvent(new CustomEvent("auth:ready", { detail: auth }));
  }, 0);
})();
