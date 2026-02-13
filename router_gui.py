#!/usr/bin/env python3
import os, sys, glob, subprocess, re, tkinter as tk
import json
import urllib.request
import urllib.error
from typing import List, Dict, Tuple
from tkinter import ttk, filedialog, messagebox, simpledialog

APP_TITLE = "LLM Router GUI v2.0"

def find_router_candidates() -> List[str]:
    """Find router scripts reliably.

    Search is based on the directory where this GUI file lives (script dir),
    so it works even when the user launches the GUI from another cwd.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))

    patterns = [
        # Same folder as GUI
        os.path.join(script_dir, "llm_router*.py"),

        # routers/ folder under GUI folder (recommended for multi-project)
        os.path.join(script_dir, "routers", "*.py"),
        os.path.join(script_dir, "routers", "*router*.py"),

        # tools/ subfolder under GUI folder
        os.path.join(script_dir, "tools", "llm_router*.py"),
    ]

    found: List[str] = []
    for p in patterns:
        found.extend(glob.glob(p))

    # Deduplicate + keep stable order
    uniq: List[str] = []
    for f in found:
        af = os.path.abspath(f)
        if af not in uniq and os.path.isfile(af):
            uniq.append(af)
    return uniq

def git_status_summary(cwd: str) -> str:
    try:
        r = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=cwd)
        if r.returncode != 0:
            return "git not available here"
        out = r.stdout.strip()
        return "clean" if not out else "DIRTY (uncommitted changes)"
    except:
        return "git check failed"

TRANSLATE_MAP = {
    "[BEGINNER MODE READY]": "[BEGINNER MODE READY]",
    "[BEGINNER MODE]": "[BEGINNER MODE]",
    "요청 텍스트를 입력해줘.": "Enter request.",
    "출력이 없어.": "No output.",
    "복사할 출력이 없어.": "No output.",
    "복사 완료.": "Copied.",
    "Claude 복사 블록을 찾지 못했어.": "No ``` block found.",
    "Claude에 붙여넣을 블록만 복사했어.": "Block copied.",
    "복사할 내용이 없어.": "Nothing to copy.",
    "❌ 실행 실패:": "❌ Failed:",
    "⚠️ Router not found.": "⚠️ Router not found.",
    "- Click 'Browse…' and select your router script (.py).": "- Browse → select .py",
    "- Recommended: put routers in tools/routers/": "- Use tools/routers/",
    "Refreshed router list.": "Refreshed.",
    "Found": "Found",
    "file(s).": "file(s).",
    "GUI dir": "GUI dir",
    "Tip: For multi-project, put routers in tools/routers/": "Tip: tools/routers/ for multi-project",
    "1️⃣ 아래 Output에서 '```' 로 감싸진 블록만 복사하세요.": "1️⃣ Copy ``` block only",
    "2️⃣ Claude 새 세션에 붙여넣고 실행하세요.": "2️⃣ Paste → new session → run",
    "3️⃣ 완료 후 새 세션에서 다음 Ticket 실행하세요.": "3️⃣ Next ticket → new session",
}


def translate_non_code_to_english(text: str) -> str:
    """Best-effort UI translation: only translate known Korean UI strings.

    IMPORTANT: Do not change code blocks. Only treat lines starting with ```
    as real fence boundaries (not inline backticks in prose).
    """
    lines = text.splitlines()
    in_fence = False
    out_lines = []
    for line in lines:
        if line.strip().startswith("```"):
            in_fence = not in_fence
            out_lines.append(line)
            continue
        if in_fence:
            out_lines.append(line)
            continue
        # Translate only outside fenced blocks
        translated = line
        for k, v in TRANSLATE_MAP.items():
            translated = translated.replace(k, v)
        out_lines.append(translated)
    return "\n".join(out_lines)


def _contains_korean(text: str) -> bool:
    """Check if text contains Korean (Hangul) characters."""
    return any('\uac00' <= c <= '\ud7af' for c in text)


