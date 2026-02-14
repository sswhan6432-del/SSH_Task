# SSH_WEB Project Rules
# CLAUDE.md - AI Performance Configuration
# TokenSaver Pro v1.0
# Generated: 2026-02-14
# Optimizations: 14 selected

---

## About This Configuration

This file contains optimized settings for Claude AI to maximize performance
and minimize token usage. Place this file in one of these locations:

- Global settings: ~/.claude/CLAUDE.md
- Project settings: <project-root>/.claude/CLAUDE.md

---
## [P] Performance Optimizations

### Fast Mode

Enable faster output without sacrificing quality.

**Usage:**
- Command: /fast
- Toggle on/off as needed

**Benefits:**
- Same model (Claude Opus 4.6)
- Optimized output speed
- Ideal for quick iterations

### Parallel Execution

Maximize efficiency by running independent operations simultaneously.

**Rules:**
- Call independent tools in parallel, not sequentially
- Minimize API roundtrips
- Batch similar operations together

**Example:**
Instead of reading files one-by-one, read them all at once in parallel.

### Auto Compression

Automatic context management at memory limits.

**Behavior:**
- Activates automatically when context is full
- No manual intervention required
- Preserves critical information
- Optimizes token usage

---

## [S] Response Style

### Concise Response Style

Short, focused responses that get to the point.

**Guidelines:**
- Keep explanations brief
- Avoid unnecessary verbosity
- Use bullet points for clarity
- Skip context unless explicitly requested
- Direct answers over long narratives

### Professional Text Only

Maintain professional tone without emojis.

**Rules:**
- Never use emojis or emoticons
- Text-only output
- Exception: User explicitly requests emojis

### Language Preference

Balanced bilingual communication strategy.

**Usage:**
- Code/Commits: Always English
- Explanations: Korean preferred
- Summaries: Brief Korean before major actions
- Comments: Match project language

### Format Preference

Structured output using lists and points.

**Guidelines:**
- Prefer bullet points over paragraphs
- Use numbered lists for sequential steps
- Keep each point concise
- Maximum 3 levels of nesting
- Clear hierarchy

---

## [W] Workflow Efficiency

### Smart Task Delegation

Optimize context usage through strategic agent delegation.

**Strategy:**
- Use Task tool for specialized work
- Delegate research to subagents
- Avoid work duplication
- Reserve main context for decisions
- Parallel agent execution when possible

### Tool Usage Priority

Always prefer dedicated tools over generic commands.

**Hierarchy:**
1. Read (not cat/head/tail)
2. Edit (not sed/awk)
3. Write (not echo/heredoc)
4. Glob (not find/ls)
5. Grep (not grep/rg)

**Exception:**
Only use Bash for system commands and terminal operations that
require shell execution.

### Efficient File Reading

Strategic file access to minimize token usage.

**Techniques:**
- Use offset/limit parameters for large files
- Read only necessary sections
- Parallel reads for multiple files
- Skip redundant reads
- Cache frequently accessed content

---

## [M] Memory Management

### Persistent Memory

Cross-session learning and pattern recognition.

**Process:**
1. Auto-save insights to memory files
2. Consult memory before similar tasks
3. Update patterns as they emerge
4. Keep MEMORY.md under 200 lines

**Benefit:**
Reduces repeated research and builds project knowledge.

### Context Management

Strategic limits on context consumption.

**Rules:**
- Set reasonable file read limits per task
- Focus on essential code sections only
- Use agents for exploratory work
- Protect main context for critical operations
- Clear stale context regularly

---

## [X] Security & Safety

### Secret File Protection

Comprehensive security for sensitive information.

**Blocked Patterns:**
- .env* files
- *credential* files
- *secret* files
- *token* files
- *key* files
- Certificates
- Authentication files

**Security Protocol:**
1. Never display secret file contents
2. No hardcoded secrets in code
3. Use environment variables
4. Redact secrets in outputs
5. Block commits containing secrets

### Git Safety Protocol

Prevent destructive Git operations.

**Prohibited Actions:**
- Force push to main/master
- Using --no-verify flag
- Amending published commits
- Destructive resets without confirmation

**Safe Practices:**
- Always confirm destructive operations
- Create new commits over amending
- Verify changes before pushing
- Use feature branches


## Styling Defaults (All Pages)

### Apple-Style Easing Curves (CSS Custom Properties)
All transitions MUST use these custom properties defined in `style.css`:
```css
--ease-out-quart: cubic-bezier(0.25, 1, 0.5, 1);       /* fade-in, scroll animations */
--ease-in-out-quart: cubic-bezier(0.76, 0, 0.24, 1);    /* toggles, expand/collapse */
--ease-spring: cubic-bezier(0.28, 0.11, 0.32, 1);       /* hover, interactive elements */
```

### Transition Timing Rules
- **Hover effects**: `0.4–0.5s var(--ease-spring)`
- **Fade-in on scroll**: `0.8s var(--ease-out-quart)` with `scale(0.98)` start
- **Input focus**: `0.4s var(--ease-spring)`
- **Buttons**: `0.4s var(--ease-spring)`, press `scale(0.96)` with `0.1s` duration
- **Toggle/expand**: `0.45s var(--ease-in-out-quart)`
- **Toast/overlay**: `0.4s var(--ease-out-quart)`
- **Cards hover**: `scale(1.02–1.03) translateY(-2px)` instead of `translateY(-4px)` alone
- NEVER use bare `ease`, `ease-in-out`, or `0.3s` without a custom curve

### Page Transition (Swipe Effect)
Every new page MUST include before `</body>`:
```html
<script src="page-transition.js"></script>
```

Behavior:
- White overlay with "Build. Ship. Iterate." text
- Normal pages: swipe right-to-left
- index.html: swipe left-to-right (reverse)
- 0.5s loading screen pause between pages
- Text words appear with staggered fade-up

### New Page Checklist
When creating a new `.html` page:
1. Include `<link rel="stylesheet" href="style.css">` in `<head>`
2. Include page-specific CSS if needed (e.g., `router.css`)
3. Add `<script src="page-transition.js"></script>` before `</body>`
4. Add nav link to ALL existing pages' `<nav>` and `.mobile-menu`
5. Use `var(--ease-*)` curves for all transitions in page-specific CSS

### Design Tokens (from style.css)
```
--black: #000000
--white: #ffffff
--gray: #86868b
--light-bg: #f5f5f7
--accent: #1a1a1a
--nav-height: 48px (desktop), 44px (mobile)
--font: -apple-system, BlinkMacSystemFont, "SF Pro Display", ...
```

### Component Patterns
- Cards: `border-radius: 16px`, `background: var(--light-bg)`
- Buttons: `border-radius: 8px`, primary uses `var(--black)` bg
- Inputs: `border-radius: 12px`, `1px solid rgba(0,0,0,0.12)` border
- Sections: `padding: 100px 24px`, `max-width: 1024px` container

## Architecture
- Static site served by `web_server.py` (stdlib http.server, no framework)
- All pages in `website/` directory
- Backend APIs: `/api/route`, `/api/routers`, `/api/preflight`, etc.
- No build step — plain HTML/CSS/JS
