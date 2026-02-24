/**
 * TokenRouter Dashboard - Auto-refreshing stats display.
 */

const API_BASE = window.location.origin;
const REFRESH_INTERVAL = 5000;

function formatNumber(n) {
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
    if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
    return n.toLocaleString();
}

function formatCost(n) {
    if (n < 0.01) return "$" + n.toFixed(4);
    return "$" + n.toFixed(2);
}

function renderBarChart(containerId, data) {
    const container = document.getElementById(containerId);
    if (!data || Object.keys(data).length === 0) {
        container.innerHTML = '<div class="empty-state">No data yet</div>';
        return;
    }

    const max = Math.max(...Object.values(data), 1);
    container.innerHTML = Object.entries(data)
        .sort((a, b) => b[1] - a[1])
        .map(([label, count]) => {
            const pct = (count / max) * 100;
            return `
                <div class="bar-item">
                    <span class="bar-label">${label}</span>
                    <div class="bar-track">
                        <div class="bar-fill" style="width: ${pct}%"></div>
                    </div>
                    <span class="bar-count">${formatNumber(count)}</span>
                </div>
            `;
        })
        .join("");
}

function renderModels(models) {
    const container = document.getElementById("models-list");
    if (!models || models.length === 0) {
        container.innerHTML = '<div class="empty-state">No models loaded</div>';
        return;
    }

    container.innerHTML = models
        .map(m => `
            <div class="model-tag">
                <div>${m.id}</div>
                <div class="provider">${m.owned_by} &middot; $${m.pricing.input_per_1m}/1M</div>
            </div>
        `)
        .join("");
}

async function refresh() {
    try {
        const hdrs = typeof authHeaders === "function" ? authHeaders() : {};
        const [statsRes, modelsRes] = await Promise.all([
            fetch(API_BASE + "/v1/stats", { headers: hdrs }),
            fetch(API_BASE + "/v1/models", { headers: hdrs }),
        ]);

        if (statsRes.ok) {
            const stats = await statsRes.json();
            document.getElementById("total-requests").textContent = formatNumber(stats.total_requests);
            document.getElementById("total-tokens").textContent = formatNumber(stats.total_tokens);
            document.getElementById("total-cost").textContent = formatCost(stats.total_cost_usd);
            document.getElementById("total-savings").textContent = formatCost(stats.total_savings_usd);
            document.getElementById("avg-latency").textContent = Math.round(stats.avg_latency_ms) + "ms";
            document.getElementById("cache-rate").textContent = Math.round(stats.cache_hit_rate * 100) + "%";

            renderBarChart("provider-chart", stats.requests_by_provider);
            renderBarChart("model-chart", stats.requests_by_model);
        }

        if (modelsRes.ok) {
            const models = await modelsRes.json();
            renderModels(models.data || []);
        }
    } catch (err) {
        console.error("Dashboard refresh failed:", err);
    }
}

// Initial load + auto-refresh
refresh();
setInterval(refresh, REFRESH_INTERVAL);