def translate_output_via_groq(text: str, api_key: str) -> str:
    """Translate non-code Korean text to English via Groq API (fence-safe).

    - Splits output into fenced (code) and non-fenced segments.
    - Only sends non-fenced segments containing Korean to Groq.
    - Preserves all fenced code blocks untouched.
    - Falls back to original text on any API error.
    """
    lines = text.splitlines()
    in_fence = False

    # Phase 1: split into segments — (is_code, [lines])
    segments: List[Tuple[bool, List[str]]] = []
    buf: List[str] = []

    for line in lines:
        if line.strip().startswith("```"):
            if not in_fence:
                # Opening fence — flush non-fenced buf
                if buf:
                    segments.append((False, buf))
                    buf = []
                in_fence = True
                buf = [line]
            else:
                # Closing fence — flush fenced buf
                buf.append(line)
                segments.append((True, buf))
                buf = []
                in_fence = False
            continue
        buf.append(line)
    if buf:
        segments.append((in_fence, buf))

    # Phase 2: identify non-fenced segments with Korean
    to_translate: Dict[int, str] = {}
    for i, (is_code, seg_lines) in enumerate(segments):
        if not is_code:
            chunk = "\n".join(seg_lines)
            if _contains_korean(chunk):
                to_translate[i] = chunk

    if not to_translate:
        return text  # Nothing to translate

    # Phase 3: batch translate via Groq with segment markers
    prompt_parts = []
    for idx, chunk in sorted(to_translate.items()):
        prompt_parts.append(f"---SEGMENT {idx}---\n{chunk}")
    combined = "\n\n".join(prompt_parts)

    system = (
        "Translate Korean to concise English. "
        "Keep: English text, technical terms, paths, commands, emoji, markers. "
        "Preserve line structure. "
        "Output: ---SEGMENT N--- headers."
    )

    try:
        result = _groq_chat(
            [{"role": "system", "content": system}, {"role": "user", "content": combined}],
            api_key=api_key,
            max_tokens=2000,
            temperature=0.1,
        )
    except Exception:
        return text  # Silently fall back to original

    # Phase 4: parse translated segments from response
    import re
    translated_segs: Dict[int, str] = {}
    parts = re.split(r'---SEGMENT\s+(\d+)---\n?', result)
    for i in range(1, len(parts) - 1, 2):
        seg_idx = int(parts[i])
        seg_text = parts[i + 1].rstrip("\n")
        if seg_idx in to_translate:
            translated_segs[seg_idx] = seg_text

    # Phase 5: reassemble with translated segments
    for idx, translated_text in translated_segs.items():
        if idx < len(segments):
            is_code, _ = segments[idx]
            if not is_code:
                segments[idx] = (False, translated_text.splitlines())

    out: List[str] = []
    for _, seg_lines in segments:
        out.extend(seg_lines)
    return "\n".join(out)


IMPL_RULES_SUFFIX = ""


def translate_block_to_english(block: str, api_key: str) -> str:
    """Translate Korean lines to English, keeping non-Korean lines intact.

    Translates line-by-line to preserve structure exactly.
    """
    lines = block.splitlines()
    kr_indices: List[int] = []
    for i, line in enumerate(lines):
        if _contains_korean(line):
            kr_indices.append(i)

    if not kr_indices:
        return block

    # Build 1-based numbered translation request
    numbered = "\n".join(f"{n+1}:{lines[idx]}" for n, idx in enumerate(kr_indices))
    system = (
        "Translate each numbered Korean line to concise English.\n"
        "Output ONLY: same numbered lines translated. Example:\n"
        "1:Fix the login screen.\n2:Fix gallery bug.\n"
        "Keep markers ([LOG] etc), symbols, paths. No extra text."
    )
    try:
        result = _groq_chat(
            [{"role": "system", "content": system}, {"role": "user", "content": numbered}],
            api_key=api_key,
            max_tokens=300,
            temperature=0.0,
        )
        # Parse "N:translated" responses (1-based → map back to kr_indices)
        for resp_line in result.strip().splitlines():
            resp_line = resp_line.strip()
            if not resp_line:
                continue
            m = re.match(r'^(\d+)\s*[:.]\s*(.+)$', resp_line)
            if m:
                n = int(m.group(1)) - 1  # 1-based → 0-based
                translated = m.group(2).strip()
                if 0 <= n < len(kr_indices) and translated:
                    lines[kr_indices[n]] = translated
        return "\n".join(lines)
    except Exception:
        return block


# === Groq helpers for ticket translation (low-cost) ===
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"


def _groq_chat(messages, api_key: str, model: str = DEFAULT_GROQ_MODEL, max_tokens: int = 300, temperature: float = 0.0) -> str:
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
            "User-Agent": "RouterGUI/1.0",
        },
        method="POST",
    )
    # Use certifi CA bundle if available (fixes SSL on macOS with Python 3.14+)
    ssl_ctx = None
    try:
        import certifi, ssl
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    with urllib.request.urlopen(req, timeout=25, context=ssl_ctx) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    obj = json.loads(raw)
    return obj["choices"][0]["message"]["content"]


def extract_tickets_from_claude_block(block: str) -> Tuple[Dict[str, str], str]:
    """Extract Ticket blocks (fence-aware).

    Returns (tickets_map, original_request_kr_single_line)
    - tickets_map: {"A": "...ticket text...", "B": "..."}
    - original_request_kr_single_line: best-effort extracted Korean line if present

    IMPORTANT:
    - Ignore any "Ticket X:" occurrences INSIDE fenced code blocks.
      (Because the Claude-ready block itself often contains "Ticket A:" inside ```...```.)
    """
    lines = block.splitlines()
    tickets: Dict[str, str] = {}
    cur_id = None
    buf: List[str] = []
    original_kr = ""

    in_fence = False

    def flush():
        nonlocal cur_id, buf
        if cur_id is not None:
            text = "\n".join(buf).strip()
            if text:
                tickets[cur_id] = text
        cur_id = None
        buf = []

    for i, line in enumerate(lines):
        s = line.strip()

        # Toggle fenced code block state
        if s.startswith("```"):
            in_fence = not in_fence
            # keep scanning but do not parse ticket markers inside fences
            continue

        # Try to capture original KR request line if present (outside fences only)
        if (not in_fence) and s.lower().startswith("original request") and ("kr" in s.lower()):
            for j in range(i + 1, len(lines)):
                t = lines[j].strip()
                if t and (not t.startswith("```")):
                    original_kr = t.replace("\n", " ")
                    break

        # Ignore "Ticket ..." parsing inside fences
        if in_fence:
            # If currently collecting a ticket body (outside fences), we still shouldn't append fenced content here.
            # But safe approach: just append line to buffer only if we are inside a ticket and we are NOT in_fence.
            continue

        # Ticket start patterns (outside fences only)
        if s.startswith("Ticket "):
            # e.g., "Ticket A:" or "Ticket A"
            parts = s.split()
            if len(parts) >= 2:
                tid = parts[1].rstrip(":").strip()
                if len(tid) == 1 and tid.isalpha():
                    flush()
                    cur_id = tid.upper()
                    # If inline content after colon exists
                    if ":" in s:
                        after = s.split(":", 1)[1].strip()
                        if after:
                            buf.append(after)
                    continue

        # End conditions (outside fences only)
        if cur_id and (
            s == "" or
            s.startswith("Change log stub") or
            s.startswith("→") or
            s.startswith("Change log") or
            s.startswith("Next session") or
            s.startswith("Rules:")
        ):
            flush()
            continue

        # Accumulate ticket body (outside fences only)
        if cur_id:
            buf.append(line)

    flush()
    return tickets, original_kr


