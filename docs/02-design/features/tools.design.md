---
template: design
version: 1.2
description: LLM Router (AI Task Splitter) Design Document
variables:
  - feature: tools (LLM Router)
  - date: 2026-02-13
  - author: AI Development Team
  - project: LLM Router
  - version: 4.0
---

# LLM Router Design Document

> **Summary**: Multi-interface AI task routing system with CLI, GUI, and Web support
>
> **Project**: LLM Router (AI Task Splitter)
> **Version**: 4.0
> **Author**: AI Development Team
> **Date**: 2026-02-13
> **Status**: Implemented (Reverse Documentation)
> **Planning Doc**: [tools.plan.md](../01-plan/features/tools.plan.md)

### Pipeline References

| Phase | Document | Status |
|-------|----------|--------|
| Phase 1 | Schema Definition | N/A (Standalone tool) |
| Phase 2 | Coding Conventions | N/A (Python PEP8) |
| Phase 3 | Mockup | N/A (Implemented) |
| Phase 4 | API Spec | ✅ (See Section 4) |

---

## 1. Overview

### 1.1 Design Goals

- **Simplicity**: Minimal dependencies, easy to run
- **Flexibility**: Multiple interfaces (CLI, GUI, Web)
- **Reliability**: Robust parsing with fallback mechanisms
- **Usability**: Beginner-friendly with copy-paste workflows
- **Extensibility**: Support multiple router projects

### 1.2 Design Principles

- **Single Responsibility**: Each module handles one interface (CLI, GUI, Web)
- **Fail-Safe Parsing**: Never crash on malformed input
- **Idempotent Operations**: Re-running with same input produces same output
- **Zero External Dependencies**: Core router uses Python stdlib only
- **Optional Enhancements**: Groq API for splitting/translation (optional)

---

## 2. Architecture

### 2.1 Component Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                      User Interfaces                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐   ┌──────────┐   ┌──────────────────────┐     │
│  │   CLI    │   │   GUI    │   │      Web UI          │     │
│  │ (stdin)  │   │ (Tkinter)│   │   (Browser)          │     │
│  └────┬─────┘   └────┬─────┘   └──────────┬───────────┘     │
│       │              │                     │                 │
│       └──────────────┼─────────────────────┘                 │
│                      │                                       │
├──────────────────────┼───────────────────────────────────────┤
│                      ▼                                       │
│             ┌─────────────────┐                              │
│             │  llm_router.py  │  Core Routing Engine         │
│             │                 │  • Task extraction           │
│             │                 │  • Priority assignment       │
│             │                 │  • Prompt generation         │
│             └────────┬────────┘                              │
│                      │                                       │
│                      ▼                                       │
│         ┌────────────────────────┐                           │
│         │   Optional Services    │                           │
│         ├────────────────────────┤                           │
│         │  Groq API (splitting)  │                           │
│         │  Groq API (translation)│                           │
│         └────────────────────────┘                           │
│                                                              │
└──────────────────────────────────────────────────────────────┘

Data Flow:
User Request → Interface → Router → Claude Prompt → Clipboard → Claude
```

### 2.2 Component Details

| Component | File | Lines | Responsibility |
|-----------|------|-------|----------------|
| **Core Router** | `llm_router.py` | 596 | Task extraction, routing logic, prompt generation |
| **GUI Interface** | `router_gui.py` | 1259 | Tkinter GUI, ticket selection, clipboard management |
| **Web Server** | `web_server.py` | 367 | HTTP server, REST API, static file serving |
| **Web UI** | `website/router.html` | 148 | Browser-based interface |
| **Web Client** | `website/router.js` | 277 | API client, UI interactions |
| **Styling** | `website/router.css` | 528 | Monochromatic UI design (responsive, animations, advanced styling) |

### 2.3 Data Flow

```
1. Input Phase
   User Request (Korean/English)
   ↓
   Normalization (whitespace, boilerplate removal)
   ↓
   Task Extraction (numbered list OR Groq API split)

2. Routing Phase
   Task List
   ↓
   Priority Assignment (order-based: 1st task = priority 10, decrement)
   ↓
   Confidence Scoring (fixed 0.95 for all tasks)
   ↓
   Route Selection (simplified: all tasks → "claude" route)

3. Output Phase
   Claude Prompt Generation
   ↓
   Change Log Stub Injection
   ↓
   Optional Translation (Korean → English)
   ↓
   Clipboard Copy (GUI/Web) OR stdout (CLI)
