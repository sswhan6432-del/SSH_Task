/* ============================================
   Supabase Client Configuration
   Loaded on every page before auth.js
   ============================================ */

(function () {
  "use strict";

  // ---- CONFIGURE THESE VALUES ----
  // Replace with your Supabase project URL and anon key
  var SUPABASE_URL = "https://afllgwpxiglzhphrqizg.supabase.co";
  var SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFmbGxnd3B4aWdsemhwaHJxaXpnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzAxODU4MDksImV4cCI6MjA4NTc2MTgwOX0.228gioeVfDimCoXm9h2D71dXMX8GdoXRBQhMoNgUZj0";

  // Allow overriding via meta tags in HTML
  var metaUrl = document.querySelector('meta[name="supabase-url"]');
  var metaKey = document.querySelector('meta[name="supabase-anon-key"]');
  if (metaUrl) SUPABASE_URL = metaUrl.content;
  if (metaKey) SUPABASE_ANON_KEY = metaKey.content;

  if (SUPABASE_URL === "YOUR_SUPABASE_URL" || SUPABASE_ANON_KEY === "YOUR_SUPABASE_ANON_KEY") {
    console.warn("[Supabase] Not configured. Set URL and anon key in supabase-config.js or via meta tags.");
  }

  // Initialize Supabase client (supabase-js v2 loaded via CDN)
  if (typeof supabase !== "undefined" && supabase.createClient) {
    window.supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
  } else {
    console.error("[Supabase] supabase-js not loaded. Ensure the CDN script is included before this file.");
    window.supabaseClient = null;
  }
})();
