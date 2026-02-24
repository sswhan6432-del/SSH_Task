/**
 * Claude Analytics Dashboard - Deep AI usage insights.
 */

const API = window.location.origin;
const REFRESH = 5000;

const PROVIDER_COLORS = {
    groq: "#f97316", openai: "#10b981", anthropic: "#2563eb",
    google: "#4285f4", deepseek: "#6366f1",
};

function fmt(n) {
    if (n >= 1e6) return (n / 1e6).toFixed(1) + "M";
    if (n >= 1e3) return (n / 1e3).toFixed(1) + "K";
    return n.toLocaleString();
}

function fmtCost(n) {
    if (n === 0) return "$0.00";
    if (n < 0.01) return "$" + n.toFixed(4);
    return "$" + n.toFixed(2);
}

function renderDonut(id, data) {
    const el = document.getElementById(id);
    if (!data || Object.keys(data).length === 0) {
        el.innerHTML = '<div class="empty-state">No data yet</div>';
        return;
    }
    const total = Object.values(data).reduce((a, d) => a + d.requests, 0) || 1;
    el.innerHTML = Object.entries(data)
        .filter(([, d]) => d.requests > 0)
        .sort((a, b) => b[1].requests - a[1].requests)
        .map(([name, d]) => {
            const pct = ((d.requests / total) * 100).toFixed(1);
            const color = PROVIDER_COLORS[name] || "#86868b";
            return `<div class="donut-item">
                <div class="donut-color" style="background:${color}"></div>
                <span class="donut-label">${name}</span>
                <span class="donut-value">${fmt(d.requests)}</span>
                <span class="donut-pct">${pct}%</span>
            </div>`;
        }).join("");
}

function renderBars(id, items) {
    const el = document.getElementById(id);
    if (!items || items.length === 0) {
        el.innerHTML = '<div class="empty-state">No data yet</div>';
        return;
    }
    const max = Math.max(...items.map(i => i.requests), 1);
    el.innerHTML = items.map(item => {
        const pct = (item.requests / max) * 100;
        const provider = item.model.split("/")[0];
        const fillClass = `fill-${provider}` || "fill-default";
        return `<div class="bar-item">
            <span class="bar-label">${item.model}</span>
            <div class="bar-track"><div class="bar-fill ${fillClass}" style="width:${pct}%"></div></div>
            <span class="bar-count">${fmt(item.requests)}</span>
        </div>`;
    }).join("");
}

function renderIntentCloud(id, data) {
    const el = document.getElementById(id);
    if (!data || Object.keys(data).length === 0) {
        el.innerHTML = '<div class="empty-state">No intent data (use model=auto)</div>';
        return;
    }
    el.innerHTML = Object.entries(data)
        .sort((a, b) => b[1] - a[1])
        .map(([intent, count]) => {
            return `<span class="tag ${intent}">${intent}<span class="tag-count">${count}</span></span>`;
        }).join("");
}

function renderDifficulty(id, data) {
    const el = document.getElementById(id);
    const levels = ["simple", "medium", "complex"];
    const classes = { simple: "diff-simple", medium: "diff-medium", complex: "diff-complex" };
    const total = Object.values(data || {}).reduce((a, b) => a + b, 0) || 1;

    if (!data || Object.keys(data).length === 0) {
        el.innerHTML = '<div class="empty-state">No difficulty data (use model=auto)</div>';
        return;
    }

    el.innerHTML = levels.map(level => {
        const count = data[level] || 0;
        const pct = (count / total) * 100;
        return `<div class="diff-row">
            <span class="diff-label">${level}</span>
            <div class="diff-bar-track">
                <div class="diff-bar-fill ${classes[level]}" style="width:${pct}%">${pct > 15 ? Math.round(pct) + "%" : ""}</div>
            </div>
            <span class="diff-count">${count}</span>
        </div>`;
    }).join("");
}

function renderTimeline(id, data) {
    const el = document.getElementById(id);
    if (!data || data.length === 0) {
        el.innerHTML = '<div class="empty-state">No timeline data</div>';
        return;
    }
    const maxReq = Math.max(...data.map(d => d.requests), 1);
    el.innerHTML = data.map(d => {
        const h = Math.max((d.requests / maxReq) * 100, 2);
        return `<div class="timeline-bar" style="height:${h}%">
            <div class="tooltip">${d.hour}: ${d.requests} req, ${fmt(d.tokens)} tok</div>
        </div>`;
    }).join("");
}

async function refresh() {
    try {
        const res = await fetch(API + "/v1/stats/claude");
        if (!res.ok) return;
        const d = await res.json();

        // Hero
        document.getElementById("savings-pct").textContent = d.cost_optimization.savings_pct + "%";
        document.getElementById("opus-cost").textContent = fmtCost(d.cost_optimization.opus_equivalent_usd);
        document.getElementById("actual-cost").textContent = fmtCost(d.cost_optimization.actual_cost_usd);
        document.getElementById("savings-usd").textContent = fmtCost(d.cost_optimization.savings_usd);
        document.getElementById("total-all").textContent = fmt(d.total_requests_all);
        document.getElementById("total-claude").textContent = fmt(d.total_requests_claude);

        // Claude models
        const cm = d.claude_models || {};
        const opus = cm["anthropic/claude-opus"] || {};
        const sonnet = cm["anthropic/claude-sonnet"] || {};
        const haiku = cm["anthropic/claude-haiku"] || {};

        document.getElementById("opus-requests").textContent = fmt(opus.requests || 0);
        document.getElementById("opus-tokens").textContent = fmt(opus.total_tokens || 0);
        document.getElementById("opus-model-cost").textContent = fmtCost(opus.cost_usd || 0);
        document.getElementById("opus-latency").textContent = Math.round(opus.avg_latency_ms || 0) + "ms";

        document.getElementById("sonnet-requests").textContent = fmt(sonnet.requests || 0);
        document.getElementById("sonnet-tokens").textContent = fmt(sonnet.total_tokens || 0);
        document.getElementById("sonnet-model-cost").textContent = fmtCost(sonnet.cost_usd || 0);
        document.getElementById("sonnet-latency").textContent = Math.round(sonnet.avg_latency_ms || 0) + "ms";

        document.getElementById("haiku-requests").textContent = fmt(haiku.requests || 0);
        document.getElementById("haiku-tokens").textContent = fmt(haiku.total_tokens || 0);
        document.getElementById("haiku-model-cost").textContent = fmtCost(haiku.cost_usd || 0);
        document.getElementById("haiku-latency").textContent = Math.round(haiku.avg_latency_ms || 0) + "ms";

        // Charts
        renderDonut("provider-donut", d.provider_comparison);
        renderBars("top-models-chart", d.top_models);
        renderIntentCloud("intent-cloud", d.intent_distribution);
        renderDifficulty("difficulty-chart", d.difficulty_distribution);
        renderTimeline("timeline-chart", d.timeline_24h);

    } catch (e) {
        console.error("Refresh failed:", e);
    }
}

refresh();
setInterval(refresh, REFRESH);
