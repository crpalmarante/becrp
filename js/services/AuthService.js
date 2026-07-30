/*=========================================================
  AuthService — token + API helper for BECRP pages
=========================================================*/
(function (global) {
  const TOKEN_KEY = "auth_token";
  const USER_KEY = "user_data";

  function getToken() {
    return localStorage.getItem(TOKEN_KEY) || "";
  }

  function getUser() {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY) || "null");
    } catch {
      return null;
    }
  }

  function requireAuth(loginUrl) {
    const token = getToken();
    const user = getUser();
    if (!token || !user) {
      location.href = loginUrl || "../index.html";
      return null;
    }
    return { token, user };
  }

  async function api(path, opts = {}) {
    const token = getToken();
    const headers = {
      "Content-Type": "application/json",
      "X-Auth-Token": token,
      ...(opts.headers || {}),
    };
    const res = await fetch(path, { ...opts, headers });
    if (res.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      location.href = "../index.html";
      return { status: "error", message: "Não autenticado" };
    }
    const ct = res.headers.get("Content-Type") || "";
    if (ct.includes("application/json")) return res.json();
    return { status: res.ok ? "ok" : "error", message: await res.text() };
  }

  function logout() {
    const token = getToken();
    fetch("/api/auth/logout", {
      method: "POST",
      headers: { "X-Auth-Token": token },
    }).catch(() => {});
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem("current_empresa_id");
    location.href = "../index.html";
  }

  global.AuthService = { getToken, getUser, requireAuth, api, logout };
  global.api = api;
})(window);
