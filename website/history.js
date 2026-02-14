(function () {
  "use strict";

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

  let allEntries = [];
  let filtered = [];
  const PAGE_SIZE = 20;
  let currentPage = 0;

  async function loadData() {
    try {
      const res = await fetch("/api/history");
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      allEntries = (data.entries || []).reverse();
      applyFilters();
    } catch (e) {
      document.getElementById("history-list").innerHTML =
        '<div class="empty-state"><h3>Failed to load</h3><p>' + e.message + "</p></div>";
    }
  }

  function applyFilters() {
    const routeFilter = document.getElementById("filter-route").value;
    const search = document.getElementById("filter-search").value.toLowerCase().trim();

    filtered = allEntries.filter((entry) => {
      if (routeFilter !== "all") {
        const route = entry.route || (entry.tasks && entry.tasks[0] ? entry.tasks[0].route : "");
        if (route !== routeFilter) return false;
      }
      if (search) {
        const text = JSON.stringify(entry).toLowerCase();
        if (!text.includes(search)) return false;
      }
      return true;
    });

    currentPage = 0;
    renderSummary();
    renderList();
    renderPagination();
  }

  function renderSummary() {
    let claude = 0, groq = 0, split = 0;
    filtered.forEach((e) => {
      const tasks = e.tasks || [{ route: e.route }];
      tasks.forEach((t) => {
        const r = t.route || e.route || "";
        if (r === "claude") claude++;
        else if (r === "cheap_llm") groq++;
        else if (r === "split") split++;
      });
    });
    document.getElementById("sum-total").textContent = filtered.length;
    document.getElementById("sum-claude").textContent = claude;
    document.getElementById("sum-groq").textContent = groq;
    document.getElementById("sum-split").textContent = split;
  }

  function renderList() {
    const container = document.getElementById("history-list");
    const start = currentPage * PAGE_SIZE;
    const page = filtered.slice(start, start + PAGE_SIZE);

    if (!page.length) {
      container.innerHTML = '<div class="empty-state"><h3>No results</h3><p>Try adjusting your filters.</p></div>';
      return;
    }

    container.innerHTML = "";
    page.forEach((entry, i) => {
      const card = document.createElement("div");
      card.className = "history-card";

      const tasks = entry.tasks || [{ id: "A", route: entry.route || "unknown", summary: entry.request || "" }];
      const route = entry.route || tasks[0].route || "unknown";
      const ts = entry.timestamp ? new Date(entry.timestamp).toLocaleString() : "N/A";
      const request = entry.request || tasks.map((t) => t.summary || "").join(", ") || "(no request)";

      let tasksHTML = "";
      tasks.forEach((t) => {
        const r = t.route || route;
        tasksHTML += '<span class="task-chip ' + r + '">' + (t.id || "?") + ": " + r + "</span>";
      });

      card.innerHTML =
        '<div class="history-card-header">' +
        "<h4>#" + (allEntries.length - (start + i)) + " &mdash; " + route + "</h4>" +
        '<span class="history-time">' + ts + "</span>" +
        "</div>" +
        '<div class="history-card-body">' +
        "<p>" + escapeHtml(request.substring(0, 200)) + (request.length > 200 ? "..." : "") + "</p>" +
        '<div class="history-tasks">' + tasksHTML + "</div>" +
        "</div>" +
        '<div class="history-detail">' + escapeHtml(JSON.stringify(entry, null, 2)) + "</div>";

      card.addEventListener("click", () => card.classList.toggle("expanded"));
      container.appendChild(card);
    });
  }

  function renderPagination() {
    const container = document.getElementById("pagination");
    const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
    if (totalPages <= 1) { container.innerHTML = ""; return; }

    container.innerHTML = "";
    for (let i = 0; i < totalPages; i++) {
      const btn = document.createElement("button");
      btn.className = "btn btn-sm" + (i === currentPage ? " btn-primary" : "");
      btn.textContent = i + 1;
      btn.addEventListener("click", () => {
        currentPage = i;
        renderList();
        renderPagination();
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
      container.appendChild(btn);
    }
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function debounce(fn, ms) {
    let timer;
    return function () {
      var args = arguments;
      var ctx = this;
      clearTimeout(timer);
      timer = setTimeout(function () { fn.apply(ctx, args); }, ms);
    };
  }

  document.getElementById("filter-route").addEventListener("change", applyFilters);
  document.getElementById("filter-search").addEventListener("input", debounce(applyFilters, 300));
  document.getElementById("btn-refresh").addEventListener("click", () => { loadData(); showToast("Refreshed"); });

  loadData();
})();
