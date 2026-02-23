(function () {
  "use strict";

  // Mobile menu
  const navToggle = document.getElementById("nav-toggle");
  const mobileMenu = document.getElementById("mobile-menu");
  if (navToggle && mobileMenu) {
    navToggle.addEventListener("click", () => {
      navToggle.classList.toggle("open");
      mobileMenu.classList.toggle("open");
      document.body.style.overflow = mobileMenu.classList.contains("open") ? "hidden" : "";
    });
    mobileMenu.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        navToggle.classList.remove("open");
        mobileMenu.classList.remove("open");
        document.body.style.overflow = "";
      });
    });
  }

  const toast = document.getElementById("toast");
  let toastTimer = null;
  function showToast(msg, dur) {
    dur = dur || 2000;
    toast.textContent = msg;
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("show"), dur);
  }

  // Token cost estimates (per 1K tokens)
  const COST_PER_1K = { claude: 0.015, cheap_llm: 0.0005, split: 0.008 };
  const TOKENS_PER_TASK = { claude: 2000, cheap_llm: 500, split: 1200 };

  let historyData = [];

  async function loadData() {
    try {
      if (window.supabaseData) {
        var rows = await window.supabaseData.history.list();
        historyData = rows.map(function (r) {
          return {
            id: r.id,
            request: r.request,
            route: r.route,
            tasks: r.tasks || [],
            output: r.output,
            timestamp: r.created_at,
          };
        });
      } else {
        var res = await fetch("/api/history");
        if (!res.ok) throw new Error("HTTP " + res.status);
        var data = await res.json();
        historyData = data.entries || [];
      }
      render();
    } catch (e) {
      showToast("Failed to load data: " + e.message, 3000);
    }
  }

  function render() {
    renderStats();
    renderChart();
    renderTable();
  }

  function renderStats() {
    const total = historyData.length;
    let tokens = 0, cost = 0, confSum = 0, confCount = 0;

    historyData.forEach((e) => {
      const tasks = e.tasks || [];
      tasks.forEach((t) => {
        const r = t.route || "claude";
        const tk = TOKENS_PER_TASK[r] || 1000;
        tokens += tk;
        cost += (tk / 1000) * (COST_PER_1K[r] || 0.01);
        if (t.confidence) { confSum += t.confidence; confCount++; }
      });
      if (!tasks.length) {
        const r = e.route || "claude";
        const tk = TOKENS_PER_TASK[r] || 1000;
        tokens += tk;
        cost += (tk / 1000) * (COST_PER_1K[r] || 0.01);
      }
    });

    document.getElementById("total-tasks").textContent = total;
    document.getElementById("total-tokens").textContent = tokens > 1000 ? (tokens / 1000).toFixed(1) + "K" : tokens;
    document.getElementById("total-cost").textContent = "$" + cost.toFixed(2);
    document.getElementById("avg-confidence").textContent = confCount ? Math.round((confSum / confCount) * 100) + "%" : "N/A";
  }

  function renderChart() {
    const chart = document.getElementById("bar-chart");
    const recent = historyData.slice(-30);

    if (!recent.length) {
      chart.innerHTML = '<div style="flex:1;text-align:center;color:var(--gray);align-self:center;">No data</div>';
      return;
    }

    chart.innerHTML = "";
    const maxTasks = Math.max(...recent.map((e) => (e.tasks || [{}]).length), 1);

    recent.forEach((entry, i) => {
      const tasks = entry.tasks || [{ route: entry.route || "claude" }];
      let claude = 0, groq = 0;
      tasks.forEach((t) => {
        if (t.route === "cheap_llm") groq++;
        else claude++;
      });

      const group = document.createElement("div");
      group.className = "bar-group";

      const cBar = document.createElement("div");
      cBar.className = "bar claude";
      cBar.style.height = Math.max((claude / maxTasks) * 100, claude ? 8 : 0) + "%";
      cBar.title = "Claude: " + claude;

      const gBar = document.createElement("div");
      gBar.className = "bar groq";
      gBar.style.height = Math.max((groq / maxTasks) * 100, groq ? 8 : 0) + "%";
      gBar.title = "Groq: " + groq;

      const label = document.createElement("div");
      label.className = "bar-label";
      label.textContent = "#" + (i + 1);

      group.appendChild(cBar);
      group.appendChild(gBar);
      group.appendChild(label);
      chart.appendChild(group);
    });
  }

  function renderTable() {
    const container = document.getElementById("table-container");
    if (!historyData.length) {
      container.innerHTML = '<div class="empty-state"><h3>No routing data yet</h3><p>Run some tasks through the Task Splitter to see cost data here.</p></div>';
      return;
    }

    const recent = historyData.slice(-50).reverse();
    let html = '<table class="cost-table"><thead><tr><th>Session</th><th>Route</th><th>Tasks</th><th>Est. Tokens</th><th>Est. Cost</th><th>Time</th></tr></thead><tbody>';

    recent.forEach((entry, i) => {
      const tasks = entry.tasks || [{ route: entry.route || "claude" }];
      const route = entry.route || tasks[0].route || "claude";
      let tokens = 0, cost = 0;
      tasks.forEach((t) => {
        const r = t.route || route;
        const tk = TOKENS_PER_TASK[r] || 1000;
        tokens += tk;
        cost += (tk / 1000) * (COST_PER_1K[r] || 0.01);
      });

      const ts = entry.timestamp ? new Date(entry.timestamp).toLocaleString() : "N/A";

      html += "<tr>";
      html += "<td>#" + (historyData.length - i) + "</td>";
      html += '<td><span class="route-badge ' + route + '">' + route + "</span></td>";
      html += "<td>" + tasks.length + "</td>";
      html += "<td>" + tokens.toLocaleString() + "</td>";
      html += "<td>$" + cost.toFixed(4) + "</td>";
      html += "<td>" + ts + "</td>";
      html += "</tr>";
    });

    html += "</tbody></table>";
    container.innerHTML = html;
  }

  function exportCSV() {
    if (!historyData.length) { showToast("No data to export"); return; }

    let csv = "Session,Route,Tasks,Est_Tokens,Est_Cost,Timestamp\n";
    historyData.forEach((entry, i) => {
      const tasks = entry.tasks || [{ route: entry.route || "claude" }];
      const route = entry.route || "claude";
      let tokens = 0, cost = 0;
      tasks.forEach((t) => {
        const r = t.route || route;
        const tk = TOKENS_PER_TASK[r] || 1000;
        tokens += tk;
        cost += (tk / 1000) * (COST_PER_1K[r] || 0.01);
      });
      const ts = entry.timestamp || "";
      csv += (i + 1) + "," + route + "," + tasks.length + "," + tokens + "," + cost.toFixed(4) + "," + ts + "\n";
    });

    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "cost_tracker_export.csv";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast("CSV exported!");
  }

  document.getElementById("btn-refresh").addEventListener("click", () => { loadData(); showToast("Refreshed"); });
  document.getElementById("btn-export").addEventListener("click", exportCSV);

  loadData();
})();
