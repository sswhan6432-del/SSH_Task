# Debug Log

## 2026-02-13: Split Tasks Button Not Working

### Symptoms
- "Split Tasks" button click produces no response
- "Advanced Settings (for experts)" section does not toggle
- All buttons on `router.html` completely non-functional

### Root Cause
`router.js` referenced 3 DOM elements that do not exist in `router.html`, causing a **TypeError that halted the entire JS execution**:

1. **`configToggle` (id="config-toggle")** — Line 44: `null.addEventListener("click", ...)` → TypeError → **JS execution stopped here**
   - HTML uses `<details>` tag (native toggle), so no JS toggle needed
2. **`configArrow` (id="config-arrow")** — Also null, referenced in same block
3. **`btn-copy-request`, `btn-copy-output`** — Lines 243-248: Referenced buttons that don't exist in HTML

Additionally, hidden `<input type="hidden">` elements were accessed with `.checked` instead of `.value`:
- `opt-desktop-edit`, `opt-opus-only`, `opt-tickets-md`, `opt-translate` — `.checked` returns `undefined` on hidden inputs

### Fix Applied (`router.js`)

```diff
- const configToggle = document.getElementById("config-toggle");
- const configBody = document.getElementById("config-body");
- const configArrow = document.getElementById("config-arrow");
+ const configBody = document.getElementById("config-body");

- configToggle.addEventListener("click", () => {
-   configBody.classList.toggle("open");
-   configArrow.classList.toggle("open");
- });
- configBody.classList.add("open");
- configArrow.classList.add("open");
+ // <details> handles toggle natively, no JS needed

- desktop_edit: document.getElementById("opt-desktop-edit").checked,
+ desktop_edit: document.getElementById("opt-desktop-edit").value === "true",
  (same pattern for opt-opus-only, opt-tickets-md, opt-translate)

- document.getElementById("btn-copy-request").addEventListener(...)
- document.getElementById("btn-copy-output").addEventListener(...)
  (removed — buttons don't exist in HTML)
```

### Additional Fix (`web_server.py`)
Added `Cache-Control` headers to prevent browser caching stale JS:

```python
def end_headers(self):
    self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
    self.send_header("Pragma", "no-cache")
    self.send_header("Expires", "0")
    super().end_headers()
```

### Debugging Process
1. Read `router.html` and `router.js` — found HTML/JS DOM mismatch
2. Fixed 3 JS errors, verified with `node --check`
3. Tested API with `curl` — all endpoints working (`/api/routers`, `/api/route`)
4. Browser still not working — identified **browser cache** as secondary issue
5. Added cache-busting headers to `web_server.py`
6. **Headless browser test with Playwright** confirmed full functionality:
   - Page loads, router auto-detected, button click works, 20 tickets generated, 0 JS errors

### Key Lesson
- A single `null.addEventListener()` in strict mode **halts the entire IIFE**, preventing all subsequent event listeners from registering
- Always use null-checks (`if (el) el.addEventListener(...)`) or ensure HTML and JS DOM references are in sync
- Browser cache can persist old broken JS even after server-side fixes — use `Cache-Control: no-cache` headers during development
- When debugging browser issues from CLI, **Playwright headless testing** is the most reliable method