```

### 2.4 Dependencies

| Component | Internal Deps | External Deps |
|-----------|---------------|---------------|
| `llm_router.py` | None | stdlib only |
| `router_gui.py` | `llm_router.py` (subprocess call, not import) | tkinter (stdlib) |
| `web_server.py` | `router_gui.py` (function imports) | http.server (stdlib) |
| Groq API | Duplicated in both `llm_router.py` and `router_gui.py` | GROQ_API_KEY (optional) |

**Note**: `router_gui.py` calls `llm_router.py` via `subprocess.run()` rather than module-level imports.
This avoids circular dependencies but results in duplicated `_groq_chat()` function code.

---

## 3. Data Model

### 3.1 Core Entities

```python
# TaskDecision - Individual ticket
@dataclass
class TaskDecision:
    id: str                    # A, B, C, ...
    summary: str               # Short description
    route: str                 # "claude" (v4.0 uses simplified routing)
    confidence: float          # 0.95 (fixed for all tasks in v4.0)
    priority: int              # 10, 9, 8, ... (order-based, decrementing)
    reasons: List[str]         # Routing reasons (generic in v4.0)
    claude_prompt: str         # Generated prompt for Claude
    next_session_starter: str  # Follow-up prompt template
    change_log_stub: str       # Template for change log entry

# RouterOutput - Complete routing result
@dataclass
class RouterOutput:
    route: str                 # Global route (if all tasks same)
    confidence: float          # Overall confidence
    reasons: List[str]         # Global routing reasons
    global_notes: List[str]    # Cross-cutting concerns
    session_guard: List[str]   # Safety reminders
    tasks: List[TaskDecision]  # All tickets
```

### 3.2 Task History Schema

```json
{
  "timestamp": "2026-02-13T14:00:00Z",
  "id": "A",
  "summary": "Fix translation bug in router",
  "priority": 8,
  "route": "implement",
  "confidence": 0.95,
  "reasons": ["Mentions 'bug'", "Specific component"]
}
```

### 3.3 State Management

- **Stateless Core**: `llm_router.py` has no state (pure functions)
- **GUI State**: Tkinter widgets hold UI state (input text, flags, output)
- **History Log**: `task_history.json` appends records (append-only)
- **No Database**: All data is ephemeral or JSON-based

---

## 4. API Specification

### 4.1 Web Server Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/` | Serve `router.html` | None |
| GET | `/api/routers` | List available router scripts | None |
| GET | `/api/preflight` | Git status + environment check | None |
| POST | `/api/route` | Execute routing | None |
| POST | `/api/extract-block` | Extract Claude block from output | None |

### 4.2 POST /api/route

Execute routing and return Claude-ready prompts.

**Request:**
```json
{
  "router": "/path/to/llm_router.py",
  "request": "사용자 요청 텍스트",
  "economy": "balanced",
  "phase": "implement",
  "friendly": true,
  "force_split": false,
  "translate_en": false,
  "ticket_groq_translate": false,
  "desktop_edit": false,
  "opus_only": false,
  "tickets_md": false,
  "save_tickets": "",
  "min_tickets": 0,
  "max_tickets": 0
}
```

**Note**: Request uses flat parameter structure (not nested `flags` object).

**Response (200 OK):**
```json
{
  "output": "Full router output with tickets",
  "tickets": ["A", "B", "C"],
  "translate_status": "ok",
  "error": null
}
```

**Note**: Response changes from design:
- Removed `success` field (error presence indicates failure)
- Changed `ticket_ids` to `tickets`
- Added `translate_status` field

**Error Response (400/500):**
```json
{
  "output": "",
  "tickets": [],
  "translate_status": "failed",
  "error": "Router execution failed: ..."
}
```

### 4.3 POST /api/extract-block

Extract and prepare Claude block for clipboard.

**Request:**
```json
{
  "output": "Full router output text",
  "ticket": "B",
  "translate_groq": true,
  "append_rules": true
}
```

**Note**: Field name changed from `translate` to `translate_groq`. Added `append_rules` option.

**Response (200 OK):**
```json
{
  "success": true,
  "block": "Claude-ready prompt text",
  "error": null
}
```

### 4.4 CLI Interface

```bash
# Basic usage
python3 llm_router.py "사용자 요청"

# With flags
python3 llm_router.py "요청" --phase implement --economy strict --friendly

# Save tickets to file
python3 llm_router.py "요청" --save-tickets output.md

# Force split
python3 llm_router.py "요청" --force-split --min-tickets 3
```

