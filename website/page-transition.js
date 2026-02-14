/* ============================================
   Page Transition — Swipe with loading screen
   "Build. Ship. Iterate."
   Reverse direction when navigating to index.html
   ============================================ */
(function () {
  "use strict";

  // --- Create swipe overlay ---
  var overlay = document.createElement("div");
  overlay.className = "swipe-overlay";
  overlay.innerHTML =
    '<div class="swipe-text">' +
      '<span class="swipe-word" style="--i:0">Build.</span>' +
      '<span class="swipe-word" style="--i:1">Ship.</span>' +
      '<span class="swipe-word" style="--i:2">Iterate.</span>' +
    "</div>";
  document.body.appendChild(overlay);

  // --- Check if arriving from swipe transition ---
  var swipeDir = sessionStorage.getItem("ssh_swipe");
  sessionStorage.removeItem("ssh_swipe");

  if (swipeDir) {
    overlay.classList.add("swipe-cover");

    var outClass = swipeDir === "reverse" ? "swipe-out-reverse" : "swipe-out";

    setTimeout(function () {
      overlay.classList.remove("swipe-cover");
      overlay.classList.add(outClass);

      overlay.addEventListener("animationend", function handler() {
        overlay.removeEventListener("animationend", handler);
        overlay.className = "swipe-overlay";
        overlay.style.visibility = "hidden";
      });
    }, 500);
  } else {
    overlay.style.visibility = "hidden";
  }

  // --- Helper: check if href points to index ---
  function isIndexPage(href) {
    var path = href.split("#")[0].split("?")[0];
    return path === "/index.html" || path === "/" || path === "index.html" ||
           path === "/index.html/";
  }

  // --- Intercept internal links ---
  var isTransitioning = false;

  document.addEventListener("click", function (e) {
    if (isTransitioning) return;

    var link = e.target.closest("a[href]");
    if (!link) return;

    var href = link.getAttribute("href");
    if (!href) return;
    if (href.indexOf("http") === 0 || href.indexOf("mailto:") === 0) return;
    if (href.charAt(0) === "#") return;
    if (link.target === "_blank") return;
    if (e.metaKey || e.ctrlKey || e.shiftKey) return;

    var currentPath = window.location.pathname;
    var linkPath = href.split("#")[0];
    if (linkPath === currentPath || linkPath === "") return;

    e.preventDefault();
    isTransitioning = true;

    var reverse = isIndexPage(href);
    var inClass = reverse ? "swipe-in-reverse" : "swipe-in";

    overlay.style.visibility = "visible";
    overlay.className = "swipe-overlay";
    // Re-trigger word animations
    overlay.offsetHeight;
    overlay.classList.add(inClass);

    sessionStorage.setItem("ssh_swipe", reverse ? "reverse" : "normal");

    var safetyTimeout = setTimeout(function () {
      window.location.href = href;
    }, 2000);

    overlay.addEventListener("animationend", function handler() {
      overlay.removeEventListener("animationend", handler);
      clearTimeout(safetyTimeout);

      setTimeout(function () {
        window.location.href = href;
      }, 300);
    });
  });

  // --- Handle bfcache ---
  window.addEventListener("pageshow", function (e) {
    if (e.persisted) {
      isTransitioning = false;
      overlay.className = "swipe-overlay";
      overlay.style.visibility = "hidden";
    }
  });
})();
