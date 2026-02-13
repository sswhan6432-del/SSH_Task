#!/usr/bin/env python3
"""
llm_router.py -- Generic LLM Task Router v4.0

Splits user requests into independent tasks (tickets) and generates
Claude-ready prompts for each. Works with any project.

Core flags:
  --desktop-edit
  --economy strict|balanced
  --phase analyze|implement
  --one-task B
  --save-tickets TICKETS.md
  --tickets-md
  --json
  --friendly
  --force-split
  --min-tickets N
  --max-tickets N
  --merge "A+B"

--friendly prints copy-paste blocks for Claude (beginner-friendly).
"""

from __future__ import annotations
import re, json, sys, os
import datetime  # task history logging
import urllib.request
from dataclasses import dataclass, asdict
from typing import List, Tuple, Dict, Optional

# -------------------------
# Models
# -------------------------

@dataclass
class TaskDecision:
    id: str
    summary: str
    route: str
    confidence: float
    priority: int
    reasons: List[str]
    claude_prompt: str
    next_session_starter: str
    change_log_stub: str

@dataclass
class RouterOutput:
    route: str
    confidence: float
    reasons: List[str]
    global_notes: List[str]
    session_guard: List[str]
    tasks: List[TaskDecision]


# -------------------------
# Task history logging
# -------------------------

