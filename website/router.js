/* ============================================
   Router Web UI — JavaScript
   ============================================ */

(function () {
  "use strict";

  // --- DOM refs ---
  const routerSelect = document.getElementById("router-select");
  const preflightBadge = document.getElementById("preflight-badge");
  const configBody = document.getElementById("config-body");
  const requestInput = document.getElementById("request-input");
  const outputText = document.getElementById("output-text");
  const ticketSelector = document.getElementById("ticket-selector");
  const ticketSelect = document.getElementById("ticket-select");
  const loadingOverlay = document.getElementById("loading-overlay");
  const toast = document.getElementById("toast");

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

  // --- State ---
  let currentOutput = "";
  let currentTickets = [];
  let currentMode = "basic";

  // --- Version toggle ---
  const btnModeBasic = document.getElementById("btn-mode-basic");
  const btnModeV5 = document.getElementById("btn-mode-v5");
  const v5OptionsBar = document.getElementById("v5-options-bar");
  const v5EnabledInput = document.getElementById("opt-v5-enabled");
  const pageTitle = document.getElementById("page-title");
  const pageSub = document.getElementById("page-sub");

  function setMode(mode) {
    currentMode = mode;
    btnModeBasic.classList.toggle("active", mode === "basic");
    btnModeV5.classList.toggle("active", mode === "v5");
    v5OptionsBar.style.display = mode === "v5" ? "block" : "none";

    if (mode === "v5") {
      v5EnabledInput.value = "true";
      pageTitle.textContent = "NLP/ML Engine v5";
      pageSub.innerHTML = "BERT-based intent detection, ML priority ranking, and smart compression.<br>Powered by AI — select options below.";
    } else {
      v5EnabledInput.value = "false";
      pageTitle.textContent = "AI Task Splitter";
      pageSub.innerHTML = "Break down complex requests into simple tasks for Claude AI.<br>No signup. No cost. Just paste and go.";
    }
  }

  btnModeBasic.addEventListener("click", () => setMode("basic"));
  btnModeV5.addEventListener("click", () => setMode("v5"));

  // Check URL params for ?mode=v5
  const urlMode = new URLSearchParams(window.location.search).get("mode");
  if (urlMode === "v5") {
    setMode("v5");
  }

  // --- Config: smooth <details> toggle ---
  const advDetails = document.querySelector(".advanced-settings");
  const advSummary = advDetails && advDetails.querySelector("summary");
  const advBody = advDetails && advDetails.querySelector(".config-body");

  if (advSummary && advBody) {
    advSummary.addEventListener("click", function (e) {
      e.preventDefault();

      if (advDetails.open) {
        // Closing: animate height to 0 then remove [open]
        const h = advBody.scrollHeight;
        advBody.style.height = h + "px";
        advBody.classList.add("collapsing");
        requestAnimationFrame(function () {
          advBody.style.height = "0px";
        });
        advBody.addEventListener("transitionend", function handler() {
          advDetails.open = false;
          advBody.style.height = "";
          advBody.classList.remove("collapsing");
          advBody.removeEventListener("transitionend", handler);
        });
      } else {
        // Opening: set [open], then animate from 0 to full height
        advDetails.open = true;
        var h = advBody.scrollHeight;
        advBody.style.height = "0px";
        advBody.style.overflow = "hidden";
        requestAnimationFrame(function () {
          advBody.style.height = h + "px";
        });
        advBody.addEventListener("transitionend", function handler() {
          advBody.style.height = "";
          advBody.style.overflow = "";
          advBody.removeEventListener("transitionend", handler);
          advDetails.scrollIntoView({ behavior: "smooth", block: "start" });
        });
      }
    });
  }

  // --- Toast ---
  let toastTimer = null;
  function showToast(msg, duration) {
    duration = duration || 2000;
    toast.textContent = msg;
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("show"), duration);
  }

  // --- API helpers ---
  async function apiGet(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error("HTTP " + res.status);
    return res.json();
  }

  async function apiPost(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    return res.json();
  }

  // --- Load routers ---
  async function loadRouters() {
    try {
      const data = await apiGet("/api/routers");
      routerSelect.innerHTML = "";
      (data.routers || []).forEach((r) => {
        const opt = document.createElement("option");
        opt.value = r.path;
        opt.textContent = r.name + "  (" + r.rel + ")";
        routerSelect.appendChild(opt);
      });
      if (!data.routers || data.routers.length === 0) {
        const opt = document.createElement("option");
        opt.value = "";
        opt.textContent = "No routers found";
        routerSelect.appendChild(opt);
      }
    } catch (e) {
      routerSelect.innerHTML = '<option value="">Error loading routers</option>';
    }
  }

  // --- Refresh preflight ---
  async function refreshPreflight() {
    try {
      const data = await apiGet("/api/preflight");
      const status = data.status || "unknown";
      preflightBadge.textContent = status;
      preflightBadge.className = "preflight-badge";
      if (status === "clean") {
        preflightBadge.classList.add("clean");
      } else {
        preflightBadge.classList.add("dirty");
      }
      // Warn if GROQ key missing
      if (data.groq_key === false) {
        showToast("GROQ_API_KEY not set — translation disabled", 4000);
      }
    } catch {
      preflightBadge.textContent = "error";
      preflightBadge.className = "preflight-badge dirty";
    }
  }

  // --- Gather form params ---
  function getFormParams() {
    return {
      router: routerSelect.value,
      request: requestInput.value.trim(),
      friendly: document.getElementById("opt-friendly").checked,
      desktop_edit: document.getElementById("opt-desktop-edit").value === "true",
      force_split: document.getElementById("opt-force-split").checked,
      opus_only: document.getElementById("opt-opus-only").value === "true",
      tickets_md: document.getElementById("opt-tickets-md").value === "true",
      translate_en: document.getElementById("opt-translate").value === "true",
      ticket_groq_translate: document.getElementById("opt-groq-translate").checked,
      economy: document.getElementById("sel-economy").value,
      phase: document.getElementById("sel-phase").value,
      one_task: document.getElementById("inp-one-task").value.trim(),
      max_tickets: document.getElementById("inp-max-tickets").value.trim() || "0",
      min_tickets: document.getElementById("inp-min-tickets").value.trim() || "1",
      merge: document.getElementById("inp-merge").value.trim(),
      // v5.0 NLP/ML params
      v5_enabled: document.getElementById("opt-v5-enabled").value === "true",
      compress: document.getElementById("opt-v5-compress").checked,
      compression_level: parseInt(document.getElementById("sel-v5-level").value, 10),
      show_stats: document.getElementById("opt-v5-stats").checked,
    };
  }

  // --- Run router ---
  async function runRouter() {
    const params = getFormParams();

    if (!params.router) {
      showToast("No router selected.");
      return;
    }
    if (!params.request) {
      showToast("Please enter a request.");
      return;
    }

    loadingOverlay.style.display = "flex";
    outputText.textContent = "Running... sending to /api/route";
    ticketSelector.style.display = "none";

    try {
      const data = await apiPost("/api/route", params);

      if (data.error) {
        outputText.textContent = "Error: " + data.error + "\n\n" + (data.output || "");
      } else {
        currentOutput = data.output || "(no output)";
        outputText.textContent = currentOutput;
      }

      // Show translation status
      if (data.translate_status === "no_api_key") {
        showToast("GROQ_API_KEY not set — Korean text not translated", 4000);
      } else if (data.translate_status && data.translate_status.startsWith("groq_error")) {
        showToast("Groq translation failed: " + data.translate_status, 4000);
      }

      // Populate ticket selector
      currentTickets = data.tickets || [];
      if (currentTickets.length > 0) {
        ticketSelect.innerHTML = "";
        currentTickets.forEach((t) => {
          const opt = document.createElement("option");
          opt.value = t;
          opt.textContent = "Ticket " + t;
          ticketSelect.appendChild(opt);
        });
        ticketSelector.style.display = "flex";
      }

      // Show v5.0 stats if available
      const statsEl = document.getElementById("v5-stats");
      const statsContent = document.getElementById("v5-stats-content");
      if (data.v5_stats && data.v5_stats.enabled) {
        const s = data.v5_stats;
        const parts = ["NLP: ON"];
        if (s.compress) parts.push("Compression: Level " + s.compression_level);
        if (s.token_reduction_rate) parts.push("Token Reduction: " + (s.token_reduction_rate * 100).toFixed(1) + "%");
        if (s.processing_time_ms) parts.push("Time: " + s.processing_time_ms.toFixed(0) + "ms");
        statsContent.textContent = parts.join(" | ");
        statsEl.style.display = "block";
      } else {
        statsEl.style.display = "none";
      }

      refreshPreflight();
    } catch (e) {
      outputText.textContent = "Network error: " + e.message;
    } finally {
      loadingOverlay.style.display = "none";
    }
  }

  // --- Copy Claude Block ---
  async function copyClaudeBlock() {
    if (!currentOutput) {
      showToast("No output to extract from.");
      return;
    }

    const ticket = ticketSelect.value || "A";
    const params = getFormParams();

    try {
      const data = await apiPost("/api/extract-block", {
        output: currentOutput,
        ticket: ticket,
        translate_groq: params.ticket_groq_translate,
        append_rules: true,
      });

      if (data.success && data.block) {
        await navigator.clipboard.writeText(data.block);
        showToast("Claude block copied! (Ticket " + ticket + ")");
      } else {
        showToast("Could not find a Claude block.");
      }
    } catch (e) {
      showToast("Copy failed: " + e.message);
    }
  }

  // --- Copy helpers ---
  async function copyToClipboard(text, label) {
    if (!text) {
      showToast("Nothing to copy.");
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      showToast(label + " copied!");
    } catch (e) {
      showToast("Copy failed: " + e.message);
    }
  }

  // --- Event listeners ---
  document.getElementById("btn-run").addEventListener("click", runRouter);
  document.getElementById("btn-copy-block").addEventListener("click", copyClaudeBlock);
  document.getElementById("btn-clear-input").addEventListener("click", () => {
    requestInput.value = "";
    requestInput.focus();
  });
  document.getElementById("btn-clear-output").addEventListener("click", () => {
    currentOutput = "";
    currentTickets = [];
    outputText.textContent = "Ready.";
    ticketSelector.style.display = "none";
  });
  document.getElementById("btn-refresh").addEventListener("click", () => {
    loadRouters();
    refreshPreflight();
    showToast("Refreshed.");
  });

  // Ctrl/Cmd+Enter to run
  requestInput.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      runRouter();
    }
  });

  // --- Init ---
  loadRouters();
  refreshPreflight();

  // Check for prompt from Prompt Library "Use in Splitter" action
  const promptFromLib = sessionStorage.getItem("ssh_prompt_use");
  if (promptFromLib) {
    requestInput.value = promptFromLib;
    sessionStorage.removeItem("ssh_prompt_use");
  }
})();
