/**
 * Dashboard Auth Helper - JWT management via localStorage.
 */

const AUTH_TOKEN_KEY = "tr_jwt";
const AUTH_USER_KEY = "tr_user";
const API = window.location.origin;

function getToken() {
    return localStorage.getItem(AUTH_TOKEN_KEY);
}

function getUser() {
    const raw = localStorage.getItem(AUTH_USER_KEY);
    return raw ? JSON.parse(raw) : null;
}

function saveAuth(token, user) {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
    localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
}

function clearAuth() {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_USER_KEY);
}

function logout() {
    clearAuth();
    if (typeof clearEncryptionKey === "function") clearEncryptionKey();
    window.location.href = "/dashboard/login.html";
}

function authHeaders() {
    const token = getToken();
    return token ? { "Authorization": "Bearer " + token } : {};
}

async function authFetch(url, options = {}) {
    const headers = { ...authHeaders(), ...(options.headers || {}) };
    const res = await fetch(url, { ...options, headers });
    if (res.status === 401) {
        clearAuth();
        window.location.href = "/dashboard/login.html";
        throw new Error("Session expired");
    }
    return res;
}

async function checkAuth() {
    const token = getToken();
    if (!token) {
        window.location.href = "/dashboard/login.html";
        return false;
    }
    try {
        const res = await fetch(API + "/v1/auth/me", { headers: authHeaders() });
        if (!res.ok) {
            clearAuth();
            window.location.href = "/dashboard/login.html";
            return false;
        }
        return true;
    } catch {
        clearAuth();
        window.location.href = "/dashboard/login.html";
        return false;
    }
}

function renderUserBadge(containerId) {
    const user = getUser();
    const el = document.getElementById(containerId);
    if (!el || !user) return;
    el.innerHTML = `
        <span class="user-email">${user.email || "User"}</span>
        <button class="logout-btn" onclick="logout()">Logout</button>
    `;
}