def record_tasks(tasks: List[TaskDecision], path: str = "task_history.json") -> None:
    """Append routed tasks to a local JSON history file.

    Keeps an audit trail of what the router produced per invocation.
    Failure to write must not break routing.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            history = json.load(f)
            if not isinstance(history, list):
                history = []
    except Exception:
        history = []

    ts = datetime.datetime.now().isoformat()
    for t in tasks:
        history.append({
            "timestamp": ts,
            "id": t.id,
            "summary": t.summary,
            "priority": t.priority,
            "route": t.route,
            "confidence": t.confidence,
            "reasons": t.reasons,
        })

    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

# -------------------------
# Text normalization
# -------------------------

def _norm(s: str) -> str:
    s = s.strip().replace("\r\n", "\n")
    # If the user pasted literal "\\n" sequences (common in UIs), unescape them.
    if "\\n" in s and "\n" not in s:
        s = s.replace("\\n", "\n")
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()

def _contains_any(text: str, kws: List[str]) -> bool:
    t = text.lower()
    return any(k in t for k in kws)



# Helper to remove leading punctuation artifacts from splits
def _strip_leading_punct(s: str) -> str:
    return re.sub(r"^[,;:·\-\u2013\u2014/]+\s*", "", s).strip()

# Helper to remove router boilerplate if the user pastes prior outputs back as input
def _strip_router_boilerplate(s: str) -> str:
    lines = s.splitlines()
    out: List[str] = []
    for line in lines:
        raw = line.strip()

        # Drop common pasted headers
        if raw.startswith("Task ") and raw.endswith(":"):
            continue
        if raw.startswith("Ticket ") and raw.endswith(":"):
            continue

        # If a change-log stub starts, drop everything after it
        if raw.startswith("Change log stub"):
            break

        # Drop common guardrail boilerplate lines
        if raw.startswith("Implement minimal fix"):
            continue
        if raw.startswith("IMPLEMENT:") or raw.startswith("Flow:"):
            continue
        if raw in {"STOP", "Stop", "Stop."}:
            continue

        # Drop stub lines if present
        if raw.startswith("## YYYY-MM-DD"):
            continue
        if raw.startswith("- What changed") or raw.startswith("- Files") or raw.startswith("- Notes"):
            continue

        out.append(line)

    return "\n".join(out).strip()

# -------------------------
# Task extraction
# -------------------------

def is_numbered(text: str) -> bool:
    return bool(re.search(r"(^|\n)\s*(\d+[\.\)]|[\u2460-\u2473])\s+", text)) or \
           bool(re.search(r"\d+\.\s+\S.*\d+\.\s+\S", text))

def split_numbered(text: str) -> List[str]:
    circled_map = {chr(9311 + i): f"{i+1}." for i in range(20)}
    for k, v in circled_map.items():
        text = text.replace(k, v)
    parts = re.split(r"(?:^|\n|\s)\s*\d+[\.\)]\s+", text)
    return [_strip_leading_punct(p) for p in parts if _strip_leading_punct(p)]

# -------------------------
# Groq API (text splitting)
# -------------------------

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_SPLIT_MODEL = "llama-3.1-8b-instant"

def _groq_chat(messages: list, api_key: str, *, model: str = GROQ_SPLIT_MODEL,
               max_tokens: int = 512, temperature: float = 0.0) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        GROQ_API_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "LLMRouter/4.0",
        },
        method="POST",
    )
    ssl_ctx = None
    try:
        import certifi, ssl
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    with urllib.request.urlopen(req, timeout=15, context=ssl_ctx) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    obj = json.loads(raw)
    return obj["choices"][0]["message"]["content"]


def _parse_numbered_response(text: str) -> List[str]:
    """Parse Groq response like '1. task one\\n2. task two' into a list."""
    lines = text.strip().splitlines()
    tasks: List[str] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        cleaned = re.sub(r"^\s*(?:\d+[\.\)]\s*|[-*]\s+)", "", line).strip()
        if cleaned:
            tasks.append(cleaned)
    return tasks


_SPLIT_SYSTEM_PROMPT = (
    "You are a task splitter. Given a user request (Korean or English), "
    "split it into independent, actionable tasks. Rules:\n"
    "- ONLY split when the input clearly contains multiple distinct actions "
    "(e.g. connected by '\ud558\uace0', 'and', conjunctions, or listed sequentially).\n"
    "- If the input describes ONE action (even with details), output it as a single task.\n"
    "- Do NOT invent sub-tasks. Do NOT decompose a single action into steps.\n"
    "- Preserve the original wording as much as possible.\n"
    "- Output ONLY a numbered list (1. ... 2. ...). No explanations.\n"
    "- Do NOT merge or rephrase tasks beyond minimal cleanup."
)

_SPLIT_SYSTEM_PROMPT_FORCE = (
    "You are an aggressive task splitter. Given a user request (Korean or English), "
    "split it into the smallest possible independent tasks. Rules:\n"
    "- Break compound sentences into individual actions even if loosely connected.\n"
    "- Each task must be a single, self-contained action.\n"
    "- Preserve the original wording as much as possible.\n"
    "- Output ONLY a numbered list (1. ... 2. ...). No explanations.\n"
    "- Do NOT merge or rephrase tasks beyond minimal cleanup.\n"
    "- Prefer MORE splits over fewer."
)


def split_via_groq(text: str, *, force_split: bool = False) -> List[str]:
    """Split text into tasks using Groq LLM. Returns [text] if API unavailable."""
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        print("[WARN] GROQ_API_KEY not set. Returning text as single task.", file=sys.stderr)
        return [text]

    system = _SPLIT_SYSTEM_PROMPT_FORCE if force_split else _SPLIT_SYSTEM_PROMPT
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": text},
    ]
    try:
        response = _groq_chat(messages, api_key)
        tasks = _parse_numbered_response(response)
        return tasks if tasks else [text]
    except Exception as e:
        print(f"[WARN] Groq split failed: {e}. Returning text as single task.", file=sys.stderr)
        return [text]

def extract_tasks(full_text: str, *, force_split: bool = False) -> List[str]:
    t = _norm(full_text)
    t = _strip_leading_punct(t)
    t = _strip_router_boilerplate(t)
    t = re.sub(r"^\s*\uc9c0\uae08\ubd80\ud130\s+\uc5f0\uc18d\uc801\uc73c\ub85c\s+\uc218\uc815\ud560\s+\uc774\uc288\s*[:\-]?\s*", "", t)
    if is_numbered(t):
        return [_strip_leading_punct(p) for p in split_numbered(t) if _strip_leading_punct(p)]
    return [_strip_leading_punct(p) for p in split_via_groq(t, force_split=force_split) if _strip_leading_punct(p)]

def summarize(task: str, n: int = 80) -> str:
    s = re.sub(r"\s+", " ", task.strip())
    return s if len(s) <= n else s[: n - 1].rstrip() + "\u2026"

# -------------------------
# Merge / Max tickets control
# -------------------------

def apply_max_tickets(tasks: List[str], max_tickets: int) -> List[str]:
    if max_tickets <= 0 or len(tasks) <= max_tickets:
        return tasks
    head = tasks[: max_tickets - 1]
    tail = tasks[max_tickets - 1 :]
    merged = " / ".join(tail)
    return head + [merged]

def apply_merge_spec(tasks: List[str], merge_spec: str) -> List[str]:
    if not merge_spec:
        return tasks
    m = re.match(r"^\s*([A-Za-z])\s*\+\s*([A-Za-z])\s*$", merge_spec)
    if not m:
        return tasks
    a, b = m.group(1).upper(), m.group(2).upper()
    indexed = [(chr(ord("A")+i), t) for i, t in enumerate(tasks)]
    a_idx = next((i for i,(tid,_) in enumerate(indexed) if tid==a), None)
    b_idx = next((i for i,(tid,_) in enumerate(indexed) if tid==b), None)
    if a_idx is None or b_idx is None or a_idx == b_idx:
        return tasks
    lo, hi = min(a_idx,b_idx), max(a_idx,b_idx)
    merged = indexed[lo][1] + " / " + indexed[hi][1]
    new = []
    for i,(tid,txt) in enumerate(indexed):
        if i == lo:
            new.append(merged)
        elif i == hi:
            continue
        else:
            new.append(txt)
    return new

# -------------------------
# Prompt builders (phase + economy + safety)
# -------------------------

def build_change_log_stub(ticket_id: str) -> str:
    return ""

def next_session_starter(ticket_id: str, summary_line: str) -> str:
    return f"{ticket_id}: {summary_line}"

def build_prompt_desktop(ticket_id: str, task: str, *, economy: str, phase: str) -> str:
    return task.strip() + "\n"

def build_prompt_opus_only(ticket_id: str, task: str) -> str:
    return task.strip() + "\n"

# -------------------------
# Notes + Session Guard
# -------------------------

def global_notes(full_text: str) -> List[str]:
    return []

def session_guard(n_tasks: int, economy: str, phase: str) -> List[str]:
    g = []
    if n_tasks <= 1:
        g.append("OK: single-ticket session recommended (lowest cost, lowest risk).")
        if phase == "implement":
            g.append("After finishing: append change_log and STOP. Start a NEW session for the next ticket.")
        return g

    g.append(f"Detected {n_tasks} tickets. Do NOT implement all in one session.")
    g.append("Recommended: run ONE ticket per session (Implement -> change_log -> STOP -> New session).")
    g.append("Tip: use --one-task B to re-run only one ticket for rework.")
    if economy == "strict":
        g.append("Economy strict: multi-ticket sessions cause cost spikes + regressions. Avoid.")
    return g[:10]

# -------------------------
# Rendering
# -------------------------

def print_friendly(out: RouterOutput, *, desktop_edit: bool, economy: str, phase: str, opus_only: bool) -> None:
    if len(out.tasks) > 1:
        print(f"[{len(out.tasks)} tickets] Run one at a time. A -> finish -> new session -> B")
    if out.global_notes:
        for n in out.global_notes:
            print(f"! {n}")
    for t in out.tasks:
        print(f"\nTicket {t.id} -- {t.summary}")
        print(f"[{t.route.upper()} {t.confidence:.0%}]")
        print("\n[Copy and paste to Claude]")
        print("```")
        print(t.claude_prompt.strip())
        print("```")
        print(f"next: {t.next_session_starter}")
    print()

def print_human(out: RouterOutput, *, desktop_edit: bool, economy: str, phase: str, opus_only: bool) -> None:
    mode = "OPUS" if opus_only else ("DE" if desktop_edit else "N")
    print(f"ROUTER v4.0 | {mode} {economy[0].upper()} {phase[0].upper()} | {out.route.upper()} {out.confidence:.0%}")
    for n in out.global_notes:
        print(f"! {n}")
    for s in out.session_guard:
        print(f"# {s}")
    for t in out.tasks:
        print(f"\n[{t.id}] p{t.priority} {t.summary}")
        print(f"  route={t.route} {t.confidence:.0%} | {', '.join(t.reasons[:2])}")
        print("\n[Copy and paste to Claude]")
        print("```")
        print(t.claude_prompt.strip())
        print("```")
        print(f"  next: {t.next_session_starter}")
        print(f"  log: {t.change_log_stub.strip()}")

def render_tickets_md(out: RouterOutput, *, economy: str, phase: str) -> str:
    lines = []
    lines.append("# TICKETS")
    lines.append("")
    lines.append(f"- Economy: **{economy.upper()}**")
    lines.append(f"- Phase: **{phase.upper()}**")
    lines.append("")
    if out.global_notes:
        lines.append("## Global Notes")
        for n in out.global_notes:
            lines.append(f"- {n}")
        lines.append("")
    lines.append("## Session Guard")
    for g in out.session_guard:
        lines.append(f"- {g}")
    lines.append("")
    lines.append("## Tasks")
    for t in out.tasks:
        lines.append("")
        lines.append(f"### [{t.id}] (priority {t.priority}) {t.summary}")
        lines.append(f"- Route: **{t.route.upper()}** (confidence: {t.confidence:.2f})")
        lines.append(f"- Next session: `{t.next_session_starter}`")
    lines.append("")
    return "\n".join(lines)

def save_text(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def filter_one_task(out: RouterOutput, tid: str) -> RouterOutput:
    tid = tid.strip().upper()
    tasks = [t for t in out.tasks if t.id.upper() == tid]
    if tasks:
        return RouterOutput(out.route, out.confidence, out.reasons, out.global_notes, out.session_guard, tasks)
    guard = out.session_guard[:] + [f"Warning: --one-task {tid} not found. Available: {', '.join([x.id for x in out.tasks])}"]
    return RouterOutput(out.route, out.confidence, out.reasons, out.global_notes, guard, out.tasks)

# -------------------------
# Main routing
# -------------------------

def apply_min_tickets(tasks: List[str], min_tickets: int, full_text: str, *, force_split: bool = False) -> List[str]:
    """Ensure at least min_tickets tasks. If fewer, try harder to split the largest task."""
    if min_tickets <= 0 or len(tasks) >= min_tickets:
        return tasks
    while len(tasks) < min_tickets:
        longest_idx = max(range(len(tasks)), key=lambda i: len(tasks[i]))
        longest = tasks[longest_idx]
        sub = split_via_groq(longest, force_split=True)
        if len(sub) > 1:
            tasks = tasks[:longest_idx] + sub + tasks[longest_idx + 1:]
        else:
            break
    return tasks


def route_text(full_text: str, *, desktop_edit: bool, economy: str, phase: str, opus_only: bool,
              max_tickets: int, merge_spec: str, force_split: bool = False, min_tickets: int = 0) -> RouterOutput:
    text = _norm(full_text)
    text = _strip_router_boilerplate(text)
    tasks = extract_tasks(text, force_split=force_split)
    tasks = [_strip_leading_punct(t) for t in tasks if _strip_leading_punct(t)]
    tasks = apply_merge_spec(tasks, merge_spec)
    tasks = apply_min_tickets(tasks, min_tickets, text, force_split=force_split)
    tasks = apply_max_tickets(tasks, max_tickets)

    # No domain-specific sorting -- preserve input order
    decisions: List[TaskDecision] = []

    for i, task in enumerate(tasks, start=1):
        tid = chr(ord("A") + i - 1) if i <= 26 else f"T{i}"
        priority = i  # order-based priority
        summary_line = summarize(task)

        route = "claude"
        conf = 0.85
        reasons = ["Primary route"]

        if opus_only:
            prompt = build_prompt_opus_only(tid, task)
        elif desktop_edit:
            prompt = build_prompt_desktop(tid, task, economy=economy, phase=phase)
        else:
            prompt = task.strip() + "\n"

        decisions.append(TaskDecision(
            id=tid,
            summary=summary_line,
            route=route,
            confidence=conf,
            priority=priority,
            reasons=reasons,
            claude_prompt=prompt,
            next_session_starter=next_session_starter(tid, summary_line),
            change_log_stub=build_change_log_stub(tid),
        ))

    overall_route = "claude"
    overall_conf = 0.85
    reasons = ["All tasks routed to Claude"]

    # Record task history (must not break routing)
    try:
        record_tasks(decisions)
    except Exception:
        pass
    return RouterOutput(
        route=overall_route,
        confidence=overall_conf,
        reasons=reasons,
        global_notes=global_notes(text),
        session_guard=session_guard(len(decisions), economy, phase),
        tasks=decisions,
    )

def parse_flag_value(args: List[str], flag: str) -> Tuple[List[str], Optional[str]]:
    if flag not in args:
        return args, None
    i = args.index(flag)
    if i == len(args) - 1:
        return [a for a in args if a != flag], None
    val = args[i+1]
    return args[:i] + args[i+2:], val

def main() -> int:
    args = sys.argv[1:]

    output_json = "--json" in args
    desktop_edit = "--desktop-edit" in args
    opus_only = "--opus-only" in args
    tickets_md = "--tickets-md" in args
    friendly = "--friendly" in args
    force_split = "--force-split" in args

    args, economy = parse_flag_value(args, "--economy")
    economy = (economy or "strict").strip().lower()
    if economy not in {"strict", "balanced"}:
        economy = "strict"

    args, phase = parse_flag_value(args, "--phase")
    phase = (phase or "implement").strip().lower()
    if phase not in {"analyze", "implement"}:
        phase = "implement"

    args, one_task = parse_flag_value(args, "--one-task")
    args, save_tickets = parse_flag_value(args, "--save-tickets")

    args, max_tickets = parse_flag_value(args, "--max-tickets")
    try:
        max_tickets_n = int(max_tickets) if max_tickets else 0
    except (ValueError, TypeError):
        max_tickets_n = 0

    args, min_tickets = parse_flag_value(args, "--min-tickets")
    try:
        min_tickets_n = int(min_tickets) if min_tickets else 0
    except (ValueError, TypeError):
        min_tickets_n = 0

    args, merge_spec = parse_flag_value(args, "--merge")
    merge_spec = merge_spec or ""

    # remove simple flags
    simple = {"--json","--desktop-edit","--opus-only","--tickets-md","--friendly","--force-split"}
    args = [a for a in args if a not in simple]

    if not args:
        print("Usage:")
        print("  python llm_router.py --friendly \"<request>\"")
        print("  python llm_router.py --desktop-edit --economy strict --phase implement \"<request>\"")
        print("  python llm_router.py --one-task B --desktop-edit \"<request>\"")
        print("  python llm_router.py --max-tickets 4 --merge \"A+B\" --desktop-edit \"<request>\"")
        print("  python llm_router.py --tickets-md --save-tickets TICKETS.md \"<request>\"")
        print("  python llm_router.py --opus-only \"<request>\"")
        return 2

    user_text = sys.stdin.read() if args[0] == "-" else " ".join(args)
    out = route_text(
        user_text,
        desktop_edit=desktop_edit,
        economy=economy,
        phase=phase,
        opus_only=opus_only,
        max_tickets=max_tickets_n,
        merge_spec=merge_spec,
        force_split=force_split,
        min_tickets=min_tickets_n,
    )

    if one_task:
        out = filter_one_task(out, one_task)

    if output_json:
        print(json.dumps(asdict(out), ensure_ascii=False, indent=2))
        return 0

    if tickets_md or save_tickets:
        md = render_tickets_md(out, economy=economy, phase=phase)
        if save_tickets:
            save_text(save_tickets, md)
            print(f"Saved tickets to: {save_tickets}")
        else:
            print(md)
        return 0

    if friendly:
        print_friendly(out, desktop_edit=desktop_edit, economy=economy, phase=phase, opus_only=opus_only)
    else:
        print_human(out, desktop_edit=desktop_edit, economy=economy, phase=phase, opus_only=opus_only)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
