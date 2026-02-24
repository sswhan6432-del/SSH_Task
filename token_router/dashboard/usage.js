/**
 * Usage Monitor - Fetch and display provider usage data.
 */

const API = window.location.origin;
let currentDays = 30;

// Period selector
document.querySelectorAll(".period-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".period-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        currentDays = parseInt(btn.dataset.days);
        loadAll();
    });
});

function fmt(n) {
    if (n == null) return "-";
    if (typeof n === "number") return n.toLocaleString();
    return String(n);
}

function fmtK(n) {
    if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
    if (n >= 1000) return (n / 1000).toFixed(1) + "K";
    return String(n);
}

function fmtDate(dateStr) {
    if (!dateStr) return "";
    const d = new Date(dateStr);
    return (d.getMonth() + 1) + "/" + d.getDate();
}

/**
 * Render a daily bar chart from an array of { date, input, output } objects.
 * Returns HTML string.
 */
function renderDailyChart(dailyData, colorClass) {
    if (!dailyData || dailyData.length === 0) return "";
    const maxVal = Math.max(...dailyData.map(d => d.input + d.output), 1);
    const barWidth = Math.max(4, Math.floor(600 / dailyData.length) - 2);

    let html = `<h3 class="sub-title">Daily Token Usage</h3>`;
    html += `<div class="daily-chart-wrap">`;
    html += `<div class="daily-y-axis">`;
    html += `<span>${fmtK(maxVal)}</span><span>${fmtK(Math.round(maxVal / 2))}</span><span>0</span>`;
    html += `</div>`;
    html += `<div class="daily-chart">`;

    for (const d of dailyData) {
        const total = d.input + d.output;
        const pct = (total / maxVal) * 100;
        const inputPct = total > 0 ? (d.input / total) * pct : 0;
        const outputPct = pct - inputPct;
        const label = fmtDate(d.date);
        html += `<div class="daily-bar-col" style="width:${barWidth}px">
            <div class="daily-bar-stack" style="height:${pct}%" title="${label}: ${fmt(total)} tokens (in:${fmt(d.input)} out:${fmt(d.output)})">
                <div class="daily-bar-seg output ${colorClass}" style="height:${outputPct > 0 ? (d.output/total*100) : 0}%"></div>
                <div class="daily-bar-seg input ${colorClass}-light" style="height:${inputPct > 0 ? (d.input/total*100) : 0}%"></div>
            </div>
            <span class="daily-bar-label">${label}</span>
        </div>`;
    }

    html += `</div></div>`;
    html += `<div class="chart-legend"><span class="legend-item"><span class="legend-dot ${colorClass}-light"></span>Input</span><span class="legend-item"><span class="legend-dot ${colorClass}"></span>Output</span></div>`;
    return html;
}

/**
 * Extract daily buckets from provider API response.
 * Handles various response formats from Anthropic and OpenAI.
 */
function extractDailyBuckets(usage) {
    if (!usage || !usage.data || !Array.isArray(usage.data)) return [];

    const dayMap = {};

    for (const bucket of usage.data) {
        // Try to get date from bucket-level fields
        const date = bucket.date || bucket.start_time || bucket.timestamp || bucket.day || null;
        const dateKey = date ? (typeof date === "number" ? new Date(date * 1000).toISOString().slice(0, 10) : String(date).slice(0, 10)) : null;

        const items = bucket.results || [bucket];
        for (const item of items) {
            // Per-item date overrides bucket date
            const itemDate = item.date || item.start_time || item.timestamp || dateKey;
            const key = itemDate ? (typeof itemDate === "number" ? new Date(itemDate * 1000).toISOString().slice(0, 10) : String(itemDate).slice(0, 10)) : dateKey;
            if (!key) continue;

            if (!dayMap[key]) dayMap[key] = { date: key, input: 0, output: 0 };
            dayMap[key].input += item.input_tokens || item.n_context_tokens_total || 0;
            dayMap[key].output += item.output_tokens || item.n_generated_tokens_total || 0;
        }
    }

    return Object.values(dayMap).sort((a, b) => a.date.localeCompare(b.date));
}

function fmtCost(n) {
    if (n == null) return "-";
    return "$" + Number(n).toFixed(4);
}

function setStatus(provider, text, type) {
    const el = document.getElementById("status-" + provider);
    if (!el) return;
    el.textContent = text;
    el.className = "card-status status-" + type;
}

function renderNoKey(provider) {
    setStatus(provider, "No API Key", "warn");
    document.getElementById("body-" + provider).innerHTML = `
        <div class="empty-state">
            <p>No API key configured.</p>
            <a href="/dashboard/settings.html" class="setup-link">Add key in Settings</a>
        </div>
    `;
}

function renderError(provider, msg) {
    setStatus(provider, "Error", "error");
    document.getElementById("body-" + provider).innerHTML = `
        <div class="empty-state error-state">
            <p>${msg || "Failed to fetch usage data."}</p>
        </div>
    `;
}

// ── Anthropic ──────────────────────────────────────────────

