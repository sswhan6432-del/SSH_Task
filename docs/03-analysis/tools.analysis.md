---
template: analysis
version: 1.2
description: LLM Router Gap Analysis - Design vs Implementation
variables:
  - feature: tools (LLM Router)
  - date: 2026-02-13
  - author: gap-detector
  - project: LLM Router
  - version: 4.0
---

# LLM Router (tools) Analysis Report

> **Analysis Type**: Gap Analysis (Design vs Implementation)
>
> **Project**: LLM Router (AI Task Splitter)
> **Version**: 4.0
> **Analyst**: gap-detector
> **Date**: 2026-02-13
> **Design Doc**: [tools.design.md](../02-design/features/tools.design.md)

### Pipeline References

| Phase | Document | Verification Target |
|-------|----------|---------------------|
| Phase 2 | N/A (Python PEP8) | Convention compliance |
| Phase 4 | Design Section 4 | API implementation match |
| Phase 8 | This document | Architecture/Convention review |

---

## 1. Analysis Overview

### 1.1 Analysis Purpose

Verify that the actual implementation of LLM Router v4.0 matches the design document
(`docs/02-design/features/tools.design.md`). This is the **Check** phase of the PDCA cycle,
performed as reverse documentation gap analysis since the design was written after implementation.

### 1.2 Analysis Scope

- **Design Document**: `docs/02-design/features/tools.design.md`
- **Implementation Files**:
  - `/Users/songseunghwan/Desktop/tools/llm_router.py` (596 lines)
  - `/Users/songseunghwan/Desktop/tools/router_gui.py` (1259 lines)
  - `/Users/songseunghwan/Desktop/tools/web_server.py` (367 lines)
  - `/Users/songseunghwan/Desktop/tools/website/router.html` (148 lines)
  - `/Users/songseunghwan/Desktop/tools/website/router.js` (277 lines)
  - `/Users/songseunghwan/Desktop/tools/website/router.css` (528 lines)
- **Analysis Date**: 2026-02-13

---

## 2. Gap Analysis (Design vs Implementation)

### 2.1 API Endpoints (Section 4)

| Design Endpoint | Implementation | Status | Notes |
|----------------|---------------|--------|-------|
| GET `/` (serve router.html) | `web_server.py:124-125` | Match | Redirects `/` to `/router.html` |
| GET `/api/routers` | `web_server.py:118-119` | Match | Returns router list with path/name/rel |
| GET `/api/preflight` | `web_server.py:120-121` | Match | Returns git status + groq_key boolean |
| POST `/api/route` | `web_server.py:132-133` | Partial | See 2.1.1 below |
| POST `/api/extract-block` | `web_server.py:134-135` | Partial | See 2.1.2 below |

#### 2.1.1 POST `/api/route` -- Differences

| Aspect | Design | Implementation | Status |
|--------|--------|----------------|--------|
| Request body `flags` object | Nested `{ "flags": { "economy": ... } }` | Flat: `{ "economy": ..., "friendly": ... }` | Changed |
| Response field `ticket_ids` | `"ticket_ids": ["A", "B"]` | `"tickets": ["A", "B"]` | Changed |
| Response field `success` | `"success": true` | Not present (implied by empty `error`) | Changed |
| Extra response field | Not specified | `"translate_status": "ok"` | Extra |
| Extra request fields | Not specified | `translate_en`, `ticket_groq_translate`, `desktop_edit`, `opus_only`, `tickets_md`, `save_tickets`, `min_tickets` | Extra |
| Error response status code | 500 | 400 (for validation errors) | Changed |

#### 2.1.2 POST `/api/extract-block` -- Differences

| Aspect | Design | Implementation | Status |
|--------|--------|----------------|--------|
| Request field `translate` | `"translate": true` | `"translate_groq": true` | Changed |
| Extra request field | Not specified | `"append_rules": true` | Extra |
| Response includes `success` | `"success": true` | Matches | Match |
| Response includes `error` | `"error": null` | Matches | Match |

### 2.2 Data Model (Section 3)

#### 2.2.1 TaskDecision

| Field | Design Type | Implementation (`llm_router.py:37-46`) | Status |
|-------|-------------|---------------------------------------|--------|
| `id` | str | str | Match |
| `summary` | str | str | Match |
| `route` | str | str | Match |
| `confidence` | float | float | Match |
| `priority` | int | int | Match |
| `reasons` | List[str] | List[str] | Match |
| `claude_prompt` | str | str | Match |
| `next_session_starter` | str | str | Match |
| `change_log_stub` | str | str | Match |

