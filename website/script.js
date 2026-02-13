/* ============================================
   Apple-Style Portfolio — JavaScript
   ============================================ */

(function () {
  "use strict";

  // --- Scroll fade-in (Intersection Observer) ---
  const fadeEls = document.querySelectorAll(".fade-in");
  if (fadeEls.length) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15 }
    );
    fadeEls.forEach((el) => observer.observe(el));
  }

  // --- Nav scroll effect ---
  const nav = document.getElementById("nav");
  const scrollIndicator = document.getElementById("scroll-indicator");
  let ticking = false;

  function onScroll() {
    if (!ticking) {
      requestAnimationFrame(() => {
        const y = window.scrollY;
        nav.classList.toggle("scrolled", y > 10);

        if (scrollIndicator) {
          scrollIndicator.classList.toggle("hidden", y > 100);
        }

        updateActiveLink(y);
        ticking = false;
      });
      ticking = true;
    }
  }

  window.addEventListener("scroll", onScroll, { passive: true });

  // --- Active nav link highlighting ---
  const sections = document.querySelectorAll("section[id]");
  const navAnchors = document.querySelectorAll(".nav-links a");

  function updateActiveLink(scrollY) {
    let current = "";
    sections.forEach((section) => {
      const top = section.offsetTop - 100;
      if (scrollY >= top) {
        current = section.getAttribute("id");
      }
    });
    navAnchors.forEach((a) => {
      a.classList.toggle("active", a.getAttribute("href") === "#" + current);
    });
  }

  // --- Mobile menu toggle ---
  const toggle = document.getElementById("nav-toggle");
  const mobileMenu = document.getElementById("mobile-menu");

  if (toggle && mobileMenu) {
    toggle.addEventListener("click", () => {
      toggle.classList.toggle("open");
      mobileMenu.classList.toggle("open");
      document.body.style.overflow = mobileMenu.classList.contains("open")
        ? "hidden"
        : "";
    });

    mobileMenu.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        toggle.classList.remove("open");
        mobileMenu.classList.remove("open");
        document.body.style.overflow = "";
      });
    });
  }

  // --- Hero stagger (already CSS, but ensure visible after load) ---
  document.querySelectorAll(".hero-line").forEach((el) => {
    el.style.willChange = "opacity, transform";
  });

  // --- Trigger initial scroll state ---
  onScroll();
})();