async function loadAnthropic() {
    setStatus("anthropic", "Loading...", "loading");
    try {
        const res = await authFetch(API + "/v1/usage/anthropic?days=" + currentDays);
        const data = await res.json();

        if (data.status === "no_key") return renderNoKey("anthropic");
        if (data.status !== "ok") return renderError("anthropic", data.error);

        setStatus("anthropic", "Active", "ok");
        const body = document.getElementById("body-anthropic");

        let html = "";

        // Usage data
        if (data.usage) {
            const usage = data.usage;
            // Try to extract summary metrics from various response formats
            if (usage.data && Array.isArray(usage.data)) {
                let totalInput = 0, totalOutput = 0;
                const modelMap = {};
                for (const bucket of usage.data) {
                    const items = bucket.results || [bucket];
                    for (const item of items) {
                        const model = item.model || "unknown";
                        const input = item.input_tokens || 0;
                        const output = item.output_tokens || 0;
                        totalInput += input;
                        totalOutput += output;
                        if (!modelMap[model]) modelMap[model] = { input: 0, output: 0 };
                        modelMap[model].input += input;
                        modelMap[model].output += output;
                    }
                }
                html += `<div class="metric-grid">
                    <div class="metric-item"><span class="metric-label">Input Tokens</span><span class="metric-value">${fmt(totalInput)}</span></div>
                    <div class="metric-item"><span class="metric-label">Output Tokens</span><span class="metric-value">${fmt(totalOutput)}</span></div>
                    <div class="metric-item"><span class="metric-label">Total Tokens</span><span class="metric-value">${fmt(totalInput + totalOutput)}</span></div>
                    <div class="metric-item"><span class="metric-label">Period</span><span class="metric-value">${currentDays}d</span></div>
                </div>`;

                // Daily chart
                const dailyBuckets = extractDailyBuckets(usage);
                if (dailyBuckets.length > 1) {
                    html += renderDailyChart(dailyBuckets, "bar-anthropic");
                }

                // Model breakdown
                const models = Object.entries(modelMap).sort((a,b) => (b[1].input+b[1].output) - (a[1].input+a[1].output));
                if (models.length > 0) {
                    html += `<h3 class="sub-title">By Model</h3><div class="model-breakdown">`;
                    const maxTokens = Math.max(...models.map(([,v]) => v.input + v.output));
                    for (const [model, v] of models) {
                        const total = v.input + v.output;
                        const pct = maxTokens > 0 ? (total / maxTokens * 100) : 0;
                        html += `<div class="breakdown-row">
                            <span class="breakdown-label">${model}</span>
                            <div class="breakdown-bar-track"><div class="breakdown-bar-fill fill-anthropic" style="width:${pct}%"></div></div>
                            <span class="breakdown-value">${fmt(total)}</span>
                        </div>`;
                    }
                    html += `</div>`;
                }
            } else {
                html += `<div class="raw-data"><pre>${JSON.stringify(usage, null, 2)}</pre></div>`;
            }
        }

        // Cost data
        if (data.costs) {
            html += `<h3 class="sub-title">Cost Report</h3>`;
            if (data.costs.data && Array.isArray(data.costs.data)) {
                let totalCost = 0;
                for (const bucket of data.costs.data) {
                    totalCost += bucket.cost_usd || bucket.total_cost || 0;
                }
                html += `<div class="cost-highlight">${fmtCost(totalCost)}<span class="cost-period"> / ${currentDays}d</span></div>`;
            } else {
                html += `<div class="raw-data"><pre>${JSON.stringify(data.costs, null, 2)}</pre></div>`;
            }
        }

        if (!data.usage && !data.costs) {
            html = `<div class="empty-state"><p>No usage data returned. Verify your Admin API key has the correct permissions.</p></div>`;
        }

        body.innerHTML = html;
    } catch (e) {
        renderError("anthropic", e.message);
    }
}

// ── OpenAI ─────────────────────────────────────────────────