**Score: 9/9 fields match (100%)**

#### 2.2.2 RouterOutput

| Field | Design Type | Implementation (`llm_router.py:49-55`) | Status |
|-------|-------------|---------------------------------------|--------|
| `route` | str | str | Match |
| `confidence` | float | float | Match |
| `reasons` | List[str] | List[str] | Match |
| `global_notes` | List[str] | List[str] | Match |
| `session_guard` | List[str] | List[str] | Match |
| `tasks` | List[TaskDecision] | List[TaskDecision] | Match |

**Score: 6/6 fields match (100%)**

#### 2.2.3 Task History Schema

| Field | Design | Implementation (`llm_router.py:78-86`) | Status |
|-------|--------|---------------------------------------|--------|
| `timestamp` | ISO 8601 string | `datetime.now().isoformat()` | Match |
| `id` | str | str | Match |
| `summary` | str | str | Match |
| `priority` | int | int | Match |
| `route` | str | str | Match |
| `confidence` | float | float | Match |
| `reasons` | List[str] | List[str] | Match |

**Score: 7/7 fields match (100%)**

#### 2.2.4 State Management

| Design Statement | Implementation | Status |
|-----------------|----------------|--------|
| Stateless Core: pure functions | `llm_router.py` uses no global mutable state | Match |
| GUI State: Tkinter widgets | `router_gui.py:807-823` uses Tk variables | Match |
| History Log: append-only JSON | `llm_router.py:62-89` reads/appends/writes | Match |
| No Database | No DB imports or connections found | Match |

**Score: 4/4 (100%)**

### 2.3 CLI Interface (Section 4.4)

| Flag | Design | Implementation (`llm_router.py:507-595`) | Status |
|------|--------|------------------------------------------|--------|
| `--desktop-edit` | Listed | Line 511 | Match |
| `--economy strict\|balanced` | Listed | Lines 517-520 | Match |
| `--phase analyze\|implement` | Listed | Lines 522-525 | Match |
| `--one-task B` | Listed | Line 527 | Match |
| `--save-tickets FILE` | Listed | Line 528 | Match |
| `--friendly` | Listed | Line 514 | Match |
| `--force-split` | Listed | Line 515 | Match |
| `--min-tickets N` | Listed | Lines 536-540 | Match |
| `--max-tickets N` | Listed | Lines 530-534 | Match |
| `--merge "A+B"` | Listed | Line 542 | Match |
| `--json` | Not in design Section 4.4 | Line 510 | Extra |
| `--tickets-md` | Not in design Section 4.4 | Line 513 | Extra |
| `--opus-only` | Not in design Section 4.4 | Line 512 | Extra |

**Score: 10/10 designed flags present + 3 extra**

### 2.4 Component Details (Section 2.2)

| Component | Design Lines | Actual Lines | Status | Notes |
|-----------|:----------:|:----------:|--------|-------|
| `llm_router.py` | 595 | 596 | Match | 1 line difference (negligible) |
| `router_gui.py` | 1258 | 1259 | Match | 1 line difference (negligible) |
| `web_server.py` | 366 | 367 | Match | 1 line difference (negligible) |
| `website/router.html` | ~150 | 148 | Match | Close approximation |
| `website/router.js` | ~250 | 277 | Match | Close approximation |
| `website/router.css` | ~250 | 528 | Partial | Actual is 2x the estimate |

### 2.5 UI/UX Design (Section 5)

#### 2.5.1 GUI Layout (Section 5.1)

| Design Element | Implementation | Status |
|---------------|----------------|--------|
| Title "LLM Router GUI v2.0" | `router_gui.py:9` `APP_TITLE = "LLM Router GUI v2.0"` | Match |
| Router selector dropdown | `router_gui.py:888-898` | Match |
| Refresh button | `router_gui.py:898` | Match |
| Git status display | `router_gui.py:901-902` (Preflight label) | Match |
| Request text area | `router_gui.py:942-944` | Match |
| Flag panel (Friendly, Desktop, Economy, Phase) | `router_gui.py:907-923` | Match |
| Force Split checkbox | `router_gui.py:909` | Match |
| Run Router button | `router_gui.py:948` | Match |
| Output display area | `router_gui.py:957-959` | Match |
| Copy Claude Block button | `router_gui.py:953` | Match |
| Clear Output button | `router_gui.py:955` | Match |
| Opus-Only checkbox | Not in design layout | `router_gui.py:910` | Extra |
| Tickets Markdown checkbox | Not in design layout | `router_gui.py:911` | Extra |
| Translate output checkbox | Not in design layout | `router_gui.py:912` | Extra |
| Translate Tickets via Groq checkbox | Not in design layout | `router_gui.py:913` | Extra |
| Min tickets input | Not in design layout | `router_gui.py:922-923` | Extra |
| One task input | Not in design layout | `router_gui.py:925-926` | Extra |
| Max tickets input | Not in design layout | `router_gui.py:928-929` | Extra |
| Merge input | Not in design layout | `router_gui.py:931-933` | Extra |
| Save tickets input | Not in design layout | `router_gui.py:935-937` | Extra |
| Browse button (router file) | Not in design layout | `router_gui.py:897` | Extra |
| Copy Request button | Not in design layout | `router_gui.py:950` | Extra |
| Clear Input button | Not in design layout | `router_gui.py:951` | Extra |
| Copy Full Output button | Not in design layout | `router_gui.py:954` | Extra |
| Context menu (right-click) | Not in design | `router_gui.py:830-863` | Extra |
| Startup banner | Not in design | `router_gui.py:978-985` | Extra |

