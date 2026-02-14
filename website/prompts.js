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

  let prompts = [];
  let activeCategory = "all";

  async function loadPrompts() {
    try {
      const res = await fetch("/api/prompts");
      const data = await res.json();
      prompts = data.prompts || [];
      renderGrid();
    } catch (e) {
      // If API not available, use localStorage fallback
      const stored = localStorage.getItem("ssh_prompts");
      prompts = stored ? JSON.parse(stored) : getDefaults();
      renderGrid();
    }
  }

  function getDefaults() {
    return [
      { id: "1", name: "Login Page with OAuth", category: "feature", content: "Build a login page with the following requirements:\n- Email/password authentication\n- Google OAuth integration\n- Remember me checkbox\n- Forgot password link\n- Mobile-responsive design\n- Input validation with error messages" },
      { id: "2", name: "REST API Endpoint", category: "api", content: "Create a REST API endpoint for [RESOURCE]:\n- GET /api/[resource] - List all\n- GET /api/[resource]/:id - Get one\n- POST /api/[resource] - Create\n- PUT /api/[resource]/:id - Update\n- DELETE /api/[resource]/:id - Delete\n- Input validation and error handling\n- Rate limiting" },
      { id: "3", name: "Component Refactor", category: "refactor", content: "Refactor the [COMPONENT] component:\n- Extract shared logic into custom hooks\n- Break into smaller sub-components\n- Add TypeScript types\n- Improve error handling\n- Ensure backward compatibility" },
      { id: "4", name: "Dark Mode Toggle", category: "ui", content: "Add dark mode to the application:\n- Toggle switch in settings/header\n- CSS variables for theme colors\n- Persist preference in localStorage\n- Respect system preference\n- Smooth transition animation" },
      { id: "5", name: "Fix Memory Leak", category: "bugfix", content: "Debug and fix the memory leak in [COMPONENT]:\n1. Identify the source of the leak\n2. Check for uncleaned event listeners\n3. Check for uncleaned timers/intervals\n4. Verify useEffect cleanup functions\n5. Test memory usage before and after fix" },
    ];
  }

  async function savePrompts() {
    try {
      await fetch("/api/prompts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompts: prompts }),
      });
    } catch (e) {
      // Fallback to localStorage
      localStorage.setItem("ssh_prompts", JSON.stringify(prompts));
    }
  }

  function renderGrid() {
    const grid = document.getElementById("prompt-grid");
    const search = document.getElementById("search-input").value.toLowerCase().trim();

    const filtered = prompts.filter((p) => {
      if (activeCategory !== "all" && p.category !== activeCategory) return false;
      if (search && !p.name.toLowerCase().includes(search) && !p.content.toLowerCase().includes(search)) return false;
      return true;
    });

    if (!filtered.length) {
      grid.innerHTML = '<div class="empty-state"><h3>No prompts found</h3><p>Create a new prompt or adjust your filters.</p></div>';
      return;
    }

    grid.innerHTML = "";
    filtered.forEach((p) => {
      const card = document.createElement("div");
      card.className = "prompt-card";
      card.innerHTML =
        '<div class="prompt-card-header">' +
        "<h4>" + escapeHtml(p.name) + "</h4>" +
        '<span class="prompt-category">' + p.category + "</span>" +
        "</div>" +
        '<div class="prompt-body">' + escapeHtml(p.content) + "</div>" +
        '<div class="prompt-actions">' +
        '<button class="btn" data-action="copy" data-id="' + p.id + '">Copy</button>' +
        '<button class="btn" data-action="use" data-id="' + p.id + '">Use in Splitter</button>' +
        '<button class="btn" data-action="edit" data-id="' + p.id + '">Edit</button>' +
        '<button class="btn" data-action="delete" data-id="' + p.id + '">Del</button>' +
        "</div>";
      grid.appendChild(card);
    });

    // Action handlers
    grid.querySelectorAll("[data-action]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const id = btn.dataset.id;
        const action = btn.dataset.action;
        const prompt = prompts.find((p) => p.id === id);
        if (!prompt) return;

        if (action === "copy") {
          navigator.clipboard.writeText(prompt.content).then(() => showToast("Copied!"))
            .catch((err) => showToast("Copy failed: " + err.message));
        } else if (action === "use") {
          // Redirect to splitter with prompt content
          sessionStorage.setItem("ssh_prompt_use", prompt.content);
          window.location.href = "/router.html";
        } else if (action === "edit") {
          openModal(prompt);
        } else if (action === "delete") {
          prompts = prompts.filter((p) => p.id !== id);
          savePrompts();
          renderGrid();
          showToast("Deleted");
        }
      });
    });
  }

  function openModal(prompt) {
    const overlay = document.getElementById("modal-overlay");
    document.getElementById("modal-title").textContent = prompt ? "Edit Prompt" : "New Prompt";
    document.getElementById("prompt-name").value = prompt ? prompt.name : "";
    document.getElementById("prompt-category").value = prompt ? prompt.category : "feature";
    document.getElementById("prompt-content").value = prompt ? prompt.content : "";
    document.getElementById("prompt-edit-id").value = prompt ? prompt.id : "";
    overlay.classList.add("open");
  }

  function closeModal() {
    document.getElementById("modal-overlay").classList.remove("open");
  }

  function saveFromModal() {
    const name = document.getElementById("prompt-name").value.trim();
    const category = document.getElementById("prompt-category").value;
    const content = document.getElementById("prompt-content").value.trim();
    const editId = document.getElementById("prompt-edit-id").value;

    if (!name || !content) { showToast("Name and content are required"); return; }

    if (editId) {
      const idx = prompts.findIndex((p) => p.id === editId);
      if (idx >= 0) {
        prompts[idx] = { ...prompts[idx], name, category, content };
      }
    } else {
      prompts.push({
        id: Date.now().toString(),
        name,
        category,
        content,
      });
    }

    savePrompts();
    renderGrid();
    closeModal();
    showToast(editId ? "Updated" : "Created");
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // Category tabs
  document.getElementById("category-tabs").addEventListener("click", (e) => {
    if (!e.target.classList.contains("cat-tab")) return;
    document.querySelectorAll(".cat-tab").forEach((t) => t.classList.remove("active"));
    e.target.classList.add("active");
    activeCategory = e.target.dataset.cat;
    renderGrid();
  });

  function debounce(fn, ms) {
    let timer;
    return function () {
      var args = arguments;
      var ctx = this;
      clearTimeout(timer);
      timer = setTimeout(function () { fn.apply(ctx, args); }, ms);
    };
  }

  document.getElementById("search-input").addEventListener("input", debounce(renderGrid, 300));
  document.getElementById("btn-new").addEventListener("click", () => openModal(null));
  document.getElementById("btn-cancel").addEventListener("click", closeModal);
  document.getElementById("btn-save").addEventListener("click", saveFromModal);
  document.getElementById("modal-overlay").addEventListener("click", (e) => {
    if (e.target === e.currentTarget) closeModal();
  });

  loadPrompts();
})();
