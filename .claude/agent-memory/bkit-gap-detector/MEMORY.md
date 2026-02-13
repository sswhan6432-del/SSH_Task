# Gap Detector Memory

## Project: LLM Router (tools)

### Key Architecture Facts
- `llm_router.py`: Core engine, stdlib-only, stateless pure functions
- `router_gui.py`: Tkinter GUI, calls llm_router via subprocess (NOT import)
- `web_server.py`: HTTP server, imports from router_gui (18 functions)
- Dependency: web_server -> router_gui -> llm_router (subprocess, not module import)
- `_groq_chat()` is duplicated in both llm_router.py and router_gui.py

### Analysis Results (2026-02-13)
- Overall Match Rate: 90.6%
- Design Match: 88.7% | Architecture: 85% | Convention: 98%
- 133 total design items, 112 full match, 12 partial, 9 missing/changed
- 23 extra features in implementation not documented in design
- Key gap: routing algorithm (design=keyword-based, impl=fixed "claude" route)
- Key gap: API response format differences (ticket_ids->tickets, no success field)
- Output: `/Users/songseunghwan/Desktop/tools/docs/03-analysis/tools.analysis.md`
