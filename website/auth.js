/* ============================================
   Auth — Client-side authentication logic
   Loaded on every page for nav state + protection
   ============================================ */

(function () {
  "use strict";

  var TOKEN_KEY = "ssh_auth_token";
  var USER_KEY = "ssh_auth_user";
  var REDIRECT_KEY = "ssh_auth_redirect";

  // --- Helpers ---

  function getToken() {
    try { return localStorage.getItem(TOKEN_KEY); } catch (e) { return null; }
  }

  function getUser() {
    try {
      var raw = localStorage.getItem(USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) { return null; }
  }

  function saveAuth(token, user) {
    try {
      localStorage.setItem(TOKEN_KEY, token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    } catch (e) { /* ignore */ }
  }

  function clearAuth() {
    try {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    } catch (e) { /* ignore */ }
  }

  // --- API ---

  async function apiAuthPost(url, body) {
    var res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return { status: res.status, data: await res.json() };
  }

  async function checkAuth() {
    var token = getToken();
    if (!token) return null;

    try {
      var res = await fetch("/api/auth/me", {
        headers: { Authorization: "Bearer " + token },
      });
      if (res.ok) {
        var d = await res.json();
        saveAuth(token, d.user);
        return d.user;
      }
    } catch (e) { /* network error */ }

    clearAuth();
    return null;
  }

  async function logout() {
    var token = getToken();
    if (token) {
      try {
        await fetch("/api/auth/logout", {
          method: "POST",
          headers: { Authorization: "Bearer " + token },
        });
      } catch (e) { /* ignore */ }
    }
    clearAuth();
    renderNavLoggedOut();
    renderMobileLoggedOut();
  }

  // --- Nav rendering ---

  function renderNavLoggedIn(user) {
    var container = document.getElementById("nav-auth");
    if (!container) return;

    var initial = (user.name || user.email || "U").charAt(0).toUpperCase();

    container.innerHTML =
      '<div class="nav-auth-avatar" id="nav-auth-avatar">' + initial +
        '<div class="nav-auth-dropdown" id="nav-auth-dropdown">' +
          '<div class="nav-auth-dropdown-name">' + escapeHtml(user.name) + '</div>' +
          '<div class="nav-auth-dropdown-email">' + escapeHtml(user.email) + '</div>' +
          '<button class="nav-auth-logout" id="nav-auth-logout-btn" type="button">Sign Out</button>' +
        '</div>' +
      '</div>';

    var avatar = document.getElementById("nav-auth-avatar");
    var dropdown = document.getElementById("nav-auth-dropdown");
    var logoutBtn = document.getElementById("nav-auth-logout-btn");

    avatar.addEventListener("click", function (e) {
      e.stopPropagation();
      dropdown.classList.toggle("open");
    });

    document.addEventListener("click", function () {
      dropdown.classList.remove("open");
    });

    logoutBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      logout().then(function () {
        if (document.body.dataset.authRequired === "true") {
          window.location.href = "/login.html";
        }
      });
    });
  }

  function renderNavLoggedOut() {
    var container = document.getElementById("nav-auth");
    if (!container) return;
    container.innerHTML = '<a href="/login.html" class="nav-auth-login">Sign In</a>';
  }

  function renderMobileLoggedIn(user) {
    var container = document.getElementById("mobile-auth");
    if (!container) return;
    container.innerHTML =
      '<div class="mobile-auth-user">' +
        '<span class="mobile-auth-name">' + escapeHtml(user.name) + '</span>' +
        '<button class="mobile-auth-logout-btn" id="mobile-logout-btn" type="button">Sign Out</button>' +
      '</div>';

    document.getElementById("mobile-logout-btn").addEventListener("click", function () {
      logout().then(function () {
        if (document.body.dataset.authRequired === "true") {
          window.location.href = "/login.html";
        }
      });
    });
  }

  function renderMobileLoggedOut() {
    var container = document.getElementById("mobile-auth");
    if (!container) return;
    container.innerHTML = '<a href="/login.html" class="mobile-auth-login">Sign In</a>';
  }

  function escapeHtml(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str || ""));
    return div.innerHTML;
  }

  // --- Login form handler ---

  var loginForm = document.getElementById("login-form");
  if (loginForm) {
    loginForm.addEventListener("submit", async function (e) {
      e.preventDefault();
      var errEl = document.getElementById("login-error");
      var btn = loginForm.querySelector(".auth-submit");
      var email = document.getElementById("email").value.trim();
      var password = document.getElementById("password").value;

      errEl.textContent = "";
      errEl.classList.remove("visible");
      btn.disabled = true;
      btn.textContent = "Signing in...";

      try {
        var resp = await apiAuthPost("/api/auth/login", { email: email, password: password });
        if (resp.data.ok) {
          saveAuth(resp.data.token, resp.data.user);
          var redirect = sessionStorage.getItem(REDIRECT_KEY) || "/dashboard.html";
          sessionStorage.removeItem(REDIRECT_KEY);
          window.location.href = redirect;
        } else {
          errEl.textContent = resp.data.error || "Login failed";
          errEl.classList.add("visible");
        }
      } catch (err) {
        errEl.textContent = "Network error. Is the server running?";
        errEl.classList.add("visible");
      } finally {
        btn.disabled = false;
        btn.textContent = "Sign In";
      }
    });
  }

  // --- Signup form handler ---

  var signupForm = document.getElementById("signup-form");
  if (signupForm) {
    signupForm.addEventListener("submit", async function (e) {
      e.preventDefault();
      var errEl = document.getElementById("signup-error");
      var btn = signupForm.querySelector(".auth-submit");
      var name = document.getElementById("name").value.trim();
      var email = document.getElementById("email").value.trim();
      var password = document.getElementById("password").value;

      errEl.textContent = "";
      errEl.classList.remove("visible");
      btn.disabled = true;
      btn.textContent = "Creating account...";

      try {
        var resp = await apiAuthPost("/api/auth/signup", { name: name, email: email, password: password });
        if (resp.data.ok) {
          saveAuth(resp.data.token, resp.data.user);
          var redirect = sessionStorage.getItem(REDIRECT_KEY) || "/dashboard.html";
          sessionStorage.removeItem(REDIRECT_KEY);
          window.location.href = redirect;
        } else {
          errEl.textContent = resp.data.error || "Signup failed";
          errEl.classList.add("visible");
        }
      } catch (err) {
        errEl.textContent = "Network error. Is the server running?";
        errEl.classList.add("visible");
      } finally {
        btn.disabled = false;
        btn.textContent = "Create Account";
      }
    });
  }

  // --- Init: check auth and update nav ---

  async function init() {
    var user = await checkAuth();

    if (user) {
      renderNavLoggedIn(user);
      renderMobileLoggedIn(user);

      // If on login/signup page and already logged in, redirect
      var path = window.location.pathname;
      if (path === "/login.html" || path === "/signup.html") {
        window.location.href = "/dashboard.html";
        return;
      }
    } else {
      renderNavLoggedOut();
      renderMobileLoggedOut();

      // Protected page guard
      if (document.body.dataset.authRequired === "true") {
        sessionStorage.setItem(REDIRECT_KEY, window.location.pathname);
        window.location.href = "/login.html";
        return;
      }
    }
  }

  // Run init when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // Expose for external use
  window.sshAuth = {
    getToken: getToken,
    getUser: getUser,
    checkAuth: checkAuth,
    logout: logout,
  };
})();