#### 2.5.2 Web UI Layout (Section 5.2)

| Design Element | Implementation | Status |
|---------------|----------------|--------|
| Title "AI Task Splitter" | `router.html:42` | Match |
| Request input textarea | `router.html:68` | Match |
| Friendly Mode checkbox | `router.html:109` | Match |
| Force Split checkbox | `router.html:112` | Match |
| Economy selector | `router.html:126` (hidden) | Partial |
| Route Tasks / Split Tasks button | `router.html:70-72` "Split Tasks" | Changed |
| Results output area | `router.html:86-88` | Match |
| Per-task Copy button | `router.html:90` "Copy This Task" (single) | Partial |
| Navigation bar | Not in design | `router.html:14-26` | Extra |
| Mobile menu | Not in design | `router.html:29-34` | Extra |
| How-it-works section | Not in design | `router.html:47-63` | Extra |
| Advanced Settings (details) | Not in design | `router.html:96-119` | Extra |
| Auto-translate checkbox | Not in design | `router.html:115` | Extra |
| Ticket selector dropdown | Not in design | `router.html:81-84` | Extra |
| Loading overlay | Not in design | `router.html:140-143` | Extra |
| Toast notification | Not in design | `router.html:137` | Extra |
| Hidden config fields | Not in design | `router.html:122-132` | Extra |

#### 2.5.3 User Flow (Section 5.3)

| Flow Step (GUI) | Implementation | Status |
|----------------|----------------|--------|
| Launch router_gui.py | `router_gui.py:1256-1258` | Match |
| Select router (if multiple) | Dropdown + Browse | Match |
| Enter request + set flags | Text area + checkboxes | Match |
| Click "Run Router" | Button present | Match |
| Select ticket (A/B/C) | `simpledialog` popup on Copy | Match |
| Click "Copy Claude Block" | Button present | Match |
| Paste into Claude | User action (clipboard) | Match |

| Flow Step (Web) | Implementation | Status |
|----------------|----------------|--------|
| Start web_server.py | `web_server.py:344-366` | Match |
| Open localhost:8080 | Default port 8080 | Match |
| Enter request | Textarea present | Match |
| Click "Route Tasks" | "Split Tasks" button | Changed |
| Click "Copy" on desired task | Single "Copy This Task" button | Partial |
| Paste into Claude | User action (clipboard) | Match |

| Flow Step (CLI) | Implementation | Status |
|----------------|----------------|--------|
| Run llm_router.py "request" | `main()` function | Match |
| View output in terminal | stdout output | Match |
| Copy desired ticket manually | User action | Match |

### 2.6 Key Components Table (Section 5.4)

| Component | Design Reference | Implementation | Status |
|-----------|-----------------|----------------|--------|
| Router Selector | `find_router_candidates()` | `router_gui.py:11-41` | Match |
| Request Input | Tkinter Text widget | `router_gui.py:943-944` | Match |
| Flag Panel | Checkboxes + Combobox | `router_gui.py:904-937` | Match |
| Output Display | Text widget (readonly) | `router_gui.py:958-959` | Partial (not readonly) |
| Ticket Selector | `detect_ticket_ids()` | `router_gui.py:513-534` | Match |
| Claude Block Extractor | `extract_claude_ready_block_from_output()` | `router_gui.py:536-674` | Match |
| Ticket Slicer | `slice_single_ticket_from_block()` | `router_gui.py:724-785` | Match |
| Translator | `rewrite_tickets_to_english_via_groq()` | `router_gui.py:371-425` | Match |