**CLI Flags:**
- `--desktop-edit`: Desktop editing mode
- `--economy strict|balanced`: Token economy level
- `--phase analyze|implement`: Development phase
- `--one-task B`: Extract single ticket
- `--save-tickets FILE`: Save to markdown
- `--friendly`: Copy-paste friendly format
- `--force-split`: Force task splitting via Groq
- `--min-tickets N`: Minimum number of tickets
- `--max-tickets N`: Maximum number of tickets
- `--merge "A+B"`: Merge specific tickets

---

## 5. UI/UX Design

### 5.1 GUI Layout (Tkinter)

```
┌────────────────────────────────────────────────────────┐
│  LLM Router GUI v2.0                            [X]    │
├────────────────────────────────────────────────────────┤
│                                                        │
│  Router: [llm_router.py ▼]  [Refresh]  Git: clean     │
│                                                        │
│  Request:                                              │
│  ┌──────────────────────────────────────────────────┐ │
│  │ 사용자 요청 입력...                                  │ │
│  │                                                  │ │
│  └──────────────────────────────────────────────────┘ │
│                                                        │
│  Flags: [✓] Friendly  [✓] Desktop  Economy: [Balanced]│
│         [ ] Force Split  Phase: [Implement]            │
│                                                        │
│  [Run Router]                                          │
│                                                        │
│  Output:                                               │
│  ┌──────────────────────────────────────────────────┐ │
│  │ Task A:                                          │ │
│  │ ...                                              │ │
│  │                                                  │ │
│  │ Task B:                                          │ │
│  │ ...                                              │ │
│  └──────────────────────────────────────────────────┘ │
│                                                        │
│  [Copy Claude Block]  [Clear Output]                  │
│                                                        │
└────────────────────────────────────────────────────────┘
```

### 5.2 Web UI Layout

```
┌────────────────────────────────────────────────────────┐
│  AI Task Splitter                                      │
├────────────────────────────────────────────────────────┤
│                                                        │
│  Enter your request:                                   │
│  ┌──────────────────────────────────────────────────┐ │
│  │                                                  │ │
│  └──────────────────────────────────────────────────┘ │
│                                                        │
│  ☐ Friendly Mode  ☐ Force Split  Economy: Balanced    │
│                                                        │
│  [Route Tasks]                                         │
│                                                        │
│  Results:                                              │
│  ┌──────────────────────────────────────────────────┐ │
│  │ Task A: ...                                      │ │
│  │ [Copy]                                           │ │
│  │                                                  │ │
│  │ Task B: ...                                      │ │
│  │ [Copy]                                           │ │
│  └──────────────────────────────────────────────────┘ │
│                                                        │
└────────────────────────────────────────────────────────┘
```

### 5.3 User Flow

```
1. GUI Workflow
   Launch router_gui.py
   ↓
   Select router (if multiple)
   ↓
   Enter request + set flags
   ↓
   Click "Run Router"
   ↓
   Select ticket (A/B/C)
   ↓
   Click "Copy Claude Block"
   ↓
   Paste into Claude

2. Web Workflow
   Start web_server.py
   ↓
   Open http://localhost:8080
   ↓
   Enter request
   ↓
   Click "Route Tasks"
   ↓
   Click "Copy" on desired task
   ↓
   Paste into Claude

3. CLI Workflow
   Run llm_router.py "request"
   ↓
   View output in terminal
   ↓
   Copy desired ticket manually
   ↓
   Paste into Claude
```

### 5.4 Key Components (GUI)

| Component | File Location | Responsibility |
|-----------|---------------|----------------|
| Router Selector | `router_gui.py:find_router_candidates()` | Discover router scripts |
| Request Input | Tkinter Text widget | Multi-line input |
| Flag Panel | Tkinter Checkboxes + Combobox | Configuration |
| Output Display | Tkinter Text widget (readonly) | Show results |
| Ticket Selector | `router_gui.py:detect_ticket_ids()` | Find A/B/C tickets |
| Claude Block Extractor | `router_gui.py:extract_claude_ready_block_from_output()` | Parse Claude block |
| Ticket Slicer | `router_gui.py:slice_single_ticket_from_block()` | Isolate single ticket |
| Translator | `router_gui.py:rewrite_tickets_to_english_via_groq()` | Korean → English |

---

## 6. Error Handling

### 6.1 Error Categories

| Category | Examples | Handling |
|----------|----------|----------|
| **Input Errors** | Empty request, invalid flags | Show warning, don't execute |
| **Router Errors** | Script not found, syntax error | Display stderr, log error |
| **Parsing Errors** | No tickets detected, invalid format | Return full output as fallback |
| **API Errors** | Groq timeout, invalid key | Warn user, skip translation |
| **System Errors** | Permission denied, disk full | Show error dialog, log |