def rewrite_tickets_to_english_via_groq(tickets: Dict[str, str], original_kr: str, api_key: str) -> Dict[str, str]:
    """Use Groq to rewrite each ticket into concise English, preserving meaning."""
    if not tickets:
        return {}

    # Build a compact JSON input
    ticket_items = [{"id": k, "text": v} for k, v in tickets.items()]
    kr_line = (original_kr or "").strip()

    system = (
        "Normalize tickets to concise English. "
        "Keep exact meaning. No new steps. No invented details. "
        "JSON: {\"tickets\":[{\"id\":\"A\",\"en\":\"...\"},...],\"kr\":\"...\"}"
    )

    user = {
        "tickets": ticket_items,
        "kr": kr_line,
    }

    content = _groq_chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        api_key=api_key,
        model=DEFAULT_GROQ_MODEL,
        max_tokens=450,
        temperature=0.0,
    )

    # Parse JSON safely
    try:
        obj = json.loads(content)
    except Exception:
        # Fallback: try to extract JSON substring
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            obj = json.loads(content[start:end+1])
        else:
            raise

    out: Dict[str, str] = {}
    for item in obj.get("tickets", []):
        tid = str(item.get("id", "")).strip().upper()
        en = str(item.get("en", "")).strip()
        if tid and en:
            out[tid] = en

    # If Groq returned KR one-line, use it
    if obj.get("kr"):
        out["__KR__"] = str(obj.get("kr")).strip().replace("\n", " ")

    return out

def apply_english_tickets_to_claude_block(block: str, en_map: Dict[str, str]) -> str:
    """Replace Ticket bodies with English versions and attach one-line KR when available.

    IMPORTANT (fence-aware):
    - Do NOT treat "Ticket A:" text inside ```...``` as a ticket header.
    """
    if not en_map:
        return block

    lines = block.splitlines()
    out_lines: List[str] = []

    kr_line = en_map.get("__KR__", "").strip()

    cur_id = None
    skipping = False
    in_fence = False

    def is_ticket_start(line: str) -> Tuple[bool, str, str]:
        s2 = line.strip()
        if s2.startswith("Ticket "):
            parts = s2.split()
            if len(parts) >= 2:
                tid = parts[1].rstrip(":").strip()
                if len(tid) == 1 and tid.isalpha():
                    prefix = s2.split(":", 1)[0]
                    return True, tid.upper(), prefix
        return False, "", ""

    for line in lines:
        s = line.strip()

        # Toggle fenced code block state
        if s.startswith("```"):
            in_fence = not in_fence
            out_lines.append(line)
            continue

        # Never interpret ticket headers inside fences
        if in_fence:
            out_lines.append(line)
            continue

        start, tid, prefix = is_ticket_start(line)
        if start:
            cur_id = tid
            skipping = True

            # Emit header
            out_lines.append(prefix + ":")

            # Emit English body
            en = en_map.get(tid, "").strip()
            if en:
                out_lines.append(en)

            # Optional KR line
            if kr_line:
                out_lines.append("")
                out_lines.append("Original request (KR):")
                out_lines.append(kr_line)

            out_lines.append("")
            continue

        if skipping and cur_id:
            # Stop skipping on section delimiters
            if (
                s == "" or
                s.startswith("Change log stub") or
                s.startswith("→") or
                s.startswith("Rules:") or
                s.startswith("Next session")
            ):
                skipping = False
                cur_id = None
                out_lines.append(line)
            else:
                # Skip original ticket body lines
                continue
        else:
            out_lines.append(line)

    return "\n".join(out_lines)


def detect_ticket_ids(full_text: str):
    """Return unique ticket IDs found in headings like 'Ticket A' or 'Ticket B — ...'.

    Fence-aware: ignores 'Ticket X' lines inside ```...``` code blocks.
    """
    import re
    lines = full_text.splitlines()
    in_fence = False
    uniq = []
    for line in lines:
        s = line.strip()
        if s.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = re.match(r"^\s*Ticket\s+([A-Za-z])\b", line)
        if m:
            x = m.group(1).upper()
            if x not in uniq:
                uniq.append(x)
    return uniq

