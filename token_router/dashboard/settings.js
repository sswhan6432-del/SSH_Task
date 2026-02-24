/**
 * Settings page - Provider API key management.
 */

// API is defined in auth.js (loaded first)

const PROVIDERS = [
    { id: "anthropic", name: "Anthropic", desc: "Claude models (Opus, Sonnet, Haiku)", keyHint: "sk-ant-admin-...", hasUsage: true },
    { id: "openai", name: "OpenAI", desc: "GPT-4o, GPT-4o-mini", keyHint: "sk-...", hasUsage: true },
    { id: "deepseek", name: "DeepSeek", desc: "DeepSeek Chat, Coder", keyHint: "sk-...", hasUsage: true },
    { id: "google", name: "Google", desc: "Gemini models", keyHint: "AI...", hasUsage: false },
    { id: "groq", name: "Groq", desc: "Llama, Mixtral (fast inference)", keyHint: "gsk_...", hasUsage: false },
];

let savedKeys = {};

async function loadKeys() {
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
    render();
}

function render() {
    const container = document.getElementById("provider-list");
    container.innerHTML = PROVIDERS.map(p => {
        const saved = savedKeys[p.id];
        const statusClass = saved ? "status-active" : "status-inactive";
        const statusText = saved ? "Active" : "Not configured";
        const maskedKey = saved ? saved.masked_key : "";

        return `
        <div class="provider-card" id="card-${p.id}">
            <div class="provider-header">
                <div class="provider-info">
                    <span class="provider-name">${p.name}</span>
                    <span class="provider-desc">${p.desc}</span>
                </div>
                <div class="provider-status">
                    <span class="status-dot ${statusClass}"></span>
                    <span class="status-text">${statusText}</span>
                </div>
            </div>
            ${saved ? `
            <div class="provider-key-display">
                <code class="masked-key">${maskedKey}</code>
                ${saved.label ? `<span class="key-label">${saved.label}</span>` : ""}
            </div>
            ` : ""}
            <div class="provider-actions" id="actions-${p.id}">
                <div class="input-row" id="input-row-${p.id}" style="display:none">
                    <input type="password" id="key-input-${p.id}" class="key-input" placeholder="${p.keyHint}" autocomplete="off">
                    <input type="text" id="label-input-${p.id}" class="label-input" placeholder="Label (optional)">
                    <button class="btn btn-save" onclick="saveKey('${p.id}')">Save</button>
                    <button class="btn btn-cancel" onclick="toggleInput('${p.id}', false)">Cancel</button>
                </div>
                <div class="btn-row" id="btn-row-${p.id}" style="display:flex">
                    <button class="btn btn-primary" onclick="toggleInput('${p.id}', true)">${saved ? "Update Key" : "Add Key"}</button>
                    ${saved ? `<button class="btn btn-danger" onclick="deleteKey('${p.id}')">Remove</button>` : ""}
                    ${!p.hasUsage ? `<span class="no-api-badge">No Usage API</span>` : ""}
                </div>
            </div>
        </div>
        `;
    }).join("");
}

function toggleInput(provider, show) {
    document.getElementById("input-row-" + provider).style.display = show ? "flex" : "none";
    document.getElementById("btn-row-" + provider).style.display = show ? "none" : "flex";
    if (show) {
        document.getElementById("key-input-" + provider).focus();
    }
}

async function saveKey(provider) {
    const keyInput = document.getElementById("key-input-" + provider);
    const labelInput = document.getElementById("label-input-" + provider);
    const apiKey = keyInput.value.trim();
    if (!apiKey) {
        keyInput.classList.add("input-error");
        setTimeout(() => keyInput.classList.remove("input-error"), 1000);
        return;
    }

    try {
        const res = await authFetch(API + "/v1/settings/keys/" + provider, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ api_key: apiKey, label: labelInput.value.trim() }),
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
