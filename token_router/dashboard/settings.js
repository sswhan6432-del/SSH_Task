/**
 * Settings page - Provider API key management (Zero-Knowledge Encryption).
 *
 * All API keys are encrypted in the browser with AES-256-GCM before
 * being sent to the server. The server only stores encrypted blobs.
 * Decryption happens exclusively in this browser tab.
 */

// API is defined in auth.js (loaded first)
// crypto.js provides: loadEncryptionKey, encryptString, decryptString, maskKey, hasEncryptionKey

const PROVIDERS = [
    { id: "anthropic", name: "Anthropic", desc: "Claude models (Opus, Sonnet, Haiku)", keyHint: "sk-ant-admin-...", hasUsage: true },
    { id: "openai", name: "OpenAI", desc: "GPT-4o, GPT-4o-mini", keyHint: "sk-...", hasUsage: true },
    { id: "deepseek", name: "DeepSeek", desc: "DeepSeek Chat, Coder", keyHint: "sk-...", hasUsage: true },
    { id: "google", name: "Google", desc: "Gemini models", keyHint: "AI...", hasUsage: false },
    { id: "groq", name: "Groq", desc: "Llama, Mixtral (fast inference)", keyHint: "gsk_...", hasUsage: false },
];

let savedKeys = {};  // provider -> { encrypted_key, label, ... }
let encKey = null;   // CryptoKey for encrypt/decrypt

async function initCrypto() {
    encKey = await loadEncryptionKey();
    if (!encKey) {
        // No encryption key = session expired, need re-login
        document.getElementById("provider-list").innerHTML = `
            <div class="relogin-banner">
                <p>Encryption key not available. Please log in again to manage API keys.</p>
                <a href="/dashboard/login.html" class="btn btn-primary">Log In</a>
            </div>
        `;
        return false;
    }
    return true;
}

async function loadKeys() {
    if (!await initCrypto()) return;

    try {
        const res = await authFetch(API + "/v1/settings/keys");
        if (!res.ok) return;
        const data = await res.json();
        savedKeys = {};
        for (const k of data.keys) {
            savedKeys[k.provider] = k;
        }
    } catch (e) {
        console.error("Failed to load keys:", e);
    }
    await render();
}

async function render() {
    const container = document.getElementById("provider-list");
    const cards = [];

    for (const p of PROVIDERS) {
        const saved = savedKeys[p.id];
        const statusClass = saved ? "status-active" : "status-inactive";
        const statusText = saved ? "Encrypted" : "Not configured";

        // Decrypt for masked display (client-side only)
        let maskedDisplay = "";
        if (saved && encKey) {
            try {
                const plainKey = await decryptString(saved.encrypted_key, encKey);
                maskedDisplay = maskKey(plainKey);
            } catch {
                maskedDisplay = "[decryption failed]";
            }
        }

        cards.push(`
        <div class="provider-card" id="card-${p.id}">
            <div class="provider-header">
                <div class="provider-info">
                    <span class="provider-name">${p.name}</span>
                    <span class="provider-desc">${p.desc}</span>
                </div>
                <div class="provider-status">
                    <span class="status-dot ${statusClass}"></span>
                    <span class="status-text">${statusText}</span>
                    ${!p.hasUsage ? `<span class="no-api-badge">No Usage API</span>` : ""}
                </div>
            </div>
            ${saved ? `
            <div class="provider-key-display">
                <code class="masked-key">${maskedDisplay}</code>
                <span class="encrypted-badge">E2E Encrypted</span>
                ${saved.label ? `<span class="key-label">${saved.label}</span>` : ""}
            </div>
            ` : ""}
            <div class="provider-actions" id="actions-${p.id}">
                <div class="input-row" id="input-row-${p.id}" style="display:${saved ? 'none' : 'flex'}">
                    <input type="password" id="key-input-${p.id}" class="key-input" placeholder="${p.keyHint}" autocomplete="off">
                    <input type="text" id="label-input-${p.id}" class="label-input" placeholder="Label (optional)">
                    <button class="btn btn-save" onclick="saveKey('${p.id}')">Encrypt & Save</button>
                    ${saved ? `<button class="btn btn-cancel" onclick="toggleInput('${p.id}', false)">Cancel</button>` : ""}
                </div>
                ${saved ? `
                <div class="btn-row" id="btn-row-${p.id}" style="display:flex">
                    <button class="btn btn-primary" onclick="toggleInput('${p.id}', true)">Update Key</button>
                    <button class="btn btn-danger" onclick="deleteKey('${p.id}')">Remove</button>
                </div>
                ` : ""}
            </div>
        </div>
        `);
    }

    container.innerHTML = cards.join("");
}

function toggleInput(provider, show) {
    document.getElementById("input-row-" + provider).style.display = show ? "flex" : "none";
    const btnRow = document.getElementById("btn-row-" + provider);
    if (btnRow) btnRow.style.display = show ? "none" : "flex";
    if (show) {
        document.getElementById("key-input-" + provider).focus();
    }
}

async function saveKey(provider) {
    const keyInput = document.getElementById("key-input-" + provider);
    const labelInput = document.getElementById("label-input-" + provider);
    const rawKey = keyInput.value.trim();
    if (!rawKey) {
        keyInput.classList.add("input-error");
        setTimeout(() => keyInput.classList.remove("input-error"), 1000);
        return;
    }

    if (!encKey) {
        alert("Encryption key not available. Please log in again.");
        return;
    }

    try {
        // Encrypt the API key in the browser before sending
        const encrypted = await encryptString(rawKey, encKey);

        const res = await authFetch(API + "/v1/settings/keys/" + provider, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ encrypted_key: encrypted, label: labelInput.value.trim() }),
        });
        if (res.ok) {
            keyInput.value = "";
            labelInput.value = "";
            await loadKeys();
        }
    } catch (e) {
        console.error("Save failed:", e);
    }
}

async function deleteKey(provider) {
    if (!confirm(`Remove ${provider} API key?`)) return;
    try {
        const res = await authFetch(API + "/v1/settings/keys/" + provider, { method: "DELETE" });
        if (res.ok) await loadKeys();
    } catch (e) {
        console.error("Delete failed:", e);
    }
}

// Init: loadKeys() is called from settings.html after checkAuth()