def extract_claude_ready_block_from_output(full_text: str, ticket_id: str = "") -> str:
    """
    Extract the Claude-ready payload from GUI Output.

    Robust version:
    - Ignores quoted '```' inside prose
    - Works even if fenced block is missing
    - Properly isolates each Ticket section
    """

    tid = (ticket_id or "").strip().upper()
    lines = full_text.splitlines()

    # -----------------------------
    # Helper: detect Ticket header
    # -----------------------------
    def is_ticket_heading(line: str) -> str:
        s = line.strip()
        if s.startswith("Ticket "):
            parts = s.split()
            if len(parts) >= 2:
                cand = parts[1].rstrip(":").strip()
                if len(cand) == 1 and cand.isalpha():
                    return cand.upper()
        return ""

    # -----------------------------
    # 1) Locate ticket sections (fence-aware)
    # -----------------------------
    ticket_sections = []  # (start_idx, ticket_id)
    in_fence = False
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        t = is_ticket_heading(line)
        if t:
            ticket_sections.append((i, t))

    ticket_sections.append((len(lines), ""))  # sentinel

    # -----------------------------
    # 2) Extract from a ticket range
    # -----------------------------
    def extract_from_range(start: int, end: int) -> str:

        # A) Look for fenced block AFTER copy marker
        for i in range(start, end):
            if "[복사해서 Claude에 붙여넣기]" in lines[i] or "[Copy/Paste]" in lines[i]:

                # Search for real fenced block (line-based)
                for j in range(i + 1, end):
                    if lines[j].strip().startswith("```"):
                        buf = []
                        for k in range(j + 1, end):
                            if lines[k].strip().startswith("```"):
                                return "\n".join(buf).strip()
                            buf.append(lines[k])
                        break  # no closing fence

                # Fallback: no fenced block → capture section text directly
                buf = []
                m = i + 1
                if m < end and lines[m].strip() == "":
                    m += 1

                while m < end:
                    s2 = lines[m].strip()

                    if s2.startswith("Ticket "):
                        break
                    if s2.startswith("Route:"):
                        break
                    if s2.startswith("[다음 세션") or s2.startswith("[Next session"):
                        break
                    if set(s2) == {"-"} and len(s2) >= 20:
                        break
                    if set(s2) == {"="} and len(s2) >= 20:
                        break

                    if s2:
                        buf.append(lines[m])

                    m += 1

                if buf:
                    return "\n".join(buf).strip()

        # B) Secondary: first REAL fenced block in range
        for i in range(start, end):
            if lines[i].strip().startswith("```"):
                buf = []
                for k in range(i + 1, end):
                    if lines[k].strip().startswith("```"):
                        return "\n".join(buf).strip()
                    buf.append(lines[k])
                break

        return ""

    # -----------------------------
    # 3) Extract specific ticket
    # -----------------------------
    if ticket_sections:
        for idx in range(len(ticket_sections) - 1):
            s_i, s_tid = ticket_sections[idx]
            e_i, _ = ticket_sections[idx + 1]

            if tid and s_tid != tid:
                continue

            block = extract_from_range(s_i, e_i)
            if block:
                return block

        # If no specific tid requested → use first ticket
        if not tid and len(ticket_sections) > 1:
            s_i, _ = ticket_sections[0]
            e_i, _ = ticket_sections[1]
            block = extract_from_range(s_i, e_i)
            if block:
                return block

    # -----------------------------
    # 4) Global fallback (STRICT line-based)
    # -----------------------------
    for i, line in enumerate(lines):
        if line.strip().startswith("```"):
            buf = []
            for k in range(i + 1, len(lines)):
                if lines[k].strip().startswith("```"):
                    return "\n".join(buf).strip()
                buf.append(lines[k])
            break

    return ""


# --- Helpers: fallback recovery from full Output ---
def recover_ticket_chunk_from_output(full_text: str, ticket_id: str) -> str:
    """Recover the FULL Claude-ready fenced chunk that contains `Ticket <id>:`.

    Returns text starting at `Ticket <id>:` through the end of the fenced chunk.
    Uses line-based fence detection (only lines starting with ``` count as fences).
    """
    tid = (ticket_id or "").strip().upper() or "A"
    marker = f"Ticket {tid}:"

    lines = full_text.splitlines()
    # Collect fenced chunks using line-based fence detection
    chunks: list = []
    in_fence = False
    buf: list = []
    for line in lines:
        if line.strip().startswith("```"):
            if in_fence:
                chunks.append("\n".join(buf))
                buf = []
            in_fence = not in_fence
            continue
        if in_fence:
            buf.append(line)

    for chunk in chunks:
        if marker in chunk:
            start = chunk.find(marker)
            return chunk[start:].strip()
    return ""


def recover_change_log_stub_from_output(full_text: str, ticket_id: str) -> str:
    """Recover just the Change log stub section for a given ticket from any fenced chunk."""
    tid = (ticket_id or "").strip().upper() or "A"
    chunk = recover_ticket_chunk_from_output(full_text, tid)
    if not chunk:
        return ""

    key = "Change log stub:"
    if key not in chunk:
        return ""

    # Return from Change log stub: to end (usually includes the template)
    return chunk[chunk.find(key):].strip()

