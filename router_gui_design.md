# 📐 LLM Router GUI --- Design Specification

**File:** `router_gui.py`\
**Version:** v1.4 (Multi-Project + Beginner Copy/Paste + Ticket
Isolation)

------------------------------------------------------------------------

# 1. 🎯 Purpose

This GUI acts as a safe bridge between:

User Request → Router Script → Claude (Copy/Paste Block)

Primary goals:

-   Beginner-friendly UX\
-   Safe multi-ticket isolation (A/B/C)\
-   Fence-safe parsing (ignore quoted \`\`\` in prose)\
-   Multi-project router swapping\
-   Stable copy-ready Claude prompt extraction

------------------------------------------------------------------------

# 2. 🏗 High-Level Architecture

Tkinter GUI Layer\
Router Selection Layer\
Execution Layer\
Output Processing Layer\
Ticket Extraction Layer\
Optional Groq Translator

------------------------------------------------------------------------

# 3. 🔁 Execution Flow

## Run Router

1.  User inputs request text.
2.  GUI builds CLI command dynamically based on flags.
3.  Router executed via subprocess.
4.  Output appended to Output Text widget.

## Copy Claude Block

1.  Detect available tickets (A/B/C).
2.  If multiple → user selects one.
3.  Extract Claude-ready block.
4.  Slice selected ticket only.
5.  Ensure Change Log Stub exists.
6.  Optional: normalize tickets to English via Groq.
7.  Copy final block to clipboard.

------------------------------------------------------------------------

# 4. 🧠 Core Parsing Rules

## Fence Handling

Only treat fences that START WITH
`on a line as real code blocks.   Never match quoted '`' inside prose.

## Ticket Isolation

When multiple tickets exist in one block, copy only selected ticket.

------------------------------------------------------------------------

# 5. 🧩 Main Components

### Router Discovery

-   find_router_candidates()

### Router Execution

-   run_router()

### Claude Block Extraction

-   extract_claude_ready_block_from_output()

### Ticket Slicing

-   slice_single_ticket_from_block()

### Groq Ticket Normalization

-   extract_tickets_from_claude_block()
-   rewrite_tickets_to_english_via_groq()
-   apply_english_tickets_to_claude_block()

------------------------------------------------------------------------

# 6. 🛡 Invariants

Must always guarantee:

-   Only selected ticket copied
-   Change log stub present
-   Fence parsing safe
-   Multi-ticket isolation correct

------------------------------------------------------------------------

# 7. 📂 Recommended Structure

tools/ router_gui.py routers/ `<project>`{=html}\_router.py

agent_docs/ router_gui_design.md

------------------------------------------------------------------------

End of Document