async function loadOpenAI() {
    setStatus("openai", "Loading...", "loading");
    try {
        const res = await authFetch(API + "/v1/usage/openai?days=" + currentDays);
        const data = await res.json();

        if (data.status === "no_key") return renderNoKey("openai");
        if (data.status !== "ok") return renderError("openai", data.error);

        setStatus("openai", "Active", "ok");
        const body = document.getElementById("body-openai");

        let html = "";

        if (data.usage) {
            const usage = data.usage;
            if (usage.data && Array.isArray(usage.data)) {
                let totalInput = 0, totalOutput = 0, totalRequests = 0;
                const modelMap = {};
                for (const bucket of usage.data) {
                    const items = bucket.results || [bucket];
                    for (const item of items) {
                        const model = item.model || item.snapshot_id || "unknown";
                        const input = item.input_tokens || item.n_context_tokens_total || 0;
                        const output = item.output_tokens || item.n_generated_tokens_total || 0;
                        const reqs = item.num_requests || item.n_requests || 0;
                        totalInput += input;
                        totalOutput += output;
                        totalRequests += reqs;
                        if (!modelMap[model]) modelMap[model] = { input: 0, output: 0, requests: 0 };
                        modelMap[model].input += input;
                        modelMap[model].output += output;
                        modelMap[model].requests += reqs;
                    }
                }
                html += `<div class="metric-grid">
                    <div class="metric-item"><span class="metric-label">Input Tokens</span><span class="metric-value">${fmt(totalInput)}</span></div>
                    <div class="metric-item"><span class="metric-label">Output Tokens</span><span class="metric-value">${fmt(totalOutput)}</span></div>
                    <div class="metric-item"><span class="metric-label">Total Tokens</span><span class="metric-value">${fmt(totalInput + totalOutput)}</span></div>
                    <div class="metric-item"><span class="metric-label">Requests</span><span class="metric-value">${fmt(totalRequests)}</span></div>
                </div>`;

                // Daily chart
                const dailyBucketsOai = extractDailyBuckets(usage);
                if (dailyBucketsOai.length > 1) {
                    html += renderDailyChart(dailyBucketsOai, "bar-openai");
                }

                const models = Object.entries(modelMap).sort((a,b) => (b[1].input+b[1].output) - (a[1].input+a[1].output));
                if (models.length > 0) {
                    html += `<h3 class="sub-title">By Model</h3><div class="model-breakdown">`;
                    const maxTokens = Math.max(...models.map(([,v]) => v.input + v.output));
                    for (const [model, v] of models) {
                        const total = v.input + v.output;
                        const pct = maxTokens > 0 ? (total / maxTokens * 100) : 0;
                        html += `<div class="breakdown-row">
                            <span class="breakdown-label">${model}</span>
                            <div class="breakdown-bar-track"><div class="breakdown-bar-fill fill-openai" style="width:${pct}%"></div></div>
                            <span class="breakdown-value">${fmt(total)}</span>
                        </div>`;
                    }
                    html += `</div>`;
                }
            } else {
                html += `<div class="raw-data"><pre>${JSON.stringify(usage, null, 2)}</pre></div>`;
            }
        }

        if (data.costs) {
            html += `<h3 class="sub-title">Cost Report</h3>`;
            if (data.costs.data && Array.isArray(data.costs.data)) {
                let totalCost = 0;
                for (const bucket of data.costs.data) {
                    const items = bucket.results || [bucket];
                    for (const item of items) {
                        totalCost += item.amount?.value || item.cost_usd || 0;
                    }
                }
                html += `<div class="cost-highlight">${fmtCost(totalCost)}<span class="cost-period"> / ${currentDays}d</span></div>`;
            } else {
                html += `<div class="raw-data"><pre>${JSON.stringify(data.costs, null, 2)}</pre></div>`;
            }
        }

        if (!data.usage && !data.costs) {
            html = `<div class="empty-state"><p>No usage data returned. Verify your API key has organization access.</p></div>`;
        }

        body.innerHTML = html;
    } catch (e) {
        renderError("openai", e.message);
    }
}

// ── DeepSeek ───────────────────────────────────────────────

async function loadDeepSeek() {
    setStatus("deepseek", "Loading...", "loading");
    try {
        const res = await authFetch(API + "/v1/usage/deepseek");
        const data = await res.json();

        if (data.status === "no_key") return renderNoKey("deepseek");
        if (data.status !== "ok") return renderError("deepseek", data.error);

        setStatus("deepseek", "Active", "ok");
        const body = document.getElementById("body-deepseek");

        let html = "";
        if (data.balance) {
            const bal = data.balance;
            // DeepSeek balance format: { balance_infos: [{ currency, total_balance, granted_balance, topped_up_balance }] }
            if (bal.balance_infos && Array.isArray(bal.balance_infos)) {
                for (const info of bal.balance_infos) {
                    html += `<div class="metric-grid">
                        <div class="metric-item"><span class="metric-label">Total Balance</span><span class="metric-value">${info.currency || ""} ${info.total_balance || "0"}</span></div>
                        <div class="metric-item"><span class="metric-label">Granted</span><span class="metric-value">${info.granted_balance || "0"}</span></div>
                        <div class="metric-item"><span class="metric-label">Topped Up</span><span class="metric-value">${info.topped_up_balance || "0"}</span></div>
                    </div>`;
                }
            } else if (bal.available !== undefined || bal.balance !== undefined) {
                html += `<div class="metric-grid">
                    <div class="metric-item"><span class="metric-label">Balance</span><span class="metric-value">${fmtCost(bal.available || bal.balance)}</span></div>
                </div>`;
            } else {
                html += `<div class="raw-data"><pre>${JSON.stringify(bal, null, 2)}</pre></div>`;
            }
        } else {
            html = `<div class="empty-state"><p>No balance data returned.</p></div>`;
        }

        body.innerHTML = html;
    } catch (e) {
        renderError("deepseek", e.message);
    }
}

// ── Load All ───────────────────────────────────────────────

function loadAll() {
    loadAnthropic();
    loadOpenAI();
    loadDeepSeek();
}

loadAll();
