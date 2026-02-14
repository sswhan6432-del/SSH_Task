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

  let feedbackData = {};
  let historyEntries = [];

  async function loadData() {
    try {
      const [fbRes, histRes] = await Promise.all([
        fetch("/api/feedback"),
        fetch("/api/history"),
      ]);
      if (!fbRes.ok || !histRes.ok) throw new Error("API error");
      const fbData = await fbRes.json();
      const histData = await histRes.json();
      feedbackData = fbData.feedback || {};
      historyEntries = (histData.entries || []).reverse();
      render();
    } catch (e) {
      feedbackData = JSON.parse(localStorage.getItem("ssh_feedback") || "{}");
      document.getElementById("feedback-list").innerHTML =
        '<div class="empty-state"><h3>Cannot load history</h3><p>Make sure the server is running.</p></div>';
    }
  }

  async function saveFeedback(entryId, vote, comment) {
    feedbackData[entryId] = { vote, comment: comment || "", timestamp: new Date().toISOString() };
    try {
      await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ feedback: feedbackData }),
      });
    } catch (e) {
      localStorage.setItem("ssh_feedback", JSON.stringify(feedbackData));
    }
    renderStats();
  }

  function render() {
    renderStats();
    renderList();
  }

  function renderStats() {
    const entries = Object.values(feedbackData);
    const total = entries.length;
    const positive = entries.filter((f) => f.vote === "up").length;
    const comments = entries.filter((f) => f.comment).length;
    const rate = total > 0 ? Math.round((positive / total) * 100) : 0;

    document.getElementById("total-feedback").textContent = total;
    document.getElementById("positive-rate").textContent = total > 0 ? rate + "%" : "N/A";
    document.getElementById("total-comments").textContent = comments;

    const fill = document.getElementById("accuracy-fill");
    fill.style.width = (total > 0 ? rate : 0) + "%";
    fill.textContent = total > 0 ? rate + "%" : "No data";
    fill.className = "acc-bar-fill " + (rate >= 80 ? "good" : rate >= 50 ? "medium" : "low");
  }

  function renderList() {
    const container = document.getElementById("feedback-list");
    const recent = historyEntries.slice(0, 30);

    if (!recent.length) {
      container.innerHTML = '<div class="empty-state"><h3>No routing sessions yet</h3><p>Use the Task Splitter first, then come back to rate results.</p></div>';
      return;
    }

    container.innerHTML = "";
    recent.forEach((entry, i) => {
      const entryId = entry.timestamp || "entry-" + i;
      const fb = feedbackData[entryId] || {};
      const tasks = entry.tasks || [{ route: entry.route || "unknown", summary: entry.request || "" }];
      const route = entry.route || tasks[0].route || "unknown";
      const request = entry.request || tasks.map((t) => t.summary || "").join(", ") || "(no request)";
      const ts = entry.timestamp ? new Date(entry.timestamp).toLocaleString() : "N/A";

      const card = document.createElement("div");
      card.className = "fb-card";

      card.innerHTML =
        '<div class="fb-vote">' +
        '<button class="vote-btn up' + (fb.vote === "up" ? " active" : "") + '" data-id="' + escapeAttr(entryId) + '" data-vote="up" title="Good routing" aria-label="Rate positive">+</button>' +
        '<button class="vote-btn down' + (fb.vote === "down" ? " active" : "") + '" data-id="' + escapeAttr(entryId) + '" data-vote="down" title="Bad routing" aria-label="Rate negative">-</button>' +
        "</div>" +
        '<div class="fb-content">' +
        "<h4>" + escapeHtml(request.substring(0, 120)) + (request.length > 120 ? "..." : "") + "</h4>" +
        '<div class="fb-meta">' +
        '<span class="route-badge ' + route + '">' + route + "</span>" +
        "<span>" + tasks.length + " task(s)</span>" +
        "<span>" + ts + "</span>" +
        "</div>" +
        '<div class="comment-input" id="comment-' + i + '">' +
        '<textarea placeholder="Why was this routing wrong? (optional)"></textarea>' +
        '<button class="btn" data-save="' + escapeAttr(entryId) + '" data-idx="' + i + '">Save Comment</button>' +
        "</div>" +
        (fb.comment ? '<p style="margin-top:6px;font-size:12px;color:#666;font-style:italic;">"' + escapeHtml(fb.comment) + '"</p>' : "") +
        "</div>";

      container.appendChild(card);
    });

    // Vote handlers
    container.querySelectorAll(".vote-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const id = btn.dataset.id;
        const vote = btn.dataset.vote;
        const existing = feedbackData[id];

        // Toggle
        if (existing && existing.vote === vote) {
          delete feedbackData[id];
          saveFeedback(id, null);
          btn.classList.remove("active");
        } else {
          saveFeedback(id, vote, existing ? existing.comment : "");
          // Update UI
          const parent = btn.closest(".fb-vote");
          parent.querySelectorAll(".vote-btn").forEach((b) => b.classList.remove("active"));
          btn.classList.add("active");

          // Show comment input for downvotes
          if (vote === "down") {
            const card = btn.closest(".fb-card");
            const commentDiv = card.querySelector(".comment-input");
            if (commentDiv) commentDiv.style.display = "block";
          }
        }
        showToast(vote === "up" ? "Rated positive" : vote === "down" ? "Rated negative" : "Rating removed");
      });
    });

    // Comment save handlers
    container.querySelectorAll("[data-save]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = btn.dataset.save;
        const idx = btn.dataset.idx;
        const textarea = document.getElementById("comment-" + idx).querySelector("textarea");
        const comment = textarea.value.trim();
        const existing = feedbackData[id] || {};
        saveFeedback(id, existing.vote || "down", comment);
        showToast("Comment saved");
      });
    });
  }

  function exportFeedback() {
    const entries = Object.entries(feedbackData);
    if (!entries.length) { showToast("No feedback to export"); return; }

    let csv = "Entry_ID,Vote,Comment,Timestamp\n";
    entries.forEach(([id, fb]) => {
      csv += '"' + id + '",' + (fb.vote || "") + ',"' + (fb.comment || "").replace(/"/g, '""') + '",' + (fb.timestamp || "") + "\n";
    });

    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "feedback_export.csv";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast("Feedback exported!");
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function escapeAttr(str) {
    return str.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  document.getElementById("btn-refresh").addEventListener("click", () => { loadData(); showToast("Refreshed"); });
  document.getElementById("btn-export").addEventListener("click", exportFeedback);

  loadData();
})();
