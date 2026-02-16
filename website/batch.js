(function () {
  "use strict";

  // =============================================
  // DOM Refs
  // =============================================
  const textarea = document.getElementById("batch-textarea");
  const taskCountEl = document.getElementById("task-count");
  const batchInputArea = document.getElementById("batch-input-area");
  const toast = document.getElementById("toast");

  // Controls
  const concurrencySlider = document.getElementById("concurrency-slider");
  const concurrencyValue = document.getElementById("concurrency-value");
  const modeSelect = document.getElementById("mode-select");
  const autoRetryCheckbox = document.getElementById("auto-retry");
  const economySelect = document.getElementById("economy-select");

  // Buttons
  const btnRun = document.getElementById("btn-run-batch");
  const btnPause = document.getElementById("btn-pause");
  const btnCancel = document.getElementById("btn-cancel");
  const btnClear = document.getElementById("btn-clear");
  const btnSample = document.getElementById("btn-load-sample");
  const btnImport = document.getElementById("btn-import-file");
  const fileInput = document.getElementById("file-input");
  const btnRetryfailed = document.getElementById("btn-retry-failed");
  const btnSendSplitter = document.getElementById("btn-send-splitter");
  const btnSaveHistory = document.getElementById("btn-save-history");
  const btnExportCsv = document.getElementById("btn-export-csv");
  const btnExportJson = document.getElementById("btn-export-json");
  const btnCopyAll = document.getElementById("btn-copy-all");

  // Progress
  const progressSection = document.getElementById("progress-section");
  const progressFill = document.getElementById("progress-fill");
  const progressText = document.getElementById("progress-text");
  const progressTitle = document.getElementById("progress-title");
  const progressEta = document.getElementById("progress-eta");
  const progressTasks = document.getElementById("progress-tasks");

  // Results
  const resultsSection = document.getElementById("results-section");
  const summaryCards = document.getElementById("summary-cards");
  const routeChart = document.getElementById("route-chart");
  const routeLegend = document.getElementById("route-legend");
  const filterTabs = document.getElementById("filter-tabs");
  const tableContainer = document.getElementById("results-table-container");

  // History
  const historyList = document.getElementById("history-list");

  // =============================================
  // State
  // =============================================
  let batchResults = [];
  let selectedRouter = "";
  let isRunning = false;
  let isPaused = false;
  let isCancelled = false;
  let activeFilter = "all";
  let sortColumn = null;
  let sortAsc = true;
  let batchStartTime = 0;
  let completedCount = 0;

  // =============================================
  // Mobile menu
  // =============================================
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

  // =============================================
  // Utilities
  // =============================================
  let toastTimer = null;
  function showToast(msg, dur) {
    dur = dur || 2000;
    toast.textContent = msg;
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("show"), dur);
  }

  function escapeHtml(str) {
    var div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function getTaskLines() {
    return textarea.value
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => l.length > 0);
  }

  function updateTaskCount() {
    var count = getTaskLines().length;
    taskCountEl.innerHTML = "<strong>" + count + "</strong> task" + (count !== 1 ? "s" : "");
  }

  // =============================================
  // Concurrency slider
  // =============================================
  concurrencySlider.addEventListener("input", () => {
    concurrencyValue.textContent = concurrencySlider.value;
  });

  // =============================================
  // Task count live update
  // =============================================
  textarea.addEventListener("input", updateTaskCount);
  updateTaskCount();

  // =============================================
  // File import / drag-and-drop
  // =============================================
  btnImport.addEventListener("click", () => fileInput.click());

  fileInput.addEventListener("change", (e) => {
    var file = e.target.files[0];
    if (!file) return;
    readFile(file);
    fileInput.value = "";
  });

  function readFile(file) {
    var reader = new FileReader();
    reader.onload = function (ev) {
      var text = ev.target.result;
      // CSV: try to extract first column if comma-separated
      if (file.name.endsWith(".csv")) {
        var lines = text.split("\n").map(function (l) {
          var parts = l.split(",");
          return parts[0].replace(/^["']|["']$/g, "").trim();
        }).filter(function (l) { return l.length > 0; });
        // Skip header if it looks like one
        if (lines.length > 1 && /^(task|title|name|description|item)/i.test(lines[0])) {
          lines.shift();
        }
        textarea.value = lines.join("\n");
      } else {
        textarea.value = text.trim();
      }
      updateTaskCount();
      showToast("Imported " + getTaskLines().length + " tasks from " + file.name);
    };
    reader.readAsText(file);
  }

  // Drag and drop
  batchInputArea.addEventListener("dragover", function (e) {
    e.preventDefault();
    batchInputArea.classList.add("drag-over");
  });
  batchInputArea.addEventListener("dragleave", function () {
    batchInputArea.classList.remove("drag-over");
  });
  batchInputArea.addEventListener("drop", function (e) {
    e.preventDefault();
    batchInputArea.classList.remove("drag-over");
    var file = e.dataTransfer.files[0];
    if (file && (file.name.endsWith(".txt") || file.name.endsWith(".csv"))) {
      readFile(file);
    } else {
      showToast("Please drop a .txt or .csv file");
    }
  });

  // =============================================
  // Load router
  // =============================================
  async function getRouter() {
    try {
      var res = await fetch("/api/routers");
      var data = await res.json();
      var routers = data.routers || [];
      selectedRouter = routers.length ? routers[0].path : "";
    } catch (e) {
      showToast("Failed to load routers", 3000);
    }
  }

  // =============================================
  // Parallel batch execution
  // =============================================
  async function processTask(task, index) {
    var mode = modeSelect.value;
    var economy = economySelect.value;
    var isV5 = mode === "v5";

    var body = {
      router: selectedRouter,
      request: task,
      friendly: true,
      force_split: true,
      translate_en: false,
      economy: economy,
      phase: "implement",
      v5_enabled: isV5,
      compress: isV5,
      compression_level: 2,
      show_stats: isV5,
    };

    var result = { task: task, route: "error", tickets: 0, output: "", error: "", index: index, duration: 0 };
    var start = Date.now();

    try {
      var controller = new AbortController();
      var timeoutId = setTimeout(function () { controller.abort(); }, 60000);

      var res = await fetch("/api/route", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (!res.ok) {
        result.error = "HTTP " + res.status;
      } else {
        var data = await res.json();
        if (data.error) {
          result.error = data.error;
        } else {
          result.output = data.output || "";
          result.tickets = (data.tickets || []).length;
          var routeMatch = result.output.match(/Route:\s*(claude|cheap_llm|split)/i);
          result.route = routeMatch ? routeMatch[1].toLowerCase() : "claude";
        }
      }
    } catch (e) {
      result.error = e.name === "AbortError" ? "Timeout (60s)" : e.message;
    }

    result.duration = Date.now() - start;
    return result;
  }

  async function runBatch() {
    var lines = getTaskLines();

    if (!lines.length) {
      showToast("Enter at least one task");
      return;
    }
    if (lines.length > 50) {
      showToast("Max 50 tasks. Truncating.", 3000);
      lines = lines.slice(0, 50);
    }
    if (!selectedRouter) {
      await getRouter();
      if (!selectedRouter) {
        showToast("No router available");
        return;
      }
    }

    // Reset state
    batchResults = [];
    isRunning = true;
    isPaused = false;
    isCancelled = false;
    completedCount = 0;
    batchStartTime = Date.now();
    activeFilter = "all";
    sortColumn = null;

    // UI: show progress, hide results
    progressSection.style.display = "block";
    resultsSection.style.display = "none";
    btnRun.style.display = "none";
    btnPause.style.display = "inline-flex";
    btnCancel.style.display = "inline-flex";
    progressFill.style.width = "0%";
    progressTitle.textContent = "Processing...";
    progressEta.textContent = "";
    progressText.textContent = "0 / " + lines.length;

    // Build progress pips
    progressTasks.innerHTML = "";
    for (var i = 0; i < lines.length; i++) {
      var pip = document.createElement("div");
      pip.className = "progress-pip";
      pip.id = "pip-" + i;
      pip.title = "Task " + (i + 1) + ": " + lines[i].substring(0, 40);
      progressTasks.appendChild(pip);
    }

    // Pre-fill results array with placeholders
    for (var j = 0; j < lines.length; j++) {
      batchResults.push(null);
    }

    var concurrency = parseInt(concurrencySlider.value, 10) || 3;
    var queue = lines.map(function (task, idx) { return { task: task, index: idx }; });
    var active = 0;
    var queueIdx = 0;

    await new Promise(function (resolve) {
      function next() {
        // Check cancel
        if (isCancelled) {
          if (active === 0) resolve();
          return;
        }

        // Check pause
        if (isPaused) {
          setTimeout(next, 200);
          return;
        }

        // Launch tasks up to concurrency
        while (active < concurrency && queueIdx < queue.length) {
          var item = queue[queueIdx];
          queueIdx++;
          active++;

          // Mark pip as running
          var pip = document.getElementById("pip-" + item.index);
          if (pip) pip.className = "progress-pip running";

          (function (taskItem) {
            processTask(taskItem.task, taskItem.index).then(function (result) {
              active--;
              batchResults[taskItem.index] = result;
              completedCount++;

              // Update pip
              var p = document.getElementById("pip-" + taskItem.index);
              if (p) p.className = "progress-pip " + (result.error ? "error" : "done");

              // Update progress
              var pct = Math.round((completedCount / lines.length) * 100);
              progressFill.style.width = pct + "%";
              progressText.textContent = completedCount + " / " + lines.length;

              // ETA
              var elapsed = Date.now() - batchStartTime;
              if (completedCount > 0 && completedCount < lines.length) {
                var avgTime = elapsed / completedCount;
                var remaining = Math.round((avgTime * (lines.length - completedCount)) / 1000);
                progressEta.textContent = "~" + remaining + "s remaining";
              } else {
                progressEta.textContent = "";
              }

              // Continue or finish
              if (completedCount >= lines.length) {
                resolve();
              } else {
                next();
              }
            });
          })(item);
        }
      }

      next();
    });

    // Auto-retry failed tasks
    if (autoRetryCheckbox.checked && !isCancelled) {
      var failedIndices = [];
      for (var k = 0; k < batchResults.length; k++) {
        if (batchResults[k] && batchResults[k].error) {
          failedIndices.push(k);
        }
      }
      if (failedIndices.length > 0 && failedIndices.length <= 10) {
        progressTitle.textContent = "Retrying " + failedIndices.length + " failed...";
        for (var fi = 0; fi < failedIndices.length; fi++) {
          var idx = failedIndices[fi];
          var pip2 = document.getElementById("pip-" + idx);
          if (pip2) pip2.className = "progress-pip running";

          var retryResult = await processTask(batchResults[idx].task, idx);
          batchResults[idx] = retryResult;

          if (pip2) pip2.className = "progress-pip " + (retryResult.error ? "error" : "done");
        }
      }
    }

    // Done
    isRunning = false;
    btnRun.style.display = "inline-flex";
    btnPause.style.display = "none";
    btnCancel.style.display = "none";
    progressSection.style.display = "none";

    if (!isCancelled) {
      renderResults();
      showToast("Batch complete! " + batchResults.length + " tasks processed");
    } else {
      var completed = batchResults.filter(function (r) { return r !== null; }).length;
      if (completed > 0) {
        renderResults();
        showToast("Batch cancelled. " + completed + " / " + lines.length + " completed.");
      }
    }
  }

  // =============================================
  // Pause / Cancel
  // =============================================
  btnPause.addEventListener("click", function () {
    isPaused = !isPaused;
    btnPause.textContent = isPaused ? "Resume" : "Pause";
    progressTitle.textContent = isPaused ? "Paused" : "Processing...";
  });

  btnCancel.addEventListener("click", function () {
    isCancelled = true;
    progressTitle.textContent = "Cancelling...";
  });

  // =============================================
  // Render results
  // =============================================
  function getStats() {
    var stats = { total: 0, claude: 0, cheap_llm: 0, split: 0, error: 0, totalDuration: 0 };
    batchResults.forEach(function (r) {
      if (!r) return;
      stats.total++;
      if (r.error) stats.error++;
      else if (r.route === "claude") stats.claude++;
      else if (r.route === "cheap_llm") stats.cheap_llm++;
      else if (r.route === "split") stats.split++;
      stats.totalDuration += r.duration || 0;
    });
    return stats;
  }

  function renderResults() {
    var stats = getStats();
    resultsSection.style.display = "block";

    // Summary Cards
    var avgTime = stats.total > 0 ? Math.round(stats.totalDuration / stats.total / 1000 * 10) / 10 : 0;
    var totalTime = Math.round(stats.totalDuration / 1000 * 10) / 10;
    summaryCards.innerHTML =
      '<div class="summary-card highlight">' +
        '<div class="summary-card-value">' + stats.total + '</div>' +
        '<div class="summary-card-label">Total</div>' +
      '</div>' +
      '<div class="summary-card">' +
        '<div class="summary-card-value">' + stats.claude + '</div>' +
        '<div class="summary-card-label">Claude</div>' +
      '</div>' +
      '<div class="summary-card">' +
        '<div class="summary-card-value">' + stats.cheap_llm + '</div>' +
        '<div class="summary-card-label">Groq</div>' +
      '</div>' +
      '<div class="summary-card">' +
        '<div class="summary-card-value">' + stats.split + '</div>' +
        '<div class="summary-card-label">Split</div>' +
      '</div>' +
      '<div class="summary-card">' +
        '<div class="summary-card-value">' + stats.error + '</div>' +
        '<div class="summary-card-label">Errors</div>' +
      '</div>' +
      '<div class="summary-card">' +
        '<div class="summary-card-value">' + avgTime + 's</div>' +
        '<div class="summary-card-label">Avg Time</div>' +
      '</div>';

    // Route Distribution Chart
    renderChart(stats);

    // Filter Tabs
    renderFilterTabs(stats);

    // Table
    renderTable();

    // Scroll to results
    resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function renderChart(stats) {
    if (stats.total === 0) {
      routeChart.innerHTML = "";
      routeLegend.innerHTML = "";
      return;
    }

    var segments = [
      { key: "claude", label: "Claude", count: stats.claude },
      { key: "cheap_llm", label: "Groq", count: stats.cheap_llm },
      { key: "split", label: "Split", count: stats.split },
      { key: "error", label: "Error", count: stats.error },
    ].filter(function (s) { return s.count > 0; });

    routeChart.innerHTML = "";
    segments.forEach(function (seg) {
      var pct = (seg.count / stats.total * 100).toFixed(1);
      var div = document.createElement("div");
      div.className = "route-chart-seg " + seg.key;
      div.style.width = pct + "%";
      div.textContent = pct > 10 ? seg.label + " " + seg.count : seg.count;
      routeChart.appendChild(div);
    });

    routeLegend.innerHTML = segments.map(function (seg) {
      var pct = (seg.count / stats.total * 100).toFixed(0);
      return '<span class="route-legend-item">' +
        '<span class="route-legend-dot ' + seg.key + '"></span>' +
        seg.label + ' ' + seg.count + ' (' + pct + '%)' +
      '</span>';
    }).join("");
  }

  function renderFilterTabs(stats) {
    var tabs = [
      { key: "all", label: "All", count: stats.total },
      { key: "claude", label: "Claude", count: stats.claude },
      { key: "cheap_llm", label: "Groq", count: stats.cheap_llm },
      { key: "split", label: "Split", count: stats.split },
      { key: "error", label: "Errors", count: stats.error },
    ];

    filterTabs.innerHTML = "";
    tabs.forEach(function (tab) {
      var btn = document.createElement("button");
      btn.className = "filter-tab" + (activeFilter === tab.key ? " active" : "");
      btn.innerHTML = tab.label + '<span class="tab-count">' + tab.count + '</span>';
      btn.addEventListener("click", function () {
        activeFilter = tab.key;
        renderFilterTabs(getStats());
        renderTable();
      });
      filterTabs.appendChild(btn);
    });
  }

  function getFilteredResults() {
    var filtered = batchResults.filter(function (r) {
      if (!r) return false;
      if (activeFilter === "all") return true;
      if (activeFilter === "error") return !!r.error;
      return !r.error && r.route === activeFilter;
    });

    // Sort
    if (sortColumn) {
      filtered.sort(function (a, b) {
        var va, vb;
        if (sortColumn === "index") { va = a.index; vb = b.index; }
        else if (sortColumn === "task") { va = a.task; vb = b.task; }
        else if (sortColumn === "route") { va = a.error ? "zzz" : a.route; vb = b.error ? "zzz" : b.route; }
        else if (sortColumn === "tickets") { va = a.tickets; vb = b.tickets; }
        else if (sortColumn === "time") { va = a.duration; vb = b.duration; }

        if (va < vb) return sortAsc ? -1 : 1;
        if (va > vb) return sortAsc ? 1 : -1;
        return 0;
      });
    }

    return filtered;
  }

  function renderTable() {
    var filtered = getFilteredResults();

    var cols = [
      { key: "index", label: "#" },
      { key: "task", label: "Task" },
      { key: "route", label: "Route" },
      { key: "tickets", label: "Tickets" },
      { key: "time", label: "Time" },
      { key: "actions", label: "Actions" },
    ];

    var html = '<table class="result-table"><thead><tr>';
    cols.forEach(function (col) {
      var sorted = sortColumn === col.key;
      var arrow = col.key === "actions" ? "" : '<span class="sort-arrow">' + (sorted ? (sortAsc ? "^" : "v") : "-") + '</span>';
      html += '<th class="' + (sorted ? "sorted" : "") + '" data-col="' + col.key + '">' +
        col.label + arrow + '</th>';
    });
    html += "</tr></thead><tbody>";

    filtered.forEach(function (r) {
      var routeClass = r.error ? "error" : r.route;
      var statusText = r.error ? "ERR" : "OK";
      var statusClass = r.error ? "error" : "done";
      var timeStr = (r.duration / 1000).toFixed(1) + "s";

      html += '<tr class="batch-row" data-idx="' + r.index + '">';
      html += "<td>" + (r.index + 1) + "</td>";
      html += "<td>" + escapeHtml(r.task.substring(0, 80)) + (r.task.length > 80 ? "..." : "") + "</td>";
      html += '<td><span class="route-badge ' + routeClass + '">' + (r.error ? "error" : r.route) + "</span></td>";
      html += "<td>" + (r.error ? "-" : r.tickets) + "</td>";
      html += "<td>" + timeStr + "</td>";
      html += '<td class="row-actions">' +
        '<button class="row-action-btn" data-action="copy" data-idx="' + r.index + '">Copy</button>' +
        (r.error ? '<button class="row-action-btn" data-action="retry" data-idx="' + r.index + '">Retry</button>' : '') +
        '<button class="row-action-btn" data-action="splitter" data-idx="' + r.index + '">Splitter</button>' +
      '</td>';
      html += "</tr>";
      html += '<tr class="detail-row"><td colspan="6"><div class="task-detail-output" id="detail-' + r.index + '">' +
        escapeHtml(r.error || r.output || "(no output)") + "</div></td></tr>";
    });

    html += "</tbody></table>";
    tableContainer.innerHTML = html;

    // Sort headers
    tableContainer.querySelectorAll("th[data-col]").forEach(function (th) {
      if (th.dataset.col === "actions") return;
      th.addEventListener("click", function () {
        var col = th.dataset.col;
        if (sortColumn === col) {
          sortAsc = !sortAsc;
        } else {
          sortColumn = col;
          sortAsc = true;
        }
        renderTable();
      });
    });

    // Toggle detail
    tableContainer.querySelectorAll(".batch-row").forEach(function (row) {
      row.addEventListener("click", function (e) {
        if (e.target.closest(".row-action-btn")) return;
        var idx = row.dataset.idx;
        var detail = document.getElementById("detail-" + idx);
        if (detail) detail.style.display = detail.style.display === "block" ? "none" : "block";
      });
    });

    // Row action buttons
    tableContainer.querySelectorAll(".row-action-btn").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        var action = btn.dataset.action;
        var idx = parseInt(btn.dataset.idx, 10);
        var result = batchResults[idx];
        if (!result) return;

        if (action === "copy") {
          navigator.clipboard.writeText(result.output || result.error || "")
            .then(function () { showToast("Output copied!"); })
            .catch(function () { showToast("Copy failed"); });
        } else if (action === "retry") {
          retryTask(idx);
        } else if (action === "splitter") {
          sessionStorage.setItem("ssh_prompt_use", result.task);
          window.location.href = "/router.html";
        }
      });
    });
  }

  // =============================================
  // Retry single task
  // =============================================
  async function retryTask(idx) {
    var result = batchResults[idx];
    if (!result) return;

    showToast("Retrying task " + (idx + 1) + "...");
    var newResult = await processTask(result.task, idx);
    batchResults[idx] = newResult;
    renderResults();
    showToast(newResult.error ? "Retry failed again" : "Retry succeeded!");
  }

  // =============================================
  // Retry all failed
  // =============================================
  btnRetryfailed.addEventListener("click", async function () {
    var failed = [];
    batchResults.forEach(function (r, i) {
      if (r && r.error) failed.push(i);
    });

    if (!failed.length) {
      showToast("No failed tasks to retry");
      return;
    }

    showToast("Retrying " + failed.length + " failed tasks...");
    for (var i = 0; i < failed.length; i++) {
      var idx = failed[i];
      var newResult = await processTask(batchResults[idx].task, idx);
      batchResults[idx] = newResult;
    }
    renderResults();
    showToast("Retry complete!");
  });

  // =============================================
  // Send to Splitter
  // =============================================
  btnSendSplitter.addEventListener("click", function () {
    var tasks = batchResults.filter(function (r) { return r && !r.error; })
      .map(function (r) { return r.task; });
    if (!tasks.length) {
      showToast("No successful tasks to send");
      return;
    }
    sessionStorage.setItem("ssh_prompt_use", tasks[0]);
    window.location.href = "/router.html";
  });

  // =============================================
  // Export CSV
  // =============================================
  function exportCsv() {
    if (!batchResults.length) { showToast("No results to export"); return; }

    var csv = "Index,Task,Route,Tickets,Status,Duration_ms\n";
    batchResults.forEach(function (r, i) {
      if (!r) return;
      csv += (r.index + 1) + ',"' + r.task.replace(/"/g, '""') + '",' +
        (r.error ? "error" : r.route) + "," +
        (r.error ? 0 : r.tickets) + "," +
        (r.error ? "error" : "ok") + "," +
        r.duration + "\n";
    });

    downloadBlob(csv, "batch_results.csv", "text/csv");
    showToast("CSV exported!");
  }

  // =============================================
  // Export JSON
  // =============================================
  function exportJson() {
    if (!batchResults.length) { showToast("No results to export"); return; }

    var data = {
      exported_at: new Date().toISOString(),
      stats: getStats(),
      results: batchResults.filter(function (r) { return r !== null; }).map(function (r) {
        return {
          index: r.index + 1,
          task: r.task,
          route: r.error ? "error" : r.route,
          tickets: r.tickets,
          status: r.error ? "error" : "ok",
          error: r.error || null,
          duration_ms: r.duration,
          output: r.output,
        };
      }),
    };

    downloadBlob(JSON.stringify(data, null, 2), "batch_results.json", "application/json");
    showToast("JSON exported!");
  }

  function downloadBlob(content, filename, type) {
    var blob = new Blob([content], { type: type });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  // =============================================
  // Copy all outputs
  // =============================================
  function copyAll() {
    if (!batchResults.length) { showToast("No results to copy"); return; }
    var text = batchResults
      .filter(function (r) { return r !== null; })
      .map(function (r) {
        return "--- Task " + (r.index + 1) + " ---\n" + r.task + "\n\n" + (r.error || r.output || "(no output)");
      }).join("\n\n");
    navigator.clipboard.writeText(text)
      .then(function () { showToast("All outputs copied!"); })
      .catch(function (e) { showToast("Copy failed: " + e.message); });
  }

  // =============================================
  // Batch History (localStorage)
  // =============================================
  var HISTORY_KEY = "ssh_batch_history";
  var MAX_HISTORY = 20;

  function getHistory() {
    try {
      return JSON.parse(localStorage.getItem(HISTORY_KEY)) || [];
    } catch (e) {
      return [];
    }
  }

  function saveHistory() {
    if (!batchResults.length) {
      showToast("No results to save");
      return;
    }

    var stats = getStats();
    var entry = {
      id: Date.now(),
      date: new Date().toISOString(),
      taskCount: stats.total,
      stats: stats,
      tasks: batchResults.filter(function (r) { return r !== null; }).map(function (r) {
        return { task: r.task, route: r.error ? "error" : r.route, tickets: r.tickets, error: r.error || "" };
      }),
    };

    var history = getHistory();
    history.unshift(entry);
    if (history.length > MAX_HISTORY) history = history.slice(0, MAX_HISTORY);

    try {
      localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
      showToast("Saved to batch history");
      renderHistory();
    } catch (e) {
      showToast("Save failed (storage full?)");
    }
  }

  function renderHistory() {
    var history = getHistory();

    if (!history.length) {
      historyList.innerHTML = '<div class="history-empty">No batch history yet. Run a batch and save results.</div>';
      return;
    }

    historyList.innerHTML = "";
    history.forEach(function (entry) {
      var date = new Date(entry.date);
      var dateStr = date.toLocaleDateString() + " " + date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      var firstTask = entry.tasks.length > 0 ? entry.tasks[0].task.substring(0, 40) : "Empty batch";

      var item = document.createElement("div");
      item.className = "history-item";
      item.innerHTML =
        '<div class="history-item-info">' +
          '<span class="history-item-title">' + escapeHtml(firstTask) + (entry.tasks.length > 1 ? " (+" + (entry.tasks.length - 1) + " more)" : "") + '</span>' +
          '<span class="history-item-meta">' + dateStr + ' | ' + entry.taskCount + ' tasks | Claude: ' + entry.stats.claude + ', Groq: ' + entry.stats.cheap_llm + '</span>' +
        '</div>' +
        '<div class="history-item-actions">' +
          '<button class="row-action-btn" data-hid="' + entry.id + '" data-haction="load">Load</button>' +
          '<button class="row-action-btn" data-hid="' + entry.id + '" data-haction="delete">Delete</button>' +
        '</div>';

      historyList.appendChild(item);
    });

    // History action handlers
    historyList.querySelectorAll(".row-action-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var id = parseInt(btn.dataset.hid, 10);
        var action = btn.dataset.haction;

        if (action === "load") {
          var history = getHistory();
          var entry = history.find(function (e) { return e.id === id; });
          if (entry) {
            textarea.value = entry.tasks.map(function (t) { return t.task; }).join("\n");
            updateTaskCount();
            showToast("Loaded " + entry.tasks.length + " tasks from history");
          }
        } else if (action === "delete") {
          var hist = getHistory();
          hist = hist.filter(function (e) { return e.id !== id; });
          try {
            localStorage.setItem(HISTORY_KEY, JSON.stringify(hist));
          } catch (e) { /* ignore */ }
          renderHistory();
          showToast("History entry deleted");
        }
      });
    });
  }

  // =============================================
  // Load sample tasks
  // =============================================
  function loadSample() {
    textarea.value =
      "Build a login page with email validation\n" +
      "Add dark mode toggle to the settings page\n" +
      "Fix the navigation menu on mobile\n" +
      "Create a contact form with SMTP integration\n" +
      "Optimize database queries for user dashboard\n" +
      "Implement user profile picture upload\n" +
      "Add search functionality with autocomplete\n" +
      "Create a real-time notification system";
    updateTaskCount();
    showToast("Sample loaded (8 tasks)");
  }

  // =============================================
  // Event Listeners
  // =============================================
  btnRun.addEventListener("click", runBatch);
  btnClear.addEventListener("click", function () {
    textarea.value = "";
    updateTaskCount();
    resultsSection.style.display = "none";
    batchResults = [];
  });
  btnSample.addEventListener("click", loadSample);
  btnSaveHistory.addEventListener("click", saveHistory);
  btnExportCsv.addEventListener("click", exportCsv);
  btnExportJson.addEventListener("click", exportJson);
  btnCopyAll.addEventListener("click", copyAll);

  // =============================================
  // Init
  // =============================================
  getRouter();
  renderHistory();

  // Check for tasks from Splitter
  var batchFromSplitter = sessionStorage.getItem("ssh_batch_tasks");
  if (batchFromSplitter) {
    textarea.value = batchFromSplitter;
    sessionStorage.removeItem("ssh_batch_tasks");
    updateTaskCount();
    showToast("Tasks loaded from Splitter");
  }
})();