### 6.2 Error Response Format (API)

```json
{
  "success": false,
  "output": "",
  "ticket_ids": [],
  "error": "Router execution failed: FileNotFoundError: llm_router.py"
}
```

### 6.3 Fallback Strategies

1. **Task Extraction Failure** → Return input as single task
2. **Translation Failure** → Return original Korean text
3. **Ticket Parsing Failure** → Return entire Claude block
4. **Change Log Stub Missing** → Inject default stub
5. **Groq API Unavailable** → Use local parsing (numbered lists)

---

## 7. Security Considerations

- [x] **No Credential Storage**: Groq API key from environment only
- [x] **No Command Injection**: subprocess uses list args, not shell
- [x] **No XSS**: Web UI escapes output (browser handles)
- [ ] **CORS Protection**: Not implemented (localhost-only server)
- [ ] **Rate Limiting**: Not implemented
- [x] **Safe Parsing**: Regex-based, no `eval()` or `exec()`

**Security Notes:**
- Web server is **localhost-only** (not exposed to internet)
- No authentication needed (single-user tool)
- No database or persistent credentials
- Environment variable `GROQ_API_KEY` is optional

---

## 8. Test Plan

### 8.1 Test Scope

| Type | Target | Method |
|------|--------|--------|
| Unit Test | Task extraction logic | Manual testing with sample inputs |
| Integration Test | Router → GUI → Clipboard | End-to-end manual testing |
| API Test | Web server endpoints | curl/Postman requests |
| UI Test | GUI interactions | Manual click testing |

### 8.2 Test Cases (Key Scenarios)

- [x] **Single task input** → Produces 1 ticket
- [x] **Numbered list input** → Splits correctly
- [x] **Korean input** → Groq splits tasks
- [x] **Multiple tickets** → A/B/C labeling works
- [x] **Ticket selection** → Only selected ticket copied
- [x] **Translation** → Korean → English via Groq
- [x] **Change log stub** → Present in output
- [x] **Empty input** → Handled gracefully
- [ ] **Malformed input** → No crashes (needs verification)
- [ ] **API timeout** → Graceful degradation (needs verification)

### 8.3 Testing Tools

- **Manual Testing**: Primary method (developer testing)
- **Browser DevTools**: For web UI debugging
- **curl**: For API endpoint testing
- **Task History Log**: Verify routing decisions

---

## 9. Clean Architecture (Python)

### 9.1 Layer Structure

| Layer | Responsibility | Location |
|-------|---------------|----------|
| **Interface** | CLI, GUI, Web handlers | `llm_router.py` (main), `router_gui.py` (GUI), `web_server.py` (HTTP) |
| **Application** | Task extraction, routing logic | `llm_router.py` (functions) |
| **Domain** | Data models (TaskDecision, RouterOutput) | `llm_router.py` (dataclasses) |
| **Infrastructure** | Groq API client, file I/O | `llm_router.py` (Groq), `router_gui.py` (clipboard) |

### 9.2 Module Dependency Rules

```
┌───────────────────────────────────────────────────────────────┐
│  Dependency Direction (subprocess vs import)                  │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│   router_gui.py  ──subprocess──▶  llm_router.py              │
│        │                               │                      │
│        │ (duplicated)                  ▼                      │
│        │ _groq_chat()            (Groq API)                   │
│        │                                                      │
│        ▼                                                      │
│   (Tkinter)                                                   │
│                                                               │
│   web_server.py  ──import──▶  router_gui.py (functions)     │
│        │                               │                      │
│        │                               └──subprocess──▶       │
│        ▼                                   llm_router.py      │
│   (http.server)                                               │
│                                                               │
│   Rule: No module-level circular dependencies                │
│   router_gui uses subprocess (not import) to call router     │
│   Side effect: _groq_chat() duplicated in both files         │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### 9.3 Import Rules

| Module | Can Import | Cannot Import | Notes |
|--------|-----------|---------------|-------|
| `llm_router.py` | stdlib only | router_gui, web_server | Standalone CLI |
| `router_gui.py` | tkinter, stdlib | llm_router (uses subprocess), web_server | Duplicates `_groq_chat()` |
| `web_server.py` | router_gui (functions), http.server | llm_router (indirect via subprocess) | Imports helper functions from GUI |

**Architectural Note**: `router_gui.py` calls `llm_router.py` via `subprocess.run()`
rather than Python imports. This avoids circular dependency issues but results in
code duplication (`_groq_chat()` function exists in both files).

---

## 10. Coding Convention Reference

### 10.1 Python Naming Conventions

| Target | Rule | Example |
|--------|------|---------|
| Functions | snake_case | `extract_tasks()`, `split_via_groq()` |
| Classes | PascalCase | `TaskDecision`, `RouterOutput` |
| Constants | UPPER_SNAKE_CASE | `GROQ_API_URL`, `DEFAULT_PORT` |
| Private Functions | _leading_underscore | `_norm()`, `_groq_chat()` |
| Modules | lowercase | `llm_router`, `router_gui`, `web_server` |

### 10.2 Import Order

```python
# 1. Standard library
import re, json, sys, os

