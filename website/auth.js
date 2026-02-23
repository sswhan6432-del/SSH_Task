/* ============================================
   Auth — Supabase Auth integration
   Loaded on every page for nav state + protection
   Requires supabase-config.js to be loaded first
   ============================================ */

(function () {
  "use strict";

  var REDIRECT_KEY = "ssh_auth_redirect";

  function getClient() {
    return window.supabaseClient;
  }

  // --- Public API helpers ---

  async function getUser() {
    var client = getClient();
    if (!client) return null;
    try {
      var { data } = await client.auth.getUser();
      if (!data.user) return null;
      return {
        id: data.user.id,
        email: data.user.email,
        name: data.user.user_metadata ? data.user.user_metadata.name : (data.user.email || ""),
      };
    } catch (e) { return null; }
  }

  function getSession() {
    var client = getClient();
    if (!client) return Promise.resolve(null);
    return client.auth.getSession().then(function (res) {
      return res.data.session;
    }).catch(function () { return null; });
  }

  async function checkAuth() {
    return await getUser();
  }

  async function logout() {
    var client = getClient();
    if (client) {
      try { await client.auth.signOut(); } catch (e) { /* ignore */ }
    }
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
        var client = getClient();
        if (!client) throw new Error("Supabase not configured");

        var { data, error } = await client.auth.signInWithPassword({
          email: email,
          password: password,
        });

        if (error) throw error;

        if (data.user) {
          var redirect = sessionStorage.getItem(REDIRECT_KEY) || "/dashboard.html";
          sessionStorage.removeItem(REDIRECT_KEY);
          window.location.href = redirect;
        } else {
          errEl.textContent = "Login failed";
          errEl.classList.add("visible");
        }
      } catch (err) {
        errEl.textContent = err.message || "Login failed";
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
        var client = getClient();
        if (!client) throw new Error("Supabase not configured");

        var { data, error } = await client.auth.signUp({
          email: email,
          password: password,
          options: {
            data: { name: name },
          },
        });

        if (error) throw error;

        if (data.user) {
          // Check if email confirmation is required
          if (data.user.identities && data.user.identities.length === 0) {
            errEl.textContent = "This email is already registered";
            errEl.classList.add("visible");
          } else if (data.session) {
            // Auto-confirmed, redirect
            var redirect = sessionStorage.getItem(REDIRECT_KEY) || "/dashboard.html";
            sessionStorage.removeItem(REDIRECT_KEY);
            window.location.href = redirect;
          } else {
            // Email confirmation required
            errEl.textContent = "Check your email to confirm your account";
            errEl.classList.add("visible");
            errEl.style.color = "#22c55e";
          }
        }
      } catch (err) {
        errEl.textContent = err.message || "Signup failed";
        errEl.classList.add("visible");
      } finally {
        btn.disabled = false;
        btn.textContent = "Create Account";
      }
    });
  }

  // --- Auth state change listener ---
  function setupAuthListener() {
    var client = getClient();
    if (!client) return;

    client.auth.onAuthStateChange(function (event, session) {
      if (event === "SIGNED_IN" && session) {
        var user = session.user;
        var profile = {
          id: user.id,
          email: user.email,
          name: user.user_metadata ? user.user_metadata.name : (user.email || ""),
        };
        renderNavLoggedIn(profile);
        renderMobileLoggedIn(profile);
      } else if (event === "SIGNED_OUT") {
        renderNavLoggedOut();
        renderMobileLoggedOut();
        if (document.body.dataset.authRequired === "true") {
          sessionStorage.setItem(REDIRECT_KEY, window.location.pathname);
          window.location.href = "/login.html";
        }
      }
    });
  }

  // --- Init: check auth and update nav ---

  async function init() {
    var client = getClient();
    if (!client) {
      renderNavLoggedOut();
      renderMobileLoggedOut();
      return;
    }

    setupAuthListener();

    var user = await getUser();

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
    getUser: getUser,
    getSession: getSession,
    checkAuth: checkAuth,
    logout: logout,
  };
})();
