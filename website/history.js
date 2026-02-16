(function () {
  "use strict";

  // --- Mobile menu ---
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

  // --- Toast ---
  const toast = document.getElementById("toast");
  let toastTimer = null;
  function showToast(msg, dur) {
    dur = dur || 2000;
    toast.textContent = msg;
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("show"), dur);
  }

  // --- State ---
  let allEntries = [];
  let filtered = [];
  const PAGE_SIZE = 20;
  let currentPage = 0;

  // --- Trash icon SVG ---
  const TRASH_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
    '<polyline points="3 6 5 6 21 6"/>' +
    '<path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>' +
    '<line x1="10" y1="11" x2="10" y2="17"/>' +
    '<line x1="14" y1="11" x2="14" y2="17"/>' +
    '</svg>';

  // --- Load data ---
  async function loadData() {
    try {
      const res = await fetch("/api/history");
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      allEntries = (data.entries || []).reverse();
      applyFilters();
    } catch (e) {
      document.getElementById("history-list").innerHTML =
        '<div class="empty-state">' +
          '<div class="empty-state-icon">' +
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' +
              '<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>' +
            '</svg>' +
          '</div>' +
          '<h3>Failed to load</h3><p>' + escapeHtml(e.message) + '</p>' +
        '</div>';
    }
  }

  // --- Filters ---
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

  // --- Summary ---
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

  // --- Render list ---
  function renderList() {
    const container = document.getElementById("history-list");
    const start = currentPage * PAGE_SIZE;
    const page = filtered.slice(start, start + PAGE_SIZE);

    if (!page.length) {
      container.innerHTML =
        '<div class="empty-state">' +
          '<div class="empty-state-icon">' +
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' +
              '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>' +
            '</svg>' +
          '</div>' +
          '<h3>No results</h3><p>Try adjusting your filters.</p>' +
        '</div>';
      return;
    }

    container.innerHTML = "";
    page.forEach((entry, i) => {
      const card = document.createElement("div");
      card.className = "history-card";

      // Entrance animation
      card.style.opacity = "0";
      card.style.transform = "translateY(10px)";

      const tasks = entry.tasks || [{ id: "A", route: entry.route || "unknown", summary: entry.request || "" }];
      const route = entry.route || tasks[0].route || "unknown";
      const ts = entry.timestamp ? formatTime(entry.timestamp) : "N/A";
      const request = entry.request || tasks.map((t) => t.summary || "").join(", ") || "(no request)";
      const entryNum = allEntries.length - (start + i);

      // The original index in the non-reversed array (for delete API)
      const originalIndex = allEntries.length - 1 - (start + i);

      let tasksHTML = "";
      tasks.forEach((t) => {
        const r = t.route || route;
        tasksHTML += '<span class="task-chip ' + r + '">' + (t.id || "?") + ": " + r + "</span>";
      });

      card.innerHTML =
        '<div class="history-card-inner">' +
          '<div class="history-card-header">' +
            '<div class="history-card-header-left">' +
              '<span class="history-num">#' + entryNum + '</span>' +
              '<h4>' + escapeHtml(route) + '</h4>' +
            '</div>' +
            '<div class="history-card-header-right">' +
              '<span class="history-time">' + ts + '</span>' +
              '<button class="history-delete-btn" data-idx="' + originalIndex + '" type="button" title="Delete this entry">' + TRASH_SVG + '</button>' +
            '</div>' +
          '</div>' +
          '<div class="history-card-body">' +
            '<p>' + escapeHtml(request.substring(0, 200)) + (request.length > 200 ? "..." : "") + '</p>' +
            '<div class="history-tasks">' + tasksHTML + '</div>' +
          '</div>' +
        '</div>' +
        '<div class="history-detail">' +
          '<div class="history-detail-inner">' +
            '<pre>' + escapeHtml(JSON.stringify(entry, null, 2)) + '</pre>' +
          '</div>' +
        '</div>';

      // Click to expand (but not when clicking delete button)
      card.querySelector(".history-card-inner").addEventListener("click", function (e) {
        if (e.target.closest(".history-delete-btn")) return;
        card.classList.toggle("expanded");
      });

      // Delete single entry
      card.querySelector(".history-delete-btn").addEventListener("click", function (e) {
        e.stopPropagation();
        deleteEntry(card, parseInt(this.getAttribute("data-idx"), 10));
      });

      container.appendChild(card);

      // Staggered entrance animation
      setTimeout(function () {
        card.style.transition = "opacity 0.5s var(--ease-out-quart), transform 0.5s var(--ease-out-quart)";
        card.style.opacity = "1";
        card.style.transform = "translateY(0)";
      }, i * 40);
    });
  }

  // --- Delete single entry ---
  async function deleteEntry(cardEl, originalIndex) {
    // Set initial height for collapse animation
    cardEl.style.maxHeight = cardEl.offsetHeight + "px";
    cardEl.style.overflow = "hidden";

    // Force reflow
    cardEl.offsetHeight;

    // Apply removing animation
    cardEl.classList.add("removing");

    try {
      const res = await fetch("/api/history/" + originalIndex, { method: "DELETE" });
      if (!res.ok) throw new Error("HTTP " + res.status);

      // Wait for animation to finish, then reload data
      setTimeout(function () {
        loadData();
        showToast("Entry deleted");
      }, 450);
    } catch (e) {
      // Revert animation on error
      cardEl.classList.remove("removing");
      cardEl.style.maxHeight = "";
      cardEl.style.overflow = "";
      showToast("Delete failed: " + e.message, 3000);
    }
  }

  // --- Delete all ---
  const confirmOverlay = document.getElementById("confirm-overlay");
  const btnDeleteAll = document.getElementById("btn-delete-all");
  const confirmCancel = document.getElementById("confirm-cancel");
  const confirmDelete = document.getElementById("confirm-delete");

  btnDeleteAll.addEventListener("click", function () {
    if (allEntries.length === 0) {
      showToast("No entries to delete");
      return;
    }
    confirmOverlay.classList.add("show");
  });

  confirmCancel.addEventListener("click", function () {
    confirmOverlay.classList.remove("show");
  });

  confirmOverlay.addEventListener("click", function (e) {
    if (e.target === confirmOverlay) {
      confirmOverlay.classList.remove("show");
    }
  });

  confirmDelete.addEventListener("click", async function () {
    confirmOverlay.classList.remove("show");

    // Animate all cards out
    var cards = document.querySelectorAll(".history-card");
    cards.forEach(function (card, i) {
      card.style.maxHeight = card.offsetHeight + "px";
      card.style.overflow = "hidden";
      setTimeout(function () {
        card.classList.add("removing");
      }, i * 30);
    });

    try {
      const res = await fetch("/api/history", { method: "DELETE" });
      if (!res.ok) throw new Error("HTTP " + res.status);

      setTimeout(function () {
        allEntries = [];
        filtered = [];
        renderSummary();
        renderList();
        renderPagination();
        showToast("All history deleted");
      }, cards.length * 30 + 400);
    } catch (e) {
      loadData();
      showToast("Delete failed: " + e.message, 3000);
    }
  });

  // --- Pagination ---
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

  // --- Helpers ---
  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function formatTime(ts) {
    try {
      const d = new Date(ts);
      var month = d.getMonth() + 1;
      var day = d.getDate();
      var hours = d.getHours();
      var minutes = d.getMinutes();
      return month + "/" + day + " " + (hours < 10 ? "0" : "") + hours + ":" + (minutes < 10 ? "0" : "") + minutes;
    } catch (e) {
      return ts;
    }
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

  // --- Event listeners ---
  document.getElementById("filter-route").addEventListener("change", applyFilters);
  document.getElementById("filter-search").addEventListener("input", debounce(applyFilters, 300));
  document.getElementById("btn-refresh").addEventListener("click", () => { loadData(); showToast("Refreshed"); });

  // --- Init ---
  loadData();
})();
