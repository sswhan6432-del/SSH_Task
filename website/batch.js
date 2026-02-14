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

  let batchResults = [];
  let selectedRouter = "";

  async function getRouter() {
    try {
      const res = await fetch("/api/routers");
      const data = await res.json();
      const routers = data.routers || [];
      selectedRouter = routers.length ? routers[0].path : "";
    } catch (e) {
      showToast("Failed to load routers", 3000);
    }
  }

  async function runBatch() {
    const textarea = document.getElementById("batch-textarea");
    const lines = textarea.value.split("\n").map((l) => l.trim()).filter((l) => l.length > 0);

    if (!lines.length) { showToast("Enter at least one task"); return; }
    if (lines.length > 50) {
      showToast("Maximum 50 tasks allowed. Truncating.", 3000);
      lines.length = 50;
    }
    if (!selectedRouter) {
      await getRouter();
      if (!selectedRouter) { showToast("No router available"); return; }
    }

    batchResults = [];
    const progressContainer = document.getElementById("progress-container");
    const progressFill = document.getElementById("progress-fill");
    const progressText = document.getElementById("progress-text");
    const resultsSection = document.getElementById("results-section");

    progressContainer.style.display = "block";
    resultsSection.style.display = "none";
    progressFill.style.width = "0%";
    progressText.textContent = "0 / " + lines.length + " tasks processed";

    for (let i = 0; i < lines.length; i++) {
      const task = lines[i];
      let result = { task: task, route: "error", tickets: 0, output: "", error: "" };

      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000);
        const res = await fetch("/api/route", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            router: selectedRouter,
            request: task,
            friendly: true,
            force_split: true,
            translate_en: false,
            economy: "strict",
            phase: "implement",
          }),
          signal: controller.signal,
        });
        clearTimeout(timeoutId);
        if (!res.ok) {
          result.error = "HTTP " + res.status;
        } else {
          const data = await res.json();
          if (data.error) {
            result.error = data.error;
          } else {
            result.output = data.output || "";
            result.tickets = (data.tickets || []).length;
            const routeMatch = result.output.match(/Route:\s*(claude|cheap_llm|split)/i);
            result.route = routeMatch ? routeMatch[1].toLowerCase() : "claude";
          }
        }
      } catch (e) {
        result.error = e.message;
      }

      batchResults.push(result);
      const pct = Math.round(((i + 1) / lines.length) * 100);
      progressFill.style.width = pct + "%";
      progressText.textContent = (i + 1) + " / " + lines.length + " tasks processed";
    }

    progressContainer.style.display = "none";
    renderResults();
    showToast("Batch complete! " + lines.length + " tasks processed");
  }

  function renderResults() {
    const section = document.getElementById("results-section");
    const summary = document.getElementById("results-summary");
    const container = document.getElementById("results-table-container");

    let claude = 0, groq = 0, split = 0, errors = 0;
    batchResults.forEach((r) => {
      if (r.error) errors++;
      else if (r.route === "claude") claude++;
      else if (r.route === "cheap_llm") groq++;
      else if (r.route === "split") split++;
    });

    summary.innerHTML =
      "Total: <strong>" + batchResults.length + "</strong> | " +
      "Claude: <strong>" + claude + "</strong> | " +
      "Groq: <strong>" + groq + "</strong> | " +
      "Split: <strong>" + split + "</strong>" +
      (errors ? " | Errors: <strong>" + errors + "</strong>" : "");

    let html = '<table class="result-table"><thead><tr>' +
      "<th>#</th><th>Task</th><th>Route</th><th>Tickets</th><th>Status</th>" +
      "</tr></thead><tbody>";

    batchResults.forEach((r, i) => {
      const routeClass = r.error ? "error" : r.route;
      const statusClass = r.error ? "error" : "done";
      const statusText = r.error ? "ERR" : "OK";

      html += '<tr class="batch-row" data-idx="' + i + '">';
      html += "<td>" + (i + 1) + "</td>";
      html += "<td>" + escapeHtml(r.task.substring(0, 80)) + (r.task.length > 80 ? "..." : "") + "</td>";
      html += '<td><span class="route-badge ' + routeClass + '">' + (r.error ? "error" : r.route) + "</span></td>";
      html += "<td>" + (r.error ? "-" : r.tickets) + "</td>";
      html += '<td><span class="status-icon ' + statusClass + '">' + statusText + "</span></td>";
      html += "</tr>";
      html += '<tr><td colspan="5"><div class="task-detail-output" id="detail-' + i + '">' +
        escapeHtml(r.error || r.output || "(no output)") + "</div></td></tr>";
    });

    html += "</tbody></table>";
    container.innerHTML = html;

    // Toggle detail rows
    container.querySelectorAll(".batch-row").forEach((row) => {
      row.addEventListener("click", () => {
        const idx = row.dataset.idx;
        const detail = document.getElementById("detail-" + idx);
        detail.style.display = detail.style.display === "block" ? "none" : "block";
      });
    });

    section.style.display = "block";
  }

  function exportResults() {
    if (!batchResults.length) { showToast("No results to export"); return; }
    let csv = "Index,Task,Route,Tickets,Status\n";
    batchResults.forEach((r, i) => {
      csv += (i + 1) + ',"' + r.task.replace(/"/g, '""') + '",' +
        (r.error ? "error" : r.route) + "," +
        (r.error ? 0 : r.tickets) + "," +
        (r.error ? "error" : "ok") + "\n";
    });
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "batch_results.csv";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast("Results exported!");
  }

  function copyAllOutputs() {
    if (!batchResults.length) { showToast("No results to copy"); return; }
    const text = batchResults.map((r, i) =>
      "--- Task " + (i + 1) + " ---\n" + r.task + "\n\n" + (r.error || r.output || "(no output)")
    ).join("\n\n");
    navigator.clipboard.writeText(text).then(() => showToast("All outputs copied!"))
      .catch((e) => showToast("Copy failed: " + e.message));
  }

  function loadSample() {
    document.getElementById("batch-textarea").value =
      "Build a login page with email validation\n" +
      "Add dark mode toggle to the settings page\n" +
      "Fix the navigation menu on mobile\n" +
      "Create a contact form with SMTP integration\n" +
      "Optimize database queries for user dashboard";
    showToast("Sample loaded");
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  document.getElementById("btn-run-batch").addEventListener("click", runBatch);
  document.getElementById("btn-clear").addEventListener("click", () => {
    document.getElementById("batch-textarea").value = "";
    document.getElementById("results-section").style.display = "none";
    batchResults = [];
  });
  document.getElementById("btn-load-sample").addEventListener("click", loadSample);
  document.getElementById("btn-export").addEventListener("click", exportResults);
  document.getElementById("btn-copy-all").addEventListener("click", copyAllOutputs);

  getRouter();
})();