**Score: 7/8 match, 1 partial**

### 2.7 Error Handling (Section 6)

#### 2.7.1 Error Categories

| Category | Design | Implementation | Status |
|----------|--------|----------------|--------|
| **Input Errors** (empty request) | Show warning | GUI: `messagebox.showwarning` (`router_gui.py:1062-1063`), Web: returns 400 (`web_server.py:196`) | Match |
| **Router Errors** (not found) | Display stderr, log | GUI: `messagebox.showerror` (`router_gui.py:1054-1058`), Web: returns 400 (`web_server.py:194`) | Match |
| **Parsing Errors** (no tickets) | Return full output as fallback | Block extractor has multi-level fallback (`router_gui.py:627-674`) | Match |
| **API Errors** (Groq timeout) | Warn user, skip | `llm_router.py:255-257`, `router_gui.py:174-175` | Match |
| **System Errors** (permission) | Show error dialog | GUI: `try/except` in `run_router` (`router_gui.py:1145-1149`) | Match |

#### 2.7.2 Error Response Format (API)

| Design Format | Implementation | Status |
|--------------|----------------|--------|
| `{ success: false, output: "", ticket_ids: [], error: "..." }` | `{ error: "...", output: "", tickets: [] }` (no `success` field for route) | Changed |
| extract-block: `{ success: false, block: "", error: "..." }` | `{ block: "", success: false }` | Match |

#### 2.7.3 Fallback Strategies

| Strategy | Design | Implementation | Status |
|----------|--------|----------------|--------|
| Task Extraction Failure -> single task | Specified | `llm_router.py:254,266` returns `[text]` | Match |
| Translation Failure -> original Korean | Specified | `router_gui.py:174-175` returns `text` | Match |
| Ticket Parsing Failure -> entire block | Specified | `router_gui.py:664-672` global fallback | Match |
| Change Log Stub Missing -> inject default | Specified | `llm_router.py:312-313` returns empty string | Partial |
| Groq API Unavailable -> local parsing | Specified | `llm_router.py:242-244` warns and returns `[text]` | Match |

**Score: 4/5 match, 1 partial (change_log_stub returns empty instead of default)**

### 2.8 Dependencies (Section 2.4)

| Component | Design Internal Deps | Actual Imports | Status |
|-----------|---------------------|----------------|--------|
| `llm_router.py` | None | stdlib only (re, json, sys, os, datetime, urllib, dataclasses, typing) | Match |
| `router_gui.py` | `llm_router.py` | Does NOT import `llm_router.py` directly | Changed |
| `web_server.py` | `router_gui.py` | `from router_gui import ...` (`web_server.py:35-51`) | Match |
| Groq API | `llm_router.py` | Both `llm_router.py:167-198` and `router_gui.py:249-281` have Groq client | Changed |

**Important finding:** `router_gui.py` does NOT import from `llm_router.py`. Instead, it has
its own duplicate `_groq_chat()` function (`router_gui.py:253-281`) and calls `llm_router.py`
only via `subprocess.run()` (`router_gui.py:1146`). The design states `router_gui.py` imports
from `llm_router.py`, but the actual dependency is process-level, not module-level.

### 2.9 Security (Section 7)

| Item | Design Status | Implementation | Status |
|------|:------------:|----------------|--------|
| No Credential Storage (env only) | Checked | `os.environ.get("GROQ_API_KEY")` throughout | Match |
| No Command Injection (list args) | Checked | `subprocess.run(cmd, ...)` with list args | Match |
| No XSS (browser handles) | Checked | Web UI uses `textContent` not `innerHTML` (`router.js:166`) | Match |
| CORS Protection | Not implemented | Not implemented | Match |
| Rate Limiting | Not implemented | Not implemented | Match |
| Safe Parsing (no eval) | Checked | Regex-based parsing, `json.loads` only | Match |

**Score: 6/6 match**

---

## 3. Code Quality Analysis

### 3.1 Complexity Analysis

| File | Function | Approx Lines | Status | Notes |
|------|----------|:------------:|--------|-------|
| `router_gui.py` | `extract_claude_ready_block_from_output` | 139 | High complexity | 4 nested strategies, multiple fallbacks |
| `router_gui.py` | `copy_claude_block` | 67 | Moderate | Multi-step extraction pipeline |
| `router_gui.py` | `run_router` | 120 | Moderate | Command building + execution |
| `router_gui.py` | `translate_output_via_groq` | 90 | Moderate | 5-phase translation pipeline |
| `llm_router.py` | `route_text` | 58 | Good | Clear linear flow |
| `web_server.py` | `_api_extract_block` | 60 | Moderate | Multiple translation passes |