# 2. Third-party (if any)
# (None in this project)

# 3. Local modules
from router_gui import find_router_candidates

# 4. Type hints
from typing import List, Tuple, Dict, Optional
```

### 10.3 Environment Variables

| Variable | Purpose | Scope | Required |
|----------|---------|-------|:--------:|
| `GROQ_API_KEY` | Groq API authentication | All modules | Optional |

### 10.4 File Organization

```
tools/
├── llm_router.py          # Core engine (CLI entry point)
├── router_gui.py          # GUI entry point
├── web_server.py          # Web server entry point
├── website/               # Static web assets
│   ├── router.html        # Main web UI
│   ├── router.js          # Client logic
│   ├── router.css         # Styling
│   ├── index.html         # Portfolio page
│   ├── style.css          # Main styles
│   └── script.js          # Main scripts
├── docs/                  # PDCA documentation
│   ├── 01-plan/
│   └── 02-design/
├── agent_docs/            # Change logs
│   └── change_log.md
├── task_history.json      # Task history (generated)
└── router_gui_design.md   # GUI design spec
```

---

## 11. Implementation Guide

### 11.1 Key Algorithms

#### Task Extraction Algorithm

```python
def extract_tasks(text: str, force_split: bool = False) -> List[str]:
    # 1. Normalize (remove whitespace, boilerplate)
    # 2. Check if numbered list → split by numbers
    # 3. Otherwise → call Groq API for splitting
    # 4. Fallback: return [text] if all fails
```

#### Routing Algorithm

```python
def route_task(task: str) -> str:
    # Simplified routing in v4.0
    # All tasks are routed to "claude"
    # No keyword-based classification
    # Future versions may restore analyze/implement/research routing
    return "claude"
```

**Note**: v4.0 uses simplified routing. All tasks receive the same `"claude"` route,
with priority determined by order (1st = priority 10, 2nd = priority 9, etc.)
and fixed confidence of 0.95.

#### Ticket Extraction Algorithm

```python
def slice_single_ticket_from_block(block: str, ticket_id: str) -> str:
    # 1. Find ticket header (Task A:, Ticket B:, etc.)
    # 2. Extract until next ticket or end of block
    # 3. Preserve fence blocks (```) correctly
    # 4. Include change log stub if missing
```

### 11.2 Implementation Order

1. [x] Core router engine (`llm_router.py`)
2. [x] CLI interface (same file)
3. [x] GUI interface (`router_gui.py`)
4. [x] Ticket selection and extraction
5. [x] Groq translation integration
6. [x] Web server (`web_server.py`)
7. [x] Web UI (`website/router.html`)
8. [x] Task history logging
9. [ ] Documentation and user guide
10. [ ] Gap analysis and quality review

### 11.3 Critical Files

| Priority | File | Purpose |
|:--------:|------|---------|
| **High** | `llm_router.py` | Core logic - must work standalone |
| **High** | `router_gui.py` | Primary user interface |
| **Medium** | `web_server.py` | Alternative interface |
| **Medium** | `website/router.js` | Web client functionality |
| **Low** | `website/router.css` | UI styling |

---

## 12. Known Issues and Limitations

### 12.1 Current Limitations

1. **No Database**: Task history is append-only JSON (no queries)
2. **No Authentication**: Web server is localhost-only
3. **Manual Copy-Paste**: No direct Claude API integration
4. **Single Language**: UI text is mixed Korean/English
5. **No Tests**: Manual testing only

### 12.2 Future Improvements

- [ ] Add unit tests for task extraction
- [ ] Implement Claude API direct integration
- [ ] Add user authentication for web UI
- [ ] Migrate to SQLite for task history
- [ ] Improve error messages and logging
- [ ] Add configuration file support
- [ ] Implement rate limiting for Groq API

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-02-13 | Initial design document (reverse documentation) | AI Development Team |
| 0.2 | 2026-02-13 | Updated to match actual implementation (Gap Analysis sync): simplified routing algorithm, API format changes, subprocess dependencies, updated line counts | AI Development Team |
