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
  const btnModeBlueprint = document.getElementById("btn-mode-blueprint");
  const v5OptionsBar = document.getElementById("v5-options-bar");
  const v5EnabledInput = document.getElementById("opt-v5-enabled");
  const pageTitle = document.getElementById("page-title");
  const pageSub = document.getElementById("page-sub");

  function setMode(mode) {
    currentMode = mode;
    btnModeBasic.classList.toggle("active", mode === "basic");
    btnModeV5.classList.toggle("active", mode === "v5");
    btnModeBlueprint.classList.toggle("active", mode === "blueprint");
    v5OptionsBar.style.display = mode === "v5" ? "block" : "none";

    var btnRun = document.getElementById("btn-run");

    if (mode === "v5") {
      v5EnabledInput.value = "true";
      pageTitle.textContent = "NLP/ML Engine v5";
      pageSub.innerHTML = "Hybrid NLP engine: SentenceTransformer embeddings + SVM classifier + keyword analysis.<br>Powered by AI — select options below.";
      requestInput.placeholder = "Example: Build a contact form with email validation and add a thank you page";
      if (btnRun) btnRun.textContent = "Split Tasks";
    } else if (mode === "blueprint") {
      v5EnabledInput.value = "false";
      pageTitle.textContent = "Project Blueprint";
      pageSub.innerHTML = "Enter a short project idea and get a full implementation plan.<br>Architecture, tech stack, features, and step-by-step tasks.";
      requestInput.placeholder = "Example: Used car platform website\nExample: SaaS billing dashboard\nExample: AI chatbot for customer support";
      if (btnRun) btnRun.textContent = "Generate Blueprint";
    } else {
      v5EnabledInput.value = "false";
      pageTitle.textContent = "AI Task Splitter";
      pageSub.innerHTML = "Break down complex requests into simple tasks for Claude AI.<br>No signup. No cost. Just paste and go.";
      requestInput.placeholder = "Example: Build a contact form with email validation and add a thank you page";
      if (btnRun) btnRun.textContent = "Split Tasks";
    }
  }

  btnModeBasic.addEventListener("click", () => setMode("basic"));
  btnModeV5.addEventListener("click", () => setMode("v5"));
  btnModeBlueprint.addEventListener("click", () => setMode("blueprint"));

  // Check URL params for ?mode=v5 or ?mode=blueprint
  const urlMode = new URLSearchParams(window.location.search).get("mode");
  if (urlMode === "v5") {
    setMode("v5");
  } else if (urlMode === "blueprint") {
    setMode("blueprint");
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

  // --- Blueprint generator (client-side, no router needed) ---
  function generateBlueprint(idea) {
    var P = idea.trim();
    var tickets = [
      {
        letter: "A",
        title: "Project Overview & Tech Stack",
        summary_ko: "Set up project structure and choose the tech stack",
        prompt: "I'm building: " + P + "\n\n" +
          "Please help me create a complete project overview:\n" +
          "1. Project summary - What this project does, target users, key value proposition\n" +
          "2. Recommended tech stack - Frontend framework, backend, database, hosting (with reasons for each choice)\n" +
          "3. Project folder structure - Show the recommended directory layout\n" +
          "4. Key dependencies - List npm packages or libraries needed\n" +
          "5. Development environment setup - Step-by-step commands to initialize the project\n\n" +
          "Be specific to this project. Provide actual commands and file structures I can use immediately."
      },
      {
        letter: "B",
        title: "Database Schema & Data Model",
        summary_ko: "Design database tables, relationships, and seed data",
        prompt: "Project: " + P + "\n\n" +
          "Design the complete database schema for this project:\n" +
          "1. List all entities/tables needed (users, products, orders, etc. - specific to this project)\n" +
          "2. Define each table with columns, data types, constraints, and relationships\n" +
          "3. Draw the ER diagram in text format showing relationships (1:N, N:M)\n" +
          "4. Write the actual SQL CREATE TABLE statements or ORM model definitions\n" +
          "5. Include seed data examples for testing\n" +
          "6. Add indexes for performance on frequently queried columns\n\n" +
          "Make the schema production-ready with proper normalization and foreign keys."
      },
      {
        letter: "C",
        title: "Authentication & User System",
        summary_ko: "Build login, signup, JWT auth, and role-based access",
        prompt: "Project: " + P + "\n\n" +
          "Implement the complete authentication and user management system:\n" +
          "1. User registration (signup) with email validation\n" +
          "2. Login with JWT token (access + refresh token strategy)\n" +
          "3. Password hashing with bcrypt, password reset flow\n" +
          "4. User roles and permissions (admin, regular user, guest)\n" +
          "5. Protected routes / middleware for authorization\n" +
          "6. Session management and token refresh logic\n" +
          "7. Social login integration points (Google, GitHub)\n\n" +
          "Provide complete, working code for each component. Include the API endpoints, middleware, and frontend forms."
      },
      {
        letter: "D",
        title: "Core Features Implementation",
        summary_ko: "Implement the primary unique feature of this project",
        prompt: "Project: " + P + "\n\n" +
          "Build the core features that make this project unique:\n" +
          "1. Analyze what the MAIN functionality of '" + P + "' should be\n" +
          "2. List the top 5-7 core features with detailed user stories\n" +
          "3. For each feature, provide:\n" +
          "   - Backend API endpoint (method, path, request/response format)\n" +
          "   - Database queries needed\n" +
          "   - Frontend component structure\n" +
          "   - Business logic and validation rules\n" +
          "4. Implement the #1 most important feature with complete working code\n" +
          "5. Define the data flow: User action -> Frontend -> API -> Database -> Response\n\n" +
          "Focus on what makes '" + P + "' special compared to generic CRUD apps."
      },
      {
        letter: "E",
        title: "UI/UX Design & Page Structure",
        summary_ko: "Design page layouts, navigation, and responsive components",
        prompt: "Project: " + P + "\n\n" +
          "Design the complete UI/UX and page structure:\n" +
          "1. Sitemap - List all pages/routes the application needs\n" +
          "2. For each page, describe:\n" +
          "   - Purpose and key content\n" +
          "   - UI components needed (header, cards, forms, modals, etc.)\n" +
          "   - User interactions and state changes\n" +
          "3. Navigation structure (header nav, sidebar, mobile menu)\n" +
          "4. Design system basics: color palette, typography, spacing, border radius\n" +
          "5. Responsive breakpoints strategy (mobile-first)\n" +
          "6. Create the main landing/home page with complete HTML/CSS code\n" +
          "7. Key UI patterns: loading states, empty states, error states, success feedback\n\n" +
          "Provide actual component code for the 3 most important pages."
      },
      {
        letter: "F",
        title: "REST API Design & Endpoints",
        summary_ko: "Design REST endpoints with CRUD, validation, and error handling",
        prompt: "Project: " + P + "\n\n" +
          "Design and implement the complete REST API:\n" +
          "1. API endpoint table:\n" +
          "   | Method | Path | Description | Auth Required | Request Body | Response |\n" +
          "2. Group endpoints by resource (users, [main entities], admin)\n" +
          "3. Implement CRUD operations for each main entity\n" +
          "4. Error handling middleware with consistent error response format\n" +
          "5. Request validation with proper error messages\n" +
          "6. Pagination, filtering, and sorting query parameters\n" +
          "7. Rate limiting and security headers\n\n" +
          "Provide complete route handler code for all endpoints. Include request/response examples."
      },
      {
        letter: "G",
        title: "Search, Filter & Data Display",
        summary_ko: "Add search, multi-filter, sorting, and pagination",
        prompt: "Project: " + P + "\n\n" +
          "Implement search, filtering, and data display features:\n" +
          "1. Full-text search functionality across key fields\n" +
          "2. Multi-criteria filtering (category, price range, date, status, etc. - specific to this project)\n" +
          "3. Sorting options (newest, price, popularity, relevance)\n" +
          "4. Pagination with page numbers and items-per-page selector\n" +
          "5. List view vs Grid view toggle\n" +
          "6. Frontend filter UI components with real-time URL query params\n" +
          "7. Backend query builder that combines search + filters + sort + pagination efficiently\n\n" +
          "Provide both the backend query logic and frontend filter components with working code."
      },
      {
        letter: "H",
        title: "Admin Dashboard",
        summary_ko: "Build admin panel with metrics, user and content management",
        prompt: "Project: " + P + "\n\n" +
          "Build the admin dashboard for managing this platform:\n" +
          "1. Dashboard overview page with key metrics:\n" +
          "   - Total users, new registrations, active users\n" +
          "   - Content/listing statistics specific to this project\n" +
          "   - Simple charts (bar chart for weekly data, pie chart for categories)\n" +
          "2. User management: list, search, edit, ban/activate\n" +
          "3. Content management: approve/reject, edit, delete listings/items\n" +
          "4. Settings page for site configuration\n" +
          "5. Activity log / audit trail\n" +
          "6. Admin-only route protection\n\n" +
          "Provide the complete admin layout with sidebar navigation and implement 2 key admin pages."
      },
      {
        letter: "I",
        title: "Testing & Security Hardening",
        summary_ko: "Write tests, fix security vulnerabilities, harden the app",
        prompt: "Project: " + P + "\n\n" +
          "Add testing and security hardening:\n" +
          "1. Unit tests for core business logic (at least 5 test cases)\n" +
          "2. API integration tests for critical endpoints\n" +
          "3. Security checklist:\n" +
          "   - SQL injection prevention (parameterized queries)\n" +
          "   - XSS prevention (input sanitization, CSP headers)\n" +
          "   - CSRF protection\n" +
          "   - Rate limiting on auth endpoints\n" +
          "   - Secure HTTP headers (Helmet.js or equivalent)\n" +
          "   - File upload validation (if applicable)\n" +
          "4. Input validation on both client and server side\n" +
          "5. Environment variable management (.env setup)\n" +
          "6. Error logging strategy\n\n" +
          "Provide working test files and security middleware code."
      },
      {
        letter: "J",
        title: "SEO, Performance & Deployment",
        summary_ko: "Optimize SEO and performance, set up CI/CD and deploy",
        prompt: "Project: " + P + "\n\n" +
          "Optimize and deploy the project:\n" +
          "1. SEO optimization:\n" +
          "   - Meta tags, Open Graph, Twitter cards for each page\n" +
          "   - Semantic HTML structure\n" +
          "   - Sitemap.xml and robots.txt\n" +
          "   - Structured data (JSON-LD) for search engines\n" +
          "2. Performance:\n" +
          "   - Image optimization and lazy loading\n" +
          "   - Code splitting and bundle optimization\n" +
          "   - Database query optimization and caching strategy\n" +
          "   - CDN configuration\n" +
          "3. Deployment:\n" +
          "   - Recommended hosting (Vercel, Railway, AWS, etc.) with reasons\n" +
          "   - Environment configuration (production vs development)\n" +
          "   - CI/CD pipeline setup (GitHub Actions)\n" +
          "   - Domain and SSL setup\n" +
          "   - Monitoring and error tracking (Sentry, etc.)\n\n" +
          "Provide deployment configuration files and CI/CD workflow YAML."
      }
    ];

    // Build terminal-style output matching router format
    var output = "[" + tickets.length + " tickets] Run one at a time. A -> finish -> new session -> B\n\n";
    tickets.forEach(function (t) {
      output += "Ticket " + t.letter + " -- " + t.title + "\n";
      if (t.summary_ko) output += "// " + t.summary_ko + "\n";
      output += "[CLAUDE 85%]\n\n";
      output += "[Copy and paste to Claude]\n";
      output += "```\n" + t.prompt + "\n```\n";
      output += "next: " + t.letter + ": " + t.title + "\n\n";
    });

    // Store for easy card rendering
    window._blueprintTickets = tickets;

    return { output: output, tickets: tickets };
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

    // Blueprint mode: call /api/blueprint (Groq AI) with local fallback
    if (currentMode === "blueprint") {
      var loadingTextEl = document.getElementById("loading-text");
      if (loadingTextEl) loadingTextEl.textContent = "Generating blueprint with AI...";
      loadingOverlay.style.display = "flex";
      outputText.textContent = "Generating project blueprint...";

      try {
        var bpData = await apiPost("/api/blueprint", { idea: params.request });

        if (bpData.error) {
          // API error — fall back to local generator
          var blueprint = generateBlueprint(params.request);
          currentOutput = blueprint.output;
          currentTickets = blueprint.tickets.map(function (t) { return t.letter; });
          showToast("AI unavailable, used local templates.", 3000);
        } else {
          // Build terminal-style output from AI tickets
          var tickets = bpData.tickets || [];
          var output = "[" + tickets.length + " phases] AI-generated blueprint. Run one at a time. A -> finish -> new session -> B\n\n";
          tickets.forEach(function (t) {
            output += "Ticket " + t.letter + " -- " + t.title + "\n";
            if (t.summary_ko) output += "// " + t.summary_ko + "\n";
            else if (t.summary) output += t.summary + "\n";
            output += "[CLAUDE 85%]\n\n";
            output += "[Copy and paste to Claude]\n";
            output += "```\n" + t.prompt + "\n```\n";
            output += "next: " + t.letter + ": " + t.title + "\n\n";
          });
          currentOutput = output;
          // Store raw tickets for easy card rendering
          window._blueprintTickets = tickets;
          currentTickets = tickets.map(function (t) { return t.letter; });
          showToast("AI Blueprint generated! " + tickets.length + " phases.", 3000);
        }

        // Render terminal output with non-copyable Korean summaries
        renderTerminalWithKo(currentOutput);

        // Populate ticket selector
        ticketSelect.innerHTML = "";
        currentTickets.forEach(function (t) {
          var opt = document.createElement("option");
          opt.value = t;
          opt.textContent = "Ticket " + t;
          ticketSelect.appendChild(opt);
        });
        ticketSelector.style.display = "flex";

        // Update easy view
        if (easyMode) {
          renderEasyCards();
        }
      } catch (e) {
        // Network error — fall back to local generator
        var blueprint = generateBlueprint(params.request);
        currentOutput = blueprint.output;
        renderTerminalWithKo(currentOutput);
        currentTickets = blueprint.tickets.map(function (t) { return t.letter; });

        ticketSelect.innerHTML = "";
        currentTickets.forEach(function (t) {
          var opt = document.createElement("option");
          opt.value = t;
          opt.textContent = "Ticket " + t;
          ticketSelect.appendChild(opt);
        });
        ticketSelector.style.display = "flex";

        if (easyMode) renderEasyCards();
        showToast("Network error, used local templates.", 3000);
      } finally {
        loadingOverlay.style.display = "none";
      }
      return;
    }

    var loadingTextEl = document.getElementById("loading-text");
    if (loadingTextEl) {
      loadingTextEl.textContent = "Splitting your tasks...";
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
        const intentPct = s.intent_accuracy ? (s.intent_accuracy * 100).toFixed(0) : "--";
        const priorityPct = s.priority_confidence ? (s.priority_confidence * 100).toFixed(0) : "--";
        const reductionPct = s.token_reduction_rate ? (s.token_reduction_rate * 100).toFixed(1) : "0.0";
        const timeMs = s.processing_time_ms ? s.processing_time_ms.toFixed(0) : "--";
        const origTokens = s.original_tokens || "--";
        const compTokens = s.compressed_tokens || "--";
        const level = s.compression_level || 2;

        statsContent.innerHTML =
          '<div class="v5-stats-header">' +
            '<span class="v5-stats-title">v5.0 NLP/ML Pipeline</span>' +
          '</div>' +
          '<div class="v5-pipeline">' +
            '<div class="v5-pipeline-stage active">' +
              '<span class="v5-pipeline-check">&#10003;</span>' +
              '<span class="v5-pipeline-label">Intent Detection</span>' +
            '</div>' +
            '<span class="v5-pipeline-arrow">&#9654;</span>' +
            '<div class="v5-pipeline-stage active">' +
              '<span class="v5-pipeline-check">&#10003;</span>' +
              '<span class="v5-pipeline-label">Priority Ranking</span>' +
            '</div>' +
            '<span class="v5-pipeline-arrow">&#9654;</span>' +
            '<div class="v5-pipeline-stage' + (s.compress ? ' active' : '') + '">' +
              (s.compress ? '<span class="v5-pipeline-check">&#10003;</span>' : '') +
              '<span class="v5-pipeline-label">Compression</span>' +
            '</div>' +
          '</div>' +
          '<div class="v5-stats-grid">' +
            '<div class="v5-stat-item">' +
              '<span class="v5-stat-label">Intent</span>' +
              '<span class="v5-stat-value">' + intentPct + '%</span>' +
            '</div>' +
            '<div class="v5-stat-item">' +
              '<span class="v5-stat-label">Priority</span>' +
              '<span class="v5-stat-value">ML ' + priorityPct + '%</span>' +
            '</div>' +
            '<div class="v5-stat-item">' +
              '<span class="v5-stat-label">Compress</span>' +
              '<span class="v5-stat-value">Level ' + level + '</span>' +
            '</div>' +
            '<div class="v5-stat-item">' +
              '<span class="v5-stat-label">Tokens</span>' +
              '<span class="v5-stat-value">' + origTokens + ' &rarr; ' + compTokens + '</span>' +
            '</div>' +
            '<div class="v5-stat-item">' +
              '<span class="v5-stat-label">Reduction</span>' +
              '<span class="v5-stat-value">' + reductionPct + '%</span>' +
            '</div>' +
            '<div class="v5-stat-item">' +
              '<span class="v5-stat-label">Time</span>' +
              '<span class="v5-stat-value">' + timeMs + 'ms</span>' +
            '</div>' +
          '</div>';
        statsEl.style.display = "block";
      } else {
        statsEl.style.display = "none";
      }

      refreshPreflight();

      // Update easy view if active
      if (easyMode) {
        renderEasyCards();
      }
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
    if (easyMode) {
      renderEasyCards();
    }
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

  // --- Terminal with non-copyable Korean summaries ---
  function renderTerminalWithKo(text) {
    if (!text) { outputText.textContent = ""; return; }
    // Split lines and wrap "// ..." Korean summary lines in non-selectable spans
    var container = document.getElementById("output-display");
    var pre = outputText;
    // Check if any Korean summary lines exist
    if (text.indexOf("// ") === -1) {
      pre.textContent = text;
      return;
    }
    pre.innerHTML = "";
    var lines = text.split("\n");
    lines.forEach(function (line, idx) {
      if (line.match(/^\/\/\s+.+/)) {
        // Korean summary line — non-copyable
        var span = document.createElement("span");
        span.className = "ko-summary-line";
        span.textContent = line;
        pre.appendChild(span);
      } else {
        pre.appendChild(document.createTextNode(line));
      }
      if (idx < lines.length - 1) pre.appendChild(document.createTextNode("\n"));
    });
  }

  // --- Easy Mode ---
  const easyToggle = document.getElementById("easy-toggle");
  const easyToggleLabel = document.getElementById("easy-toggle-label");
  const outputDisplay = document.getElementById("output-display");
  const easyView = document.getElementById("easy-view");
  const easyCards = document.getElementById("easy-cards");
  const easyPlaceholder = document.getElementById("easy-placeholder");
  const terminalBtnRow = document.getElementById("terminal-btn-row");
  let easyMode = false;

  // Restore saved preference
  try {
    easyMode = localStorage.getItem("ssh_easy_mode") === "true";
  } catch (e) { /* ignore */ }

  function setEasyMode(on) {
    easyMode = on;
    try { localStorage.setItem("ssh_easy_mode", on ? "true" : "false"); } catch (e) { /* ignore */ }
    easyToggle.classList.toggle("active", on);
    easyToggleLabel.textContent = on ? "Easy" : "Easy";

    if (on) {
      outputDisplay.style.display = "none";
      easyView.style.display = "block";
      terminalBtnRow.style.display = "none";
      ticketSelector.style.display = "none";
      renderEasyCards();
    } else {
      outputDisplay.style.display = "block";
      easyView.style.display = "none";
      terminalBtnRow.style.display = "flex";
      if (currentTickets.length > 0) {
        ticketSelector.style.display = "flex";
      }
    }
  }

  easyToggle.addEventListener("click", () => setEasyMode(!easyMode));

  function parseTickets(text) {
    if (!text || text === "Your split tasks will appear here..." || text === "Ready.") {
      return [];
    }

    const tickets = [];
    // Match "Ticket X -- title" pattern
    const ticketRegex = /Ticket\s+([A-Z])\s*[-—]+\s*(.+)/g;
    let match;
    const ticketPositions = [];

    while ((match = ticketRegex.exec(text)) !== null) {
      ticketPositions.push({
        letter: match[1],
        title: match[2].replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/gu, "").trim(),
        index: match.index,
      });
    }

    for (let i = 0; i < ticketPositions.length; i++) {
      const start = ticketPositions[i].index;
      const end = i + 1 < ticketPositions.length ? ticketPositions[i + 1].index : text.length;
      const block = text.substring(start, end).trim();

      // Extract model info (e.g., "[CLAUDE 85%]")
      const modelMatch = block.match(/\[([A-Z]+)\s+(\d+%)\]/);
      const model = modelMatch ? modelMatch[1] + " " + modelMatch[2] : "";

      // Extract prompt (text between ``` markers)
      const promptMatch = block.match(/```\s*\n?([\s\S]*?)```/);
      const prompt = promptMatch ? promptMatch[1].trim() : "";

      // Extract next info
      const nextMatch = block.match(/next:\s*(.+)/i);
      const nextInfo = nextMatch ? nextMatch[1].trim() : "";

      tickets.push({
        letter: ticketPositions[i].letter,
        title: ticketPositions[i].title,
        model: model,
        prompt: prompt,
        next: nextInfo,
        rawBlock: block,
      });
    }

    return tickets;
  }

  function renderEasyCards() {
    const parsed = parseTickets(currentOutput);
    easyCards.innerHTML = "";

    if (parsed.length === 0) {
      easyPlaceholder.style.display = "flex";
      easyCards.style.display = "none";
      return;
    }

    easyPlaceholder.style.display = "none";
    easyCards.style.display = "flex";

    // Build Korean summary lookup from blueprint tickets
    var koLookup = {};
    if (window._blueprintTickets) {
      window._blueprintTickets.forEach(function (t) {
        if (t.summary_ko) koLookup[t.letter] = t.summary_ko;
      });
    }

    parsed.forEach((ticket, idx) => {
      const card = document.createElement("div");
      card.className = "easy-card";
      card.style.opacity = "0";
      card.style.transform = "translateY(12px)";

      const promptDisplay = ticket.prompt || ticket.title;
      const koSummary = koLookup[ticket.letter] || "";

      card.innerHTML =
        '<div class="easy-card-header">' +
          '<div class="easy-card-badge">' +
            '<span class="easy-card-letter">' + ticket.letter + '</span>' +
            '<span class="easy-card-title">' + escapeHtml(ticket.title) + '</span>' +
          '</div>' +
          (ticket.model ? '<span class="easy-card-model">' + escapeHtml(ticket.model) + '</span>' : '') +
        '</div>' +
        '<div class="easy-card-body">' +
          (koSummary ? '<div class="easy-card-ko">' + escapeHtml(koSummary) + '</div>' : '') +
          '<div class="easy-card-prompt-label">Prompt to copy</div>' +
          '<div class="easy-card-prompt">' + escapeHtml(promptDisplay) + '</div>' +
        '</div>' +
        '<div class="easy-card-footer">' +
          (ticket.next
            ? '<span class="easy-card-next">' +
                '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
                  '<polyline points="9 18 15 12 9 6"/>' +
                '</svg>' +
                'Next: ' + escapeHtml(ticket.next) +
              '</span>'
            : '<span></span>') +
          '<button class="easy-card-copy" data-prompt="' + encodeURIComponent(promptDisplay) + '" type="button">' +
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
              '<rect x="9" y="9" width="13" height="13" rx="2"/>' +
              '<path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>' +
            '</svg>' +
            'Copy' +
          '</button>' +
        '</div>';

      easyCards.appendChild(card);

      // Staggered fade-in
      setTimeout(function () {
        card.style.transition = "opacity 0.5s var(--ease-out-quart), transform 0.5s var(--ease-out-quart)";
        card.style.opacity = "1";
        card.style.transform = "translateY(0)";
      }, idx * 80);
    });

    // Attach copy handlers
    easyCards.querySelectorAll(".easy-card-copy").forEach(function (btn) {
      btn.addEventListener("click", async function () {
        const prompt = decodeURIComponent(this.getAttribute("data-prompt"));
        try {
          await navigator.clipboard.writeText(prompt);
          this.classList.add("copied");
          this.innerHTML =
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">' +
              '<polyline points="20 6 9 17 4 12"/>' +
            '</svg>' +
            'Copied!';
          showToast("Prompt copied! Paste it into Claude.");
          var self = this;
          setTimeout(function () {
            self.classList.remove("copied");
            self.innerHTML =
              '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
                '<rect x="9" y="9" width="13" height="13" rx="2"/>' +
                '<path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>' +
              '</svg>' +
              'Copy';
          }, 2000);
        } catch (e) {
          showToast("Copy failed: " + e.message);
        }
      });
    });
  }

  function escapeHtml(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  // --- Send to Batch ---
  var btnSendBatch = document.getElementById("btn-send-batch");
  if (btnSendBatch) {
    btnSendBatch.addEventListener("click", function () {
      if (!currentOutput || currentOutput === "Your split tasks will appear here..." || currentOutput === "Ready.") {
        showToast("No tasks to send. Run Split Tasks first.");
        return;
      }
      // Parse ticket titles from output for batch input
      var ticketRegex = /Ticket\s+[A-Z]\s*[-—]+\s*(.+)/g;
      var tasks = [];
      var match;
      while ((match = ticketRegex.exec(currentOutput)) !== null) {
        var title = match[1].replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/gu, "").trim();
        if (title) tasks.push(title);
      }
      if (tasks.length === 0) {
        // Fallback: send original request
        tasks.push(requestInput.value.trim());
      }
      sessionStorage.setItem("ssh_batch_tasks", tasks.join("\n"));
      window.location.href = "/batch.html";
    });
  }

  // --- Init ---
  loadRouters();
  refreshPreflight();

  // Apply saved easy mode on load
  if (easyMode) {
    setEasyMode(true);
  }

  // Check for prompt from Prompt Library "Use in Splitter" action
  const promptFromLib = sessionStorage.getItem("ssh_prompt_use");
  if (promptFromLib) {
    requestInput.value = promptFromLib;
    sessionStorage.removeItem("ssh_prompt_use");
  }
})();