### 3.2 Code Duplication

| Type | Location A | Location B | Description |
|------|-----------|-----------|-------------|
| Duplicate `_groq_chat()` | `llm_router.py:170-198` | `router_gui.py:253-281` | Nearly identical Groq API client |
| Duplicate `GROQ_API_URL` | `llm_router.py:167` | `router_gui.py:249` | Same constant defined twice |
| Duplicate SSL fix | `llm_router.py:190-194` | `router_gui.py:272-277` | Same certifi pattern |

### 3.3 Security Issues

| Severity | File | Location | Issue |
|----------|------|----------|-------|
| Info | `web_server.py:351` | `HTTPServer(("127.0.0.1", port), ...)` | Localhost-only binding (correct) |
| Info | `web_server.py:355` | Prints first 4 chars of API key | Minimal exposure (acceptable for local tool) |

---

## 4. Clean Architecture Compliance (Section 9)

### 4.1 Layer Dependency Verification

| Layer | Design Location | Actual Implementation | Status |
|-------|----------------|----------------------|--------|
| **Interface** | CLI, GUI, Web handlers | CLI: `llm_router.py:507-595`, GUI: `router_gui.py:787+`, Web: `web_server.py:107+` | Match |
| **Application** | Task extraction, routing logic | `llm_router.py:259-496` (extract_tasks, route_text, etc.) | Match |
| **Domain** | Data models | `llm_router.py:36-55` (TaskDecision, RouterOutput) | Match |
| **Infrastructure** | Groq API, file I/O | `llm_router.py:167-198`, `router_gui.py:249-281` | Partial |

### 4.2 Module Dependency Violations

| Rule (Design) | Actual Dependency | Status |
|---------------|-------------------|--------|
| `web_server.py` -> `router_gui.py` -> `llm_router.py` | `web_server.py` imports from `router_gui.py` | Match |
| `router_gui.py` -> `llm_router.py` (import) | `router_gui.py` calls `llm_router.py` via subprocess only | Changed |
| `llm_router.py` imports stdlib only | Confirmed: no local imports | Match |
| No circular dependencies | No circular imports detected | Match |

### 4.3 Import Rules Verification

| Module | Design: Can Import | Actual Imports | Status |
|--------|-------------------|----------------|--------|
| `llm_router.py` | stdlib only | `re, json, sys, os, datetime, urllib, dataclasses, typing` | Match |
| `router_gui.py` | `llm_router`, tkinter | `os, sys, glob, subprocess, re, tkinter, json, urllib` (NO `llm_router` import) | Changed |
| `web_server.py` | `router_gui`, http.server | `router_gui` (18 imports), `http.server, json, os, ssl, sys, subprocess, urllib` | Match |

### 4.4 Architecture Score

```
Architecture Compliance: 85%

  Layer structure matches design:    4/4 layers (100%)
  Dependency direction correct:      3/4 rules  (75%)
  Import rules followed:             2/3 modules (67%)
  No circular dependencies:          Yes        (100%)

Deduction: router_gui.py uses subprocess instead of import
  (functionally equivalent but architecturally different)
```

---

## 5. Convention Compliance (Section 10)

### 5.1 Naming Convention Check

| Category | Convention | Files Checked | Compliance | Violations |
|----------|-----------|:-------------:|:----------:|------------|
| Functions | snake_case | 3 .py files | 100% | None |
| Classes | PascalCase | `TaskDecision`, `RouterOutput`, `RouterGUI`, `RouterHandler` | 100% | None |
| Constants | UPPER_SNAKE_CASE | `GROQ_API_URL`, `DEFAULT_PORT`, `APP_TITLE`, etc. | 100% | None |
| Private funcs | _leading_underscore | `_norm`, `_groq_chat`, `_strip_leading_punct`, etc. | 100% | None |
| Modules | lowercase | `llm_router`, `router_gui`, `web_server` | 100% | None |

**Score: 100%**

### 5.2 Import Order Check

**`llm_router.py`** (lines 25-30):
```python
from __future__ import annotations        # Future
import re, json, sys, os                   # Stdlib
import datetime                            # Stdlib
import urllib.request                      # Stdlib
from dataclasses import dataclass, asdict  # Stdlib
from typing import List, Tuple, Dict, Optional  # Type hints
```
Compliance: Match (stdlib first, then type hints). No third-party imports.

