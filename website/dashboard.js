/**
 * Enterprise Dashboard — Real-time analytics with SSE.
 * Vanilla JS, SVG gauge, Canvas 2D charts, CSS grid heatmap.
 */

(function () {
  'use strict';

  // ─── State ───
  let currentPeriod = '24h';
  let sseSource = null;
  let fetchController = null;
  const alerts = [];
  const MAX_TOASTS = 5;
  const MODEL_COLORS = {
    opus: '#000000',
    sonnet: '#4a90d9',
    haiku: '#86868b',
    mixed: '#555555',
    claude: '#1a1a1a',
    cheap_llm: '#b0b0b5',
    split: '#a0a0a5',
    groq: '#f55036',
    gpt: '#10a37f',
  };

  // ─── DOM refs ───
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  // ─── Init ───
  document.addEventListener('DOMContentLoaded', () => {
    initNav();
    initPeriodSelector();
    fetchDashboardData();
    // SSE only works with local Python backend
    if (!window.supabaseClient) connectSSE();
  });

  // ─── Cleanup on page exit (prevent SSE memory leak) ───
  window.addEventListener('beforeunload', () => {
    if (sseSource) {
      sseSource.close();
      sseSource = null;
    }
    if (fetchController) {
      fetchController.abort();
      fetchController = null;
    }
  });

  // ─── Navigation toggle (same pattern as other pages) ───
  function initNav() {
    const toggle = $('#nav-toggle');
    const menu = $('#mobile-menu');
    if (toggle && menu) {
      toggle.addEventListener('click', () => {
        menu.classList.toggle('open');
        toggle.classList.toggle('open');
      });
      menu.querySelectorAll('a').forEach((a) => {
        a.addEventListener('click', () => {
          menu.classList.remove('open');
          toggle.classList.remove('open');
        });
      });
    }
  }

  // ─── Period Selector with debounce ───
  function initPeriodSelector() {
    let debounceTimer = null;
    $$('.period-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        $$('.period-btn').forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        currentPeriod = btn.dataset.period;
        // Debounce rapid clicks
        if (debounceTimer) clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => fetchDashboardData(), 150);
      });
    });
  }

  // ─── Fetch Dashboard Data with AbortController ───
  async function fetchDashboardData() {
    // If Supabase is available, aggregate from DB
    if (window.supabaseData) {
      try {
        await fetchFromSupabase();
      } catch (err) {
        renderEmptyCharts();
      }
      return;
    }

    // Cancel any in-flight request
    if (fetchController) fetchController.abort();
    fetchController = new AbortController();
    const signal = fetchController.signal;

    try {
      const [analyticsRes, costRes, budgetRes] = await Promise.allSettled([
        fetch(`/api/v2/analytics?period=${currentPeriod}`, { signal }),
        fetch('/api/cost-stats', { signal }),
        fetch('/api/v2/budget', { signal }),
      ]);

      // Analytics data (v2)
      if (analyticsRes.status === 'fulfilled' && analyticsRes.value.ok) {
        const data = await analyticsRes.value.json();
        renderAnalytics(data);
      } else {
        // Fallback: use v1 cost-stats
        if (costRes.status === 'fulfilled' && costRes.value.ok) {
          const data = await costRes.value.json();
          renderFallbackStats(data);
        }
        renderEmptyCharts();
      }

      // Budget data
      if (budgetRes.status === 'fulfilled' && budgetRes.value.ok) {
        const data = await budgetRes.value.json();
        renderBudget(data.budgets || []);
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        renderEmptyCharts();
      }
    }
  }

  // ─── Supabase-based dashboard data ───
  async function fetchFromSupabase() {
    const COST_PER_1K = { claude: 0.015, cheap_llm: 0.0005, split: 0.008 };
    const TOKENS_PER_TASK = { claude: 2000, cheap_llm: 500, split: 1200 };

    const historyRows = await window.supabaseData.history.list();
    const feedbackRows = await window.supabaseData.feedback.list();

    // Period filter
    const now = new Date();
    let cutoff;
    if (currentPeriod === '24h') cutoff = new Date(now - 24 * 60 * 60 * 1000);
    else if (currentPeriod === '7d') cutoff = new Date(now - 7 * 24 * 60 * 60 * 1000);
    else cutoff = new Date(now - 30 * 24 * 60 * 60 * 1000);

    const filtered = historyRows.filter(function (r) {
      return new Date(r.created_at) >= cutoff;
    });

    // Compute stats
    let totalTokens = 0, totalCost = 0, routeCounts = {};
    filtered.forEach(function (entry) {
      const tasks = entry.tasks || [];
      if (tasks.length) {
        tasks.forEach(function (t) {
          const r = t.route || entry.route || 'claude';
          const tk = TOKENS_PER_TASK[r] || 1000;
          totalTokens += tk;
          totalCost += (tk / 1000) * (COST_PER_1K[r] || 0.01);
          routeCounts[r] = (routeCounts[r] || 0) + 1;
        });
      } else {
        const r = entry.route || 'claude';
        const tk = TOKENS_PER_TASK[r] || 1000;
        totalTokens += tk;
        totalCost += (tk / 1000) * (COST_PER_1K[r] || 0.01);
        routeCounts[r] = (routeCounts[r] || 0) + 1;
      }
    });

    const days = currentPeriod === '24h' ? 1 : currentPeriod === '7d' ? 7 : 30;
    const dailyRate = Math.round(totalTokens / days);

    safeText('#stat-tokens', formatNumber(totalTokens));
    safeText('#stat-cost', '$' + totalCost.toFixed(2));
    safeText('#stat-requests', formatNumber(filtered.length));
    safeText('#stat-burn-rate', formatNumber(dailyRate));

    safeText('#burn-daily', formatNumber(dailyRate) + ' tokens');
    safeText('#burn-monthly', formatNumber(dailyRate * 30) + ' tokens');
    safeText('#burn-cost', '$' + (totalCost / days * 30).toFixed(2));

    renderDonut(routeCounts);

    // Cost trends by date
    const dateMap = {};
    filtered.forEach(function (entry) {
      const d = (entry.created_at || '').slice(0, 10);
      if (!d) return;
      if (!dateMap[d]) dateMap[d] = 0;
      const tasks = entry.tasks || [{ route: entry.route || 'claude' }];
      tasks.forEach(function (t) {
        const r = t.route || entry.route || 'claude';
        const tk = TOKENS_PER_TASK[r] || 1000;
        dateMap[d] += (tk / 1000) * (COST_PER_1K[r] || 0.01);
      });
    });
    const trends = Object.keys(dateMap).sort().map(function (date) {
      return { date: date, cost: dateMap[date] };
    });
    renderCostChart(trends);

    // Heatmap
    const heatmap = [];
    for (let i = 0; i < 7; i++) heatmap.push(new Array(24).fill(0));
    filtered.forEach(function (entry) {
      var d = new Date(entry.created_at);
      var day = (d.getDay() + 6) % 7; // Mon=0
      var hour = d.getHours();
      heatmap[day][hour]++;
    });
    renderHeatmap(heatmap);
    renderLatency({});
    renderBudget([]);

    // Connection status
    const dot = $('#connection-dot');
    const text = $('#connection-text');
    if (dot && text) {
      dot.classList.add('connected');
      text.textContent = 'Supabase (Live)';
    }
  }

  // ─── Render Analytics (v2 data) ───
  function renderAnalytics(data) {
    const burn = data.burn_rate || {};
    safeText('#stat-tokens', formatNumber(burn.total_tokens || 0));
    safeText('#stat-cost', '$' + (burn.total_cost || 0).toFixed(2));
    safeText('#stat-requests', formatNumber(burn.request_count || 0));
    safeText('#stat-burn-rate', formatNumber(burn.daily_token_rate || 0));

    safeText('#burn-daily', formatNumber(burn.daily_token_rate || 0) + ' tokens');
    safeText('#burn-monthly', formatNumber(burn.monthly_projection || 0) + ' tokens');
    safeText('#burn-cost', '$' + (burn.monthly_cost_projection || 0).toFixed(2));

    renderHeatmap(data.heatmap || []);
    renderLatency(data.latency || {});
    renderCostChart(data.cost_trends || []);
    renderDonut(data.model_distribution || {});
  }

  // ─── Render Fallback Stats (v1 data) ───
  function renderFallbackStats(data) {
    safeText('#stat-tokens', formatNumber(data.total_tokens || 0));
    safeText('#stat-cost', '$' + (data.total_cost || 0).toFixed(2));
    safeText('#stat-requests', formatNumber(data.total_sessions || 0));
    safeText('#stat-burn-rate', '\u2014');

    renderDonut(data.route_counts || {});
  }

  // ─── Empty Charts ───
  function renderEmptyCharts() {
    renderHeatmap([]);
    renderLatency({});
    renderCostChart([]);
  }

  // ─── Budget Gauge ───
  function renderBudget(budgets) {
    const gaugeFill = $('#gauge-fill');
    const gaugePct = $('#gauge-pct');
    const gaugeLabel = $('#gauge-label');
    const details = $('#budget-details');
    if (!gaugeFill || !gaugePct || !gaugeLabel || !details) return;

    if (!budgets.length) {
      gaugeFill.style.strokeDashoffset = '251';
      gaugePct.textContent = '0%';
      gaugeLabel.textContent = 'No budget set';
      details.textContent = 'Create a budget via API to track usage.';
      return;
    }

    const b = budgets[0];
    const pct = Math.min(100, b.usage_pct || 0);
    const offset = 251 - (251 * pct) / 100;

    gaugeFill.style.strokeDashoffset = offset;
    gaugePct.textContent = pct.toFixed(0) + '%';
    gaugeLabel.textContent = b.name;

    if (pct >= 90) gaugeFill.setAttribute('stroke', '#ef4444');
    else if (pct >= 80) gaugeFill.setAttribute('stroke', '#f59e0b');
    else gaugeFill.setAttribute('stroke', 'var(--black)');

    details.textContent = formatNumber(b.used) + ' / ' + formatNumber(b.limit) + ' tokens (' + b.period + ')';
  }

  // ─── Donut Chart (Canvas 2D) ───
  function renderDonut(distribution) {
    const canvas = $('#donut-chart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;

    canvas.width = canvas.offsetWidth * dpr;
    canvas.height = canvas.offsetHeight * dpr;
    ctx.scale(dpr, dpr);

    const w = canvas.offsetWidth;
    const h = canvas.offsetHeight;
    const cx = w / 2;
    const cy = h / 2;
    const radius = Math.min(cx, cy) - 20;
    const thickness = 24;

    ctx.clearRect(0, 0, w, h);

    const entries = Object.entries(distribution);
    const total = entries.reduce((sum, [, v]) => sum + v, 0);

    if (total === 0) {
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(0,0,0,0.08)';
      ctx.lineWidth = thickness;
      ctx.stroke();

      ctx.fillStyle = '#86868b';
      ctx.font = '14px -apple-system, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('No data', cx, cy + 5);

      const legend = $('#donut-legend');
      if (legend) legend.innerHTML = '';
      return;
    }

    let startAngle = -Math.PI / 2;
    const colors = [];

    entries.forEach(([key, value]) => {
      const slice = (value / total) * Math.PI * 2;
      const color = getModelColor(key);
      colors.push({ key, color, value });

      ctx.beginPath();
      ctx.arc(cx, cy, radius, startAngle, startAngle + slice);
      ctx.strokeStyle = color;
      ctx.lineWidth = thickness;
      ctx.lineCap = 'round';
      ctx.stroke();

      startAngle += slice;
    });

    // Center text
    ctx.fillStyle = '#000';
    ctx.font = 'bold 20px -apple-system, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(formatNumber(total), cx, cy);
    ctx.font = '11px -apple-system, sans-serif';
    ctx.fillStyle = '#86868b';
    ctx.fillText('tokens', cx, cy + 16);

    // Legend (XSS-safe via textContent)
    const legend = $('#donut-legend');
    if (!legend) return;
    legend.innerHTML = '';
    colors.forEach(({ key, color, value }) => {
      const span = document.createElement('span');
      span.className = 'legend-item';
      const dot = document.createElement('span');
      dot.className = 'legend-dot';
      dot.style.background = color;
      span.appendChild(dot);
      span.appendChild(document.createTextNode(key + ' (' + formatNumber(value) + ')'));
      legend.appendChild(span);
    });
  }

  // ─── Cost Trend Chart (Canvas 2D Line) ───
  function renderCostChart(trends) {
    const canvas = $('#cost-chart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;

    canvas.width = canvas.offsetWidth * dpr;
    canvas.height = canvas.offsetHeight * dpr;
    ctx.scale(dpr, dpr);

    const w = canvas.offsetWidth;
    const h = canvas.offsetHeight;
    const pad = { top: 10, right: 10, bottom: 30, left: 50 };
    const plotW = w - pad.left - pad.right;
    const plotH = h - pad.top - pad.bottom;

    ctx.clearRect(0, 0, w, h);

    if (!trends.length) {
      ctx.fillStyle = '#86868b';
      ctx.font = '14px -apple-system, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('No cost data yet', w / 2, h / 2);
      return;
    }

    const maxCost = Math.max(...trends.map((t) => t.cost), 0.001);

    // Grid lines
    ctx.strokeStyle = 'rgba(0,0,0,0.06)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const y = pad.top + plotH - (plotH * i) / 4;
      ctx.beginPath();
      ctx.moveTo(pad.left, y);
      ctx.lineTo(w - pad.right, y);
      ctx.stroke();

      ctx.fillStyle = '#86868b';
      ctx.font = '10px -apple-system, sans-serif';
      ctx.textAlign = 'right';
      ctx.fillText('$' + ((maxCost * i) / 4).toFixed(3), pad.left - 6, y + 3);
    }

    // Line
    ctx.beginPath();
    ctx.strokeStyle = '#000';
    ctx.lineWidth = 2;
    ctx.lineJoin = 'round';

    trends.forEach((t, i) => {
      const x = pad.left + (plotW * i) / (trends.length - 1 || 1);
      const y = pad.top + plotH - (plotH * t.cost) / maxCost;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Fill area
    const lastX = pad.left + plotW;
    ctx.lineTo(lastX, pad.top + plotH);
    ctx.lineTo(pad.left, pad.top + plotH);
    ctx.closePath();
    ctx.fillStyle = 'rgba(0,0,0,0.04)';
    ctx.fill();

    // X labels
    ctx.fillStyle = '#86868b';
    ctx.font = '10px -apple-system, sans-serif';
    ctx.textAlign = 'center';
    const step = Math.max(1, Math.floor(trends.length / 6));
    trends.forEach((t, i) => {
      if (i % step === 0 || i === trends.length - 1) {
        const x = pad.left + (plotW * i) / (trends.length - 1 || 1);
        const label = t.date ? t.date.slice(5) : '';
        ctx.fillText(label, x, h - 8);
      }
    });

    // Dots
    ctx.fillStyle = '#000';
    trends.forEach((t, i) => {
      const x = pad.left + (plotW * i) / (trends.length - 1 || 1);
      const y = pad.top + plotH - (plotH * t.cost) / maxCost;
      ctx.beginPath();
      ctx.arc(x, y, 3, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  // ─── Heatmap (XSS-safe via DOM API) ───
  function renderHeatmap(grid) {
    const container = $('#heatmap');
    if (!container) return;

    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

    // Ensure 7x24 grid
    while (grid.length < 7) grid.push(new Array(24).fill(0));
    grid.forEach((row) => {
      while (row.length < 24) row.push(0);
    });

    const maxVal = Math.max(1, ...grid.flat());
    const frag = document.createDocumentFragment();

    // Hour labels row
    const emptyLabel = document.createElement('span');
    emptyLabel.className = 'heatmap-label';
    frag.appendChild(emptyLabel);

    for (let h = 0; h < 24; h++) {
      const hourLabel = document.createElement('span');
      hourLabel.className = 'heatmap-hour-label';
      if (h % 3 === 0) hourLabel.textContent = h + 'h';
      frag.appendChild(hourLabel);
    }

    // Data rows
    days.forEach((day, d) => {
      const dayLabel = document.createElement('span');
      dayLabel.className = 'heatmap-label';
      dayLabel.textContent = day;
      frag.appendChild(dayLabel);

      for (let h = 0; h < 24; h++) {
        const val = (grid[d] && grid[d][h]) || 0;
        const level = val === 0 ? 0 : Math.min(5, Math.ceil((val / maxVal) * 5));
        const cell = document.createElement('span');
        cell.className = 'heatmap-cell level-' + level;
        cell.title = day + ' ' + h + ':00 \u2014 ' + val + ' requests';
        cell.setAttribute('role', 'gridcell');
        cell.setAttribute('aria-label', day + ' ' + h + ':00, ' + val + ' requests');
        frag.appendChild(cell);
      }
    });

    container.innerHTML = '';
    container.appendChild(frag);
  }

  // ─── Latency Bars ───
  function renderLatency(data) {
    const p50 = data.p50 || 0;
    const p95 = data.p95 || 0;
    const p99 = data.p99 || 0;
    const maxLat = Math.max(p99, p95, p50, 1);

    safeText('#lat-p50', p50 ? formatLatency(p50) : '\u2014');
    safeText('#lat-p95', p95 ? formatLatency(p95) : '\u2014');
    safeText('#lat-p99', p99 ? formatLatency(p99) : '\u2014');

    const maxH = 130;
    const barP50 = $('#bar-p50');
    const barP95 = $('#bar-p95');
    const barP99 = $('#bar-p99');
    if (barP50) barP50.style.height = Math.max(4, (p50 / maxLat) * maxH) + 'px';
    if (barP95) barP95.style.height = Math.max(4, (p95 / maxLat) * maxH) + 'px';
    if (barP99) barP99.style.height = Math.max(4, (p99 / maxLat) * maxH) + 'px';
  }

  // ─── SSE Connection with proper cleanup ───
  function connectSSE() {
    if (sseSource) {
      sseSource.close();
      sseSource = null;
    }

    const dot = $('#connection-dot');
    const text = $('#connection-text');
    if (!dot || !text) return;

    try {
      sseSource = new EventSource('/api/v2/stream');

      sseSource.addEventListener('connected', () => {
        dot.classList.add('connected');
        text.textContent = 'Connected (Live)';
      });

      sseSource.addEventListener('session_update', (e) => {
        try {
          const data = JSON.parse(e.data);
          const tokens = (data.input_tokens || 0) + (data.output_tokens || 0);
          showToast('New session: ' + data.model + ' | ' + formatNumber(tokens) + ' tokens | ' + (data.duration || 0).toFixed(1) + 'min');
          fetchDashboardData();
        } catch (_) { /* malformed event data */ }
      });

      sseSource.addEventListener('stats_updated', () => {
        showToast('Stats refreshed');
        fetchDashboardData();
      });

      sseSource.addEventListener('route_complete', (e) => {
        try {
          const data = JSON.parse(e.data);
          showToast('Route: ' + data.model + ' | ' + data.input_tokens + '+' + data.output_tokens + ' tokens');
          fetchDashboardData();
        } catch (_) { /* malformed event data */ }
      });

      sseSource.addEventListener('budget_alert', (e) => {
        try {
          const data = JSON.parse(e.data);
          addAlert(data.message, 'warning');
          showToast(data.message);
        } catch (_) { /* malformed event data */ }
      });

      sseSource.addEventListener('heartbeat', () => {
        // Keep-alive acknowledged
      });

      sseSource.onerror = () => {
        dot.classList.remove('connected');
        text.textContent = 'Reconnecting...';
        if (sseSource) {
          sseSource.close();
          sseSource = null;
        }
        setTimeout(connectSSE, 5000);
      };
    } catch (_) {
      dot.classList.remove('connected');
      text.textContent = 'SSE not available';
    }
  }

  // ─── Alerts ───
  function addAlert(message, level) {
    level = level || 'info';
    alerts.unshift({ message: String(message), level, time: new Date() });
    if (alerts.length > 20) alerts.pop();
    renderAlerts();
  }

  function renderAlerts() {
    const container = $('#alerts-list');
    if (!container) return;

    if (!alerts.length) {
      container.innerHTML = '';
      const item = document.createElement('div');
      item.className = 'alert-item';
      const dot = document.createElement('span');
      dot.className = 'alert-dot info';
      item.appendChild(dot);
      const msg = document.createElement('span');
      msg.textContent = 'No alerts yet.';
      item.appendChild(msg);
      container.appendChild(item);
      return;
    }

    container.innerHTML = '';
    const frag = document.createDocumentFragment();
    alerts.slice(0, 10).forEach((a) => {
      const item = document.createElement('div');
      item.className = 'alert-item';
      const dot = document.createElement('span');
      dot.className = 'alert-dot ' + a.level;
      item.appendChild(dot);
      const msg = document.createElement('span');
      msg.textContent = a.message;
      item.appendChild(msg);
      const timeEl = document.createElement('span');
      timeEl.className = 'alert-time';
      timeEl.textContent = formatTime(a.time);
      item.appendChild(timeEl);
      frag.appendChild(item);
    });
    container.appendChild(frag);
  }

  // ─── Toast (max 5 to prevent unbounded stack) ───
  function showToast(message) {
    const container = $('#toast-container');
    if (!container) return;

    // Evict oldest if at capacity
    while (container.children.length >= MAX_TOASTS) {
      container.removeChild(container.firstChild);
    }

    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('removing');
      setTimeout(() => { if (toast.parentNode) toast.remove(); }, 300);
    }, 4000);
  }

  // ─── Helpers ───
  function safeText(selector, text) {
    const el = $(selector);
    if (el) el.textContent = text;
  }

  function formatNumber(n) {
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
    if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K';
    return String(n);
  }

  function formatLatency(ms) {
    if (ms >= 60000) return (ms / 60000).toFixed(1) + 'm';
    if (ms >= 1000) return (ms / 1000).toFixed(1) + 's';
    return ms + 'ms';
  }

  function formatTime(date) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function getModelColor(key) {
    const k = String(key).toLowerCase();
    for (const [prefix, color] of Object.entries(MODEL_COLORS)) {
      if (k.includes(prefix)) return color;
    }
    let hash = 0;
    for (let i = 0; i < k.length; i++) hash = k.charCodeAt(i) + ((hash << 5) - hash);
    return 'hsl(' + (Math.abs(hash) % 360) + ', 50%, 50%)';
  }
})();