# --- Helper: slice only one ticket section from a Claude-ready block ---
def slice_single_ticket_from_block(block: str, ticket_id: str) -> str:
    """Slice only one ticket section from a Claude-ready block.

    Works even if the block contains multiple tickets.
    Returns content from 'Ticket X:' through (and including) 'Change log stub:' if present.
    """
    tid = (ticket_id or "").strip().upper() or "A"
    lines = block.splitlines()

    start_idx = None
    in_fence = False

    # Find the Ticket header outside nested fences (if any)
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if s.startswith(f"Ticket {tid}"):
            start_idx = i
            break

    if start_idx is None:
        return block.strip()

    out = []
    slice_fence = False
    for j in range(start_idx, len(lines)):
        s = lines[j].strip()

        if s.startswith("```"):
            slice_fence = not slice_fence
            out.append(lines[j])
            continue

        # Stop at next ticket header only outside fences
        if not slice_fence and j != start_idx and s.startswith("Ticket "):
            break

        out.append(lines[j])

    sliced = "\n".join(out).strip()

    # If sliced doesn't include Change log stub but the original block has it later, try to append it.
    if "Change log stub" not in sliced and "Change log stub" in block:
        # Append from the first occurrence of 'Change log stub:' after start_idx until end of stub template.
        for k in range(start_idx, len(lines)):
            if lines[k].strip().startswith("Change log stub"):
                tail = []
                for m in range(k, len(lines)):
                    s2 = lines[m].strip()
                    # stop at next ticket heading
                    if m != k and s2.startswith("Ticket "):
                        break
                    tail.append(lines[m])
                if tail:
                    sliced = (sliced + "\n\n" + "\n".join(tail).strip()).strip()
                break

    return sliced

class RouterGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1040x820")

        self.router_files = find_router_candidates()
        self.router_label_to_path = {}  # label -> absolute path
        self.router_labels = []         # dropdown labels

        for p in self.router_files:
            base = os.path.basename(p)
            # Friendly label: filename + short folder hint
            rel = os.path.relpath(p, os.path.dirname(os.path.abspath(__file__)))
            label = f"{base}  ({rel})"
            self.router_label_to_path[label] = p
            self.router_labels.append(label)

        self.router_var = tk.StringVar(value=self.router_labels[0] if self.router_labels else "")

        self.desktop_edit_var = tk.BooleanVar(value=True)
        self.opus_only_var = tk.BooleanVar(value=False)
        self.tickets_md_var = tk.BooleanVar(value=False)
        self.translate_en_var = tk.BooleanVar(value=True)
        # Low-cost translation of Ticket bodies inside the Claude block (uses GROQ_API_KEY)
        self.ticket_groq_translate_var = tk.BooleanVar(value=True)
        self.friendly_var = tk.BooleanVar(value=True)
        self.force_split_var = tk.BooleanVar(value=True)
        self.min_tickets_var = tk.StringVar(value="0")

        self.economy_var = tk.StringVar(value="strict")
        self.phase_var = tk.StringVar(value="implement")

        self.one_task_var = tk.StringVar(value="")
        self.save_tickets_var = tk.StringVar(value="")
        self.max_tickets_var = tk.StringVar(value="0")
        self.merge_var = tk.StringVar(value="")

        self._build_ui()
        self._install_edit_shortcuts_and_context_menu()

        # Show a visible banner so users know beginner mode is active
        self._show_startup_banner()
    def _install_edit_shortcuts_and_context_menu(self):
        """Make paste/copy/cut/select-all work consistently + add right-click menu."""
        # Context menu
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Cut", command=lambda: self.focus_get().event_generate("<<Cut>>"))
        menu.add_command(label="Copy", command=lambda: self.focus_get().event_generate("<<Copy>>"))
        menu.add_command(label="Paste", command=lambda: self.focus_get().event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="Select All", command=lambda: self._select_all_in_focused_widget())

        def show_menu(event):
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        # Bind right-click (Windows/Linux) and Ctrl-click (macOS)
        for w in [self.input_text, self.output_text]:
            w.bind("<Button-3>", show_menu)
            w.bind("<Control-Button-1>", show_menu)

        # Keyboard shortcuts (Cmd on macOS, Ctrl elsewhere)
        for seq in ("<Command-v>", "<Control-v>"):
            self.input_text.bind(seq, lambda e: (self.input_text.event_generate("<<Paste>>"), "break"))
        for seq in ("<Command-c>", "<Control-c>"):
            self.input_text.bind(seq, lambda e: (self.input_text.event_generate("<<Copy>>"), "break"))
        for seq in ("<Command-x>", "<Control-x>"):
            self.input_text.bind(seq, lambda e: (self.input_text.event_generate("<<Cut>>"), "break"))
        for seq in ("<Command-a>", "<Control-a>"):
            self.input_text.bind(seq, lambda e: (self._select_all_widget(self.input_text), "break"))

        # Output box shortcuts too
        for seq in ("<Command-a>", "<Control-a>"):
            self.output_text.bind(seq, lambda e: (self._select_all_widget(self.output_text), "break"))

    def _select_all_widget(self, widget: tk.Text):
        try:
            widget.tag_add("sel", "1.0", "end-1c")
            widget.mark_set("insert", "1.0")
            widget.see("insert")
        except Exception:
            pass

    def _select_all_in_focused_widget(self):
        w = self.focus_get()
        if isinstance(w, tk.Text):
            self._select_all_widget(w)
        elif isinstance(w, ttk.Entry):
            try:
                w.selection_range(0, "end")
                w.icursor(0)
            except Exception:
                pass

    def _build_ui(self):
        top = ttk.Frame(self, padding=12)
        top.pack(fill="x")

        ttk.Label(top, text="Router file").grid(row=0, column=0, sticky="w")
        self.router_combo = ttk.Combobox(
            top,
            textvariable=self.router_var,
            values=self.router_labels,
            state="readonly" if self.router_labels else "disabled",
            width=65,
        )
        self.router_combo.grid(row=0, column=1, sticky="w", padx=(8, 8))
        ttk.Button(top, text="Browse…", command=self.choose_router_file).grid(row=0, column=2, sticky="w")
        ttk.Button(top, text="Refresh", command=self.refresh_router_list).grid(row=0, column=3, sticky="w", padx=(8,0))

        # Safety / preflight
        self.preflight_label = ttk.Label(top, text=f"Preflight: git status = {git_status_summary(os.getcwd())}")
        self.preflight_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=(8,0))

        opts = ttk.Frame(top)
        opts.grid(row=2, column=0, columnspan=3, sticky="w", pady=(12, 0))

        ttk.Checkbutton(opts, text="Beginner copy/paste (--friendly)", variable=self.friendly_var).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(opts, text="Desktop direct-edit (--desktop-edit)", variable=self.desktop_edit_var).grid(row=0, column=1, sticky="w", padx=(16,0))
        ttk.Checkbutton(opts, text="Force split (--force-split)", variable=self.force_split_var).grid(row=0, column=2, sticky="w", padx=(16,0))
        ttk.Checkbutton(opts, text="Opus-only (--opus-only)", variable=self.opus_only_var).grid(row=0, column=3, sticky="w", padx=(16,0))
        ttk.Checkbutton(opts, text="Tickets Markdown (--tickets-md)", variable=self.tickets_md_var).grid(row=0, column=4, sticky="w", padx=(16,0))
        ttk.Checkbutton(opts, text="Translate output to English", variable=self.translate_en_var).grid(row=0, column=5, sticky="w", padx=(16,0))
        ttk.Checkbutton(opts, text="Translate Tickets via Groq (low-cost)", variable=self.ticket_groq_translate_var).grid(row=0, column=6, sticky="w", padx=(16,0))

        ttk.Label(opts, text="Economy").grid(row=1, column=0, sticky="w", pady=(10,0))
        ttk.Combobox(opts, textvariable=self.economy_var, values=["strict", "balanced"], state="readonly", width=10)\
            .grid(row=1, column=1, sticky="w", padx=(16,0), pady=(10,0))

        ttk.Label(opts, text="Phase").grid(row=1, column=2, sticky="w", padx=(16,0), pady=(10,0))
        ttk.Combobox(opts, textvariable=self.phase_var, values=["analyze", "implement"], state="readonly", width=12)\
            .grid(row=1, column=3, sticky="w", padx=(8,0), pady=(10,0))
        ttk.Label(opts, text="Min tickets (--min-tickets)").grid(row=1, column=4, sticky="w", padx=(16,0), pady=(10,0))
        ttk.Entry(opts, textvariable=self.min_tickets_var, width=6).grid(row=1, column=5, sticky="w", padx=(8,0), pady=(10,0))

        ttk.Label(opts, text="One task (--one-task)").grid(row=2, column=0, sticky="w", pady=(10,0))
        ttk.Entry(opts, textvariable=self.one_task_var, width=8).grid(row=2, column=1, sticky="w", padx=(16,0), pady=(10,0))

        ttk.Label(opts, text="Max tickets (--max-tickets)").grid(row=2, column=2, sticky="w", padx=(16,0), pady=(10,0))
        ttk.Entry(opts, textvariable=self.max_tickets_var, width=8).grid(row=2, column=3, sticky="w", padx=(8,0), pady=(10,0))

        ttk.Label(opts, text="Merge (--merge)").grid(row=3, column=0, sticky="w", pady=(10,0))
        ttk.Entry(opts, textvariable=self.merge_var, width=8).grid(row=3, column=1, sticky="w", padx=(16,0), pady=(10,0))
        ttk.Label(opts, text='예: "A+B"').grid(row=3, column=2, sticky="w", padx=(8,0), pady=(10,0))

        ttk.Label(opts, text="Save tickets (--save-tickets)").grid(row=4, column=0, sticky="w", pady=(10,0))
        ttk.Entry(opts, textvariable=self.save_tickets_var, width=50).grid(row=4, column=1, sticky="w", padx=(16,0), pady=(10,0))
        ttk.Button(opts, text="Choose…", command=self.choose_save_path).grid(row=4, column=2, sticky="w", padx=(8,0), pady=(10,0))

        mid = ttk.Frame(self, padding=(12, 0, 12, 12))
        mid.pack(fill="both", expand=True)

        ttk.Label(mid, text="Request text").pack(anchor="w")
        self.input_text = tk.Text(mid, height=12, wrap="word")
        self.input_text.pack(fill="x", expand=False, pady=(6, 12))

        btns = ttk.Frame(mid)
        btns.pack(fill="x", pady=(0, 10))
        ttk.Button(btns, text="Run Router", command=self.run_router).pack(side="left")
        ttk.Button(btns, text="Refresh Preflight", command=self.refresh_preflight).pack(side="left", padx=(8,0))
        ttk.Button(btns, text="Copy Request", command=self.copy_request).pack(side="left", padx=(8,0))
        ttk.Button(btns, text="Clear Input", command=lambda: self._set_text(self.input_text, "")).pack(side="left", padx=(8,0))

        ttk.Button(btns, text="Copy Claude Block", command=self.copy_claude_block).pack(side="right")
        ttk.Button(btns, text="Copy Full Output", command=self.copy_output).pack(side="right", padx=(8,0))
        ttk.Button(btns, text="Clear Output", command=lambda: self._set_text(self.output_text, "")).pack(side="right", padx=(0,8))

        ttk.Label(mid, text="Output  —  Copy ``` block only").pack(anchor="w")
        self.output_text = tk.Text(mid, height=22, wrap="word")
        self.output_text.pack(fill="both", expand=True, pady=(6, 0))

        if not self.router_files:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            self._set_text(
                self.output_text,
                "⚠️ Router not found.\n"
                "Browse → select .py\n"
                "Use tools/routers/\n"
                f"GUI dir: {script_dir}\n"
            )

    def _get_text(self, widget: tk.Text) -> str:
        return widget.get("1.0", "end-1c")

    def _set_text(self, widget: tk.Text, value: str) -> None:
        widget.delete("1.0", "end")
        widget.insert("1.0", value)

    def _show_startup_banner(self):
        banner = (
            "[BEGINNER MODE]\n"
            "Request → Run → Copy Block → Paste to Claude\n\n"
            f"GUI: {os.path.abspath(__file__)}\n"
            f"CWD: {os.getcwd()}\n"
        )
        self._set_text(self.output_text, banner)

    def refresh_preflight(self):
        self.preflight_label.config(text=f"Preflight: git status = {git_status_summary(os.getcwd())}")

    def refresh_router_list(self):
        self.router_files = find_router_candidates()
        self.router_label_to_path = {}
        self.router_labels = []

        base_dir = os.path.dirname(os.path.abspath(__file__))
        for p in self.router_files:
            base = os.path.basename(p)
            rel = os.path.relpath(p, base_dir)
            label = f"{base}  ({rel})"
            self.router_label_to_path[label] = p
            self.router_labels.append(label)

        self.router_combo["values"] = self.router_labels
        if self.router_labels:
            self.router_combo["state"] = "readonly"
            self.router_var.set(self.router_labels[0])
        else:
            self.router_combo["state"] = "disabled"
            self.router_var.set("")

        script_dir = base_dir
        msg = f"Refreshed. Found {len(self.router_files)} file(s).\nGUI: {script_dir}\n"
        if self.router_files:
            msg += "First: " + self.router_files[0] + "\n"
        msg += "\nTip: tools/routers/ for multi-project\n"
        self._set_text(self.output_text, msg)

    def choose_router_file(self):
        path = filedialog.askopenfilename(
            title="Select router script…",
            filetypes=[("Python", "*.py"), ("All files", "*.*")],
            initialdir=os.path.dirname(os.path.abspath(__file__)),
        )
        if not path:
            return
        path = os.path.abspath(path)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base = os.path.basename(path)
        rel = os.path.relpath(path, base_dir)
        label = f"{base}  ({rel})"

        if label not in self.router_label_to_path:
            self.router_label_to_path[label] = path
            self.router_labels.insert(0, label)
            self.router_combo["values"] = self.router_labels

        self.router_var.set(label)
        self._set_text(self.output_text, f"Selected: {path}\n")

    def choose_save_path(self):
        path = filedialog.asksaveasfilename(
            title="Save tickets to…",
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("All files", "*.*")]
        )
        if path:
            self.save_tickets_var.set(path)

    def run_router(self):
        selected = self.router_var.get().strip()
        router = self.router_label_to_path.get(selected, "")
        router = os.path.abspath(router) if router else router
        if not router or not os.path.isfile(router):
            messagebox.showerror(
                "No router",
                "Router not found. Browse → select .py (e.g., tools/routers/<project>_router.py)"
            )
            return

        request = self._get_text(self.input_text).strip()
        if not request:
            messagebox.showwarning("Empty", "Enter request.")
            return

        # Compress and translate user request
        compressed_request = request
        if self.translate_en_var.get():
            api_key = os.environ.get("GROQ_API_KEY", "").strip()
            if api_key and _contains_korean(request):
                try:
                    system_compress = (
                        "Compress Korean request to concise English. "
                        "Keep technical terms. Use arrows (→) for workflow. "
                        "Output: single compressed sentence."
                    )
                    compressed_request = _groq_chat(
                        [{"role": "system", "content": system_compress},
                         {"role": "user", "content": request}],
                        api_key=api_key,
                        max_tokens=150,
                        temperature=0.1,
                    )
                except Exception:
                    pass  # Use original if translation fails

        cmd = [sys.executable, router]

        # Beginner mode: show copy/paste blocks only
        if self.friendly_var.get():
            cmd.append("--friendly")

        if self.desktop_edit_var.get():
            cmd.append("--desktop-edit")

        if self.force_split_var.get():
            cmd.append("--force-split")

        mt_min = (self.min_tickets_var.get() or "").strip()
        if mt_min and mt_min != "0":
            cmd.extend(["--min-tickets", mt_min])

        cmd.extend(["--economy", self.economy_var.get().strip()])
        cmd.extend(["--phase", self.phase_var.get().strip()])

        if self.opus_only_var.get():
            cmd.append("--opus-only")

        one_task = self.one_task_var.get().strip()
        if one_task:
            cmd.extend(["--one-task", one_task])

        mt = self.max_tickets_var.get().strip()
        if mt and mt != "0":
            cmd.extend(["--max-tickets", mt])

        mg = self.merge_var.get().strip()
        if mg:
            cmd.extend(["--merge", mg])

        save_tickets = self.save_tickets_var.get().strip()
        if save_tickets:
            cmd.extend(["--save-tickets", save_tickets])
        elif self.tickets_md_var.get():
            cmd.append("--tickets-md")

        cmd.append(request)

        self.refresh_preflight()

        # Show compressed/translated request in output
        request_display = f"Request: {compressed_request}\n\n" if compressed_request != request else f"Request: {request}\n\n"

        header = "Running...\n\n" + request_display + " ".join(cmd) + "\n\n"
        if self.friendly_var.get():
            header = (
                "Running...\n\n"
                "[BEGINNER MODE]\n"
                "Copy ``` block only → New Claude session → Run\n"
                "Next ticket → New session\n\n"
                + request_display
                + " ".join(cmd) + "\n\n"
            )
        self._set_text(self.output_text, header)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
        except Exception as e:
            self._set_text(self.output_text, f"❌ Failed: {e}")
            return

        out = (result.stdout or "").strip()
        err = (result.stderr or "").strip()

        combined = out if out else ""
        if err:
            combined += ("\n\n--- STDERR ---\n" + err)

        # Append router result below the header instead of overwriting it
        current = self._get_text(self.output_text)
        final_output = current + (combined or "(no output)")
        if self.translate_en_var.get():
            # Pass 1: free TRANSLATE_MAP replacement (known UI strings)
            final_output = translate_non_code_to_english(final_output)
            # Pass 2: Groq API translation for remaining Korean text
            api_key = os.environ.get("GROQ_API_KEY", "").strip()
            if api_key:
                final_output = translate_output_via_groq(final_output, api_key)
        self._set_text(self.output_text, final_output)

    def copy_request(self):
        text = self._get_text(self.input_text).strip()
        if not text:
            messagebox.showinfo("Copy", "Nothing to copy.")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Copy", "Copied.")

    def copy_claude_block(self):
        """Copy the Claude-ready payload from Output.

        Works with either ``` fenced blocks OR router-specific copy/paste markers.
        """
        text = self._get_text(self.output_text)
        if not text:
            messagebox.showinfo("Copy Block", "No output.")
            return

        desired = (self.one_task_var.get() or "").strip().upper()
        if desired and (len(desired) != 1 or not desired.isalpha()):
            desired = ""

        # If multiple tickets exist and user didn't choose one, ask them.
        ids = detect_ticket_ids(text)
        if not desired and len(ids) > 1:
            pick = simpledialog.askstring(
                "Select Ticket",
                f"Multi-ticket: {', '.join(ids)}\nType letter (e.g., A):",
                initialvalue=ids[0],
                parent=self,
            )
            if pick:
                pick = pick.strip().upper()
                if len(pick) == 1 and pick.isalpha():
                    desired = pick

        block = extract_claude_ready_block_from_output(text, desired)
        if not block:
            messagebox.showinfo(
                "Copy Block",
                "No ``` block found. For multi-ticket: set --one-task to A/B."
            )
            return

        block = block.strip()

        want = desired or "A"

        # If the extracted block contains multiple tickets, slice only the requested one.
        if "Ticket " in block:
            block = slice_single_ticket_from_block(block, want).strip()

        # Fallback 1: if the block is missing the Ticket section entirely, recover the full chunk.
        if "Ticket " not in block:
            recovered = recover_ticket_chunk_from_output(text, want)
            if recovered:
                if not block.endswith("\n"):
                    block += "\n"
                block += "\n" + recovered + "\n"

        # Change log stub removed — CLAUDE.md handles logging rules

        # Always translate Korean → English via Groq before copying
        api_key = os.environ.get("GROQ_API_KEY", "").strip()
        translated = False
        if api_key and _contains_korean(block):
            block = translate_block_to_english(block, api_key)
            translated = not _contains_korean(block)

        block = block.strip()

        self.clipboard_clear()
        self.clipboard_append(block)
        msg = "Block copied (EN)." if translated else "Block copied."
        messagebox.showinfo("Copy Block", msg)

    def copy_output(self):
        text = self._get_text(self.output_text).strip()
        if not text:
            messagebox.showinfo("Copy", "No output.")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Copy", "Copied.")

if __name__ == "__main__":
    app = RouterGUI()
    app.mainloop()