**`router_gui.py`** (lines 2-7):
```python
import os, sys, glob, subprocess, re, tkinter as tk  # Stdlib
import json                                            # Stdlib
import urllib.request                                  # Stdlib
import urllib.error                                    # Stdlib
from typing import List, Dict, Tuple                   # Type hints
from tkinter import ttk, filedialog, messagebox, simpledialog  # Stdlib
```
Compliance: Match (stdlib first, then type hints).

**`web_server.py`** (lines 11-17, 35-51):
```python
import json, os, ssl, sys, subprocess     # Stdlib
from http.server import ...               # Stdlib
from urllib.parse import urlparse         # Stdlib
# ... then local module:
from router_gui import (...)              # Local
```
Compliance: Match (stdlib, then local).

**Score: 100%**

### 5.3 Environment Variable Check

| Variable | Design | Implementation | Status |
|----------|--------|----------------|--------|
| `GROQ_API_KEY` | Optional, all modules | Used in `llm_router.py:241`, `router_gui.py:1068`, `web_server.py:178,259,316` | Match |

**Score: 100%**

### 5.4 File Organization Check

| Design Path | Exists | Status |
|------------|:------:|--------|
| `tools/llm_router.py` | Yes | Match |
| `tools/router_gui.py` | Yes | Match |
| `tools/web_server.py` | Yes | Match |
| `tools/website/router.html` | Yes | Match |
| `tools/website/router.js` | Yes | Match |
| `tools/website/router.css` | Yes | Match |
| `tools/website/index.html` | Yes | Match |
| `tools/website/style.css` | Yes | Match |
| `tools/website/script.js` | Yes | Match |
| `tools/docs/` | Yes | Match |
| `tools/agent_docs/change_log.md` | Yes | Match |
| `tools/task_history.json` | Yes | Match |
| `tools/router_gui_design.md` | Not found | Missing |

**Score: 12/13 (92%)**

### 5.5 Convention Score

```
Convention Compliance: 98%

  Naming:             100%
  Import Order:       100%
  Env Variables:      100%
  File Organization:   92%
```

---

## 6. Detailed Difference Inventory

### 6.1 Missing Features (Design specified, Implementation absent)

| # | Item | Design Location | Description | Priority |
|---|------|----------------|-------------|----------|
| M1 | `router_gui_design.md` | Section 10.4 | File listed in design but not found in project root | Low |
| M2 | Change log stub injection | Section 2.3, 6.3 | `build_change_log_stub()` returns empty string at `llm_router.py:312-313`. Design says "Change Log Stub Injection" and "Inject default stub" as fallback | Medium |
| M3 | Keyword-based routing | Section 11.1 | Design specifies keyword-based route classification (`analyze/implement/research`). Implementation always returns `"claude"` route at `llm_router.py:457` | Medium |
| M4 | Priority assignment (keywords-based) | Section 2.3 | Design says "Priority Assignment (keywords-based)". Implementation uses order-based priority at `llm_router.py:454` | Low |
| M5 | Confidence scoring (0.0-1.0 variable) | Section 2.3 | Design says variable scoring. Implementation uses fixed 0.85 at `llm_router.py:458` | Low |
| M6 | Route selection (analyze/implement/research) | Section 2.3, 11.1 | Design specifies 3 routes. Implementation uses single "claude" route | Medium |
| M7 | Output text widget readonly | Section 5.4 | Design says "readonly". Implementation is writable | Low |

### 6.2 Added Features (Implementation present, Design absent)

| # | Item | Implementation Location | Description | Priority |
|---|------|------------------------|-------------|----------|
| A1 | `--json` flag | `llm_router.py:510,575-577` | JSON output mode | Low |
| A2 | `--tickets-md` flag | `llm_router.py:513,579` | Markdown tickets output | Low |
| A3 | `--opus-only` flag | `llm_router.py:512` | Opus-only prompt mode | Low |
| A4 | Request compression/translation | `router_gui.py:1066-1084` | Pre-translates Korean requests via Groq before routing | Medium |
| A5 | `translate_output_via_groq()` | `router_gui.py:108-197` | 5-phase fence-safe Groq translation pipeline | Medium |
| A6 | `translate_block_to_english()` | `router_gui.py:203-245` | Line-by-line Korean-to-English translation | Medium |
| A7 | `TRANSLATE_MAP` dictionary | `router_gui.py:53-75` | Hardcoded UI string translation map | Low |
| A8 | Web UI navigation bar | `router.html:14-26` | Portfolio + Task Splitter nav links | Low |
| A9 | Web UI "How to use" section | `router.html:47-63` | 3-step usage guide | Low |
| A10 | Web UI Advanced Settings (details) | `router.html:96-119` | Collapsible expert settings | Low |
| A11 | Web UI loading overlay | `router.html:140-143`, `router.css:422-454` | Spinner during routing | Low |
| A12 | Web UI toast notifications | `router.html:137`, `router.js:54-60` | Non-modal feedback | Low |
| A13 | Web UI ticket selector dropdown | `router.html:81-84`, `router.js:178-187` | Dropdown instead of per-task copy buttons | Low |
| A14 | `_translate_remaining_korean()` | `web_server.py:54-101` | Additional Korean line translation helper | Low |
| A15 | `recover_ticket_chunk_from_output()` | `router_gui.py:678-706` | Fallback recovery from full output | Low |
| A16 | `recover_change_log_stub_from_output()` | `router_gui.py:709-721` | Change log stub recovery | Low |
| A17 | Context menu (right-click) | `router_gui.py:830-863` | Cut/Copy/Paste/Select All context menu | Low |
| A18 | Startup banner | `router_gui.py:978-985` | Beginner mode welcome message | Low |
| A19 | `apply_english_tickets_to_claude_block()` | `router_gui.py:427-510` | Replace ticket bodies with English versions | Medium |
| A20 | SSL certificate fix | `web_server.py:20-31`, `llm_router.py:190-194` | certifi-based SSL handling | Low |
| A21 | Web: Ctrl/Cmd+Enter shortcut | `router.js:266-271` | Keyboard shortcut to run | Low |
| A22 | `extract_tickets_from_claude_block()` | `router_gui.py:284-368` | Fence-aware ticket body extraction | Low |
| A23 | `IMPL_RULES_SUFFIX` / `append_rules` | `web_server.py:338-339` | Append implementation rules to extracted block | Low |

### 6.3 Changed Features (Design differs from Implementation)

| # | Item | Design | Implementation | Impact |
|---|------|--------|----------------|--------|
| C1 | API route response format | `{ success, output, ticket_ids, error }` | `{ output, tickets, error, translate_status }` | Medium |
| C2 | API route request format | Nested `flags` object | Flat parameters | Low |
| C3 | API extract-block `translate` field | `"translate": true` | `"translate_groq": true` | Low |
| C4 | Button label (Web) | "Route Tasks" | "Split Tasks" | Low |
| C5 | Per-task copy buttons (Web) | Individual copy per task | Single "Copy This Task" + ticket selector | Low |
| C6 | router_gui dependency on llm_router | Module-level import | subprocess.run() call only | Medium |
| C7 | Groq API client duplication | Single client in llm_router | Duplicated in router_gui (separate implementation) | Medium |
| C8 | Routing algorithm | Keywords-based (analyze/implement/research) | Fixed "claude" route for all tasks | High |
| C9 | router.css line count | ~250 | 528 | Low |
| C10 | Error response status code | 500 for route errors | 400 for validation errors | Low |

---

## 7. Match Rate Calculation

### 7.1 Scoring Methodology

Each design item is categorized and scored:
- **Full Match**: 1.0 point
- **Partial Match**: 0.5 point
- **Missing/Changed**: 0.0 points
- **Extra features** (implementation-only) are noted but do not reduce score

### 7.2 Category Scores

| Category | Total Items | Full Match | Partial | Missing | Score |
|----------|:----------:|:----------:|:-------:|:-------:|:-----:|
| **Data Model** (Sec 3) | 26 | 26 | 0 | 0 | 100% |
| **API Endpoints** (Sec 4) | 5 endpoints | 3 | 2 | 0 | 80% |
| **API Request/Response Format** | 8 fields | 4 | 1 | 3 | 59% |
| **CLI Flags** (Sec 4.4) | 10 | 10 | 0 | 0 | 100% |
| **GUI Components** (Sec 5.1, 5.4) | 12 | 10 | 1 | 1 | 88% |
| **Web UI Components** (Sec 5.2) | 7 | 4 | 2 | 1 | 71% |
| **User Flow** (Sec 5.3) | 17 steps | 15 | 2 | 0 | 94% |
| **Error Handling** (Sec 6) | 10 | 9 | 1 | 0 | 95% |
| **Dependencies** (Sec 2.4) | 4 | 2 | 0 | 2 | 50% |
| **Security** (Sec 7) | 6 | 6 | 0 | 0 | 100% |
| **Architecture Layers** (Sec 9) | 7 | 5 | 2 | 0 | 86% |
| **Routing Algorithm** (Sec 11.1) | 3 algorithms | 1 | 1 | 1 | 50% |
| **Naming Convention** (Sec 10) | 5 categories | 5 | 0 | 0 | 100% |
| **File Organization** (Sec 10.4) | 13 | 12 | 0 | 1 | 92% |

### 7.3 Overall Match Rate

```
Total Design Items:  133
Full Match:          112  (84.2%)
Partial Match:       12   (9.0%)
Missing/Changed:     9    (6.8%)

Design Match Rate = (112 + 12*0.5) / 133 = 118 / 133 = 88.7%
```

---

## 8. Overall Scores

| Category | Score | Status |
|----------|:-----:|:------:|
| Design Match | 88.7% | Partial |
| Architecture Compliance | 85% | Partial |
| Convention Compliance | 98% | Pass |
| **Overall** | **90.6%** | **Pass** |

```
Overall Score: 90.6/100

  Design Match:              88.7 points
  Architecture Compliance:   85.0 points
  Convention Compliance:     98.0 points
  Weighted Average:          90.6 points
```

---

## 9. Recommended Actions

### 9.1 Immediate Actions (Critical/High)

| Priority | Item | Files | Description |
|----------|------|-------|-------------|
| High | C8: Routing algorithm simplified | `llm_router.py:457-459` | Design specifies keyword-based routing (analyze/implement/research) but implementation uses fixed "claude" route. Either update design to reflect simplified routing or implement keyword-based logic |
| High | C1: API response format | `web_server.py:274-279` | `ticket_ids` renamed to `tickets`, `success` field removed. Update design Section 4.2 to match actual format |
| High | C6/C7: Dependency architecture | `router_gui.py` | Design says module-level import of `llm_router`. Actual uses subprocess + duplicated `_groq_chat()`. Decide which is correct and update design or refactor |

### 9.2 Short-term Actions (Medium)

| Priority | Item | Files | Description |
|----------|------|-------|-------------|
| Medium | M2: Change log stub | `llm_router.py:312-313` | `build_change_log_stub()` returns empty string. Design says inject default stub. Either implement or update design |
| Medium | M3/M6: Route types | `llm_router.py:457` | Only "claude" route used. Design specifies 3 route types. Update design to reflect v4.0 simplified routing |
| Medium | C2: API request format | Design Section 4.2 | Nested `flags` object in design vs flat parameters in implementation. Update design |
| Medium | Groq code duplication | `llm_router.py:170-198`, `router_gui.py:253-281` | `_groq_chat()` duplicated. Consider extracting shared module |

### 9.3 Long-term Actions (Low)

| Priority | Item | Files | Description |
|----------|------|-------|-------------|
| Low | M1: Missing file | Project root | `router_gui_design.md` listed in design but not found. Either create or remove from design |
| Low | A1-A23: Document extra features | Design doc | 23 implementation features not documented. Update design to reflect them |
| Low | C9: CSS line count | Design Section 2.2 | ~250 estimated vs 528 actual. Update estimate |
| Low | M4/M5: Priority and confidence | `llm_router.py:454,458` | Order-based priority and fixed confidence vs keyword-based. Update design |

---

## 10. Design Document Updates Needed

The following items require design document updates to match implementation:

- [ ] **Section 2.4**: Change `router_gui.py` dependency from "module import" to "subprocess call"
- [ ] **Section 4.2**: Update POST `/api/route` request format from nested `flags` to flat parameters
- [ ] **Section 4.2**: Update response field name from `ticket_ids` to `tickets`
- [ ] **Section 4.2**: Add `translate_status` to response, remove `success` field
- [ ] **Section 4.3**: Update `translate` field name to `translate_groq`, add `append_rules` field
- [ ] **Section 5.1**: Add extra GUI components (translation checkboxes, all input fields, context menu)
- [ ] **Section 5.2**: Update button label "Route Tasks" to "Split Tasks", document navigation/how-to/advanced/loading/toast
- [ ] **Section 10.4**: Remove `router_gui_design.md` or create the file
- [ ] **Section 11.1**: Update routing algorithm to reflect simplified "claude" route
- [ ] **Section 2.2**: Update `router.css` line count from ~250 to ~528
- [ ] Document 23 extra features (A1-A23) in appropriate design sections

---

## 11. Next Steps

- [ ] Decide synchronization direction for C8 (routing algorithm): update design or implement keywords
- [ ] Update design document Sections 2.4, 4.2, 4.3, 5.1, 5.2, 10.4, 11.1
- [ ] Consider refactoring `_groq_chat()` duplication
- [ ] Write completion report (`tools.report.md`) after gap resolution

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-02-13 | Initial gap analysis | gap-detector |
