"""v1 API Blueprint — 1:1 migration from web_server.py endpoints.

All existing endpoints preserved with identical behavior.
No authentication required (backward compatible).
"""

import io
import json
import os
import re
import ssl
import sys
import subprocess
import threading
from contextlib import redirect_stdout
from dataclasses import asdict

from flask import Blueprint, request, jsonify

# Fix SSL certificate verification for Python 3.14+ on macOS
try:
    import certifi
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    import urllib.request
    urllib.request.install_opener(
        urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ssl_ctx)
        )
    )
except ImportError:
    pass

# Ensure project root on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import router_gui helpers — may fail on Vercel (tkinter unavailable)
_HAS_ROUTER_GUI = False
try:
    from router_gui import (
        find_router_candidates,
        git_status_summary,
        detect_ticket_ids,
        extract_claude_ready_block_from_output,
        recover_ticket_chunk_from_output,
        recover_change_log_stub_from_output,
        slice_single_ticket_from_block,
        extract_tickets_from_claude_block,
        rewrite_tickets_to_english_via_groq,
        apply_english_tickets_to_claude_block,
        translate_output_via_groq,
        translate_non_code_to_english,
        _groq_chat,
        _contains_korean,
        IMPL_RULES_SUFFIX,
    )
    _HAS_ROUTER_GUI = True
except (ImportError, ModuleNotFoundError):
    # tkinter not available (e.g. Vercel) — provide fallbacks
    import glob as _glob

    def find_router_candidates():
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        found = _glob.glob(os.path.join(script_dir, "llm_router*.py"))
        return sorted(set(os.path.abspath(f) for f in found if os.path.isfile(f)))

    def git_status_summary(cwd):
        return "unavailable (serverless)"

    def detect_ticket_ids(text):
        return re.findall(r"\bTicket ([A-Z])\b", text)

    def _contains_korean(text):
        return bool(re.search(r"[\uac00-\ud7a3]", text))

    def translate_non_code_to_english(text):
        return text

    def translate_output_via_groq(text, api_key):
        return text

    def _groq_chat(messages, api_key="", **kw):
        return ""

    def extract_claude_ready_block_from_output(text, ticket_id=""):
        return ""

    def recover_ticket_chunk_from_output(text, ticket_id):
        return ""

    def recover_change_log_stub_from_output(text, ticket_id):
        return ""

    def slice_single_ticket_from_block(block, ticket_id):
        return block

    def extract_tickets_from_claude_block(block):
        return {}, ""

    def rewrite_tickets_to_english_via_groq(tickets, original_kr, api_key):
        return tickets

    def apply_english_tickets_to_claude_block(block, en_map):
        return block

    IMPL_RULES_SUFFIX = ""

# Import llm_router for direct function calls (no subprocess needed)
try:
    from llm_router import (
        route_text as _llm_route_text,
        print_friendly as _print_friendly,
        print_human as _print_human,
        filter_one_task as _filter_one_task,
        render_tickets_md as _render_tickets_md,
    )
    _HAS_LLM_ROUTER = True
except ImportError:
    _HAS_LLM_ROUTER = False

from config import (
    IS_VERCEL, BASE_DIR, HISTORY_FILE, PROMPTS_FILE, FEEDBACK_FILE,
    ROUTE_COST_PER_1K, ROUTE_TOKENS_PER_TASK,
    DEFAULT_COST_PER_1K, DEFAULT_TOKENS_PER_TASK,
)

v1_bp = Blueprint("v1", __name__)

_file_lock = threading.Lock()


def _read_json_file(path, default=None):
    if default is None:
        default = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write_json_file(path, data):
    with _file_lock:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def _translate_remaining_korean(text, api_key):
    if not _contains_korean(text):
        return text
    lines = text.splitlines()
    kr_indices = []
    kr_lines = []
    for i, line in enumerate(lines):
        if _contains_korean(line):
            kr_indices.append(i)
            kr_lines.append(line)
    if not kr_lines:
        return text
    numbered = "\n".join(f"[{i}] {line}" for i, line in zip(kr_indices, kr_lines))
    system = (
        "Translate each Korean line to English. "
        "Each line starts with a bracket number like [0], [1], [2]. "
        "Keep that exact bracket number prefix unchanged. "
        "Keep file paths, code, markers, ## headers, and bullet format intact. "
        "Only translate Korean words to English."
    )
    try:
        result = _groq_chat(
            [{"role": "system", "content": system}, {"role": "user", "content": numbered}],
            api_key=api_key, max_tokens=1000, temperature=0.0,
        )
    except Exception:
        return text
    for match in re.finditer(r"\[(\d+)\]\s*(.+)", result):
        idx = int(match.group(1))
        translated = match.group(2).strip()
        if 0 <= idx < len(lines) and translated:
            lines[idx] = translated
    return "\n".join(lines)


# ---------- GET endpoints ----------

@v1_bp.route("/api/routers", methods=["GET"])
def api_routers():
    candidates = find_router_candidates()
    items = []
    for p in candidates:
        items.append({
            "path": p,
            "name": os.path.basename(p),
            "rel": os.path.relpath(p, BASE_DIR),
        })
    return jsonify({"routers": items})


@v1_bp.route("/api/preflight", methods=["GET"])
def api_preflight():
    status = git_status_summary(os.getcwd())
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    return jsonify({"status": status, "groq_key": bool(groq_key)})


@v1_bp.route("/api/history", methods=["GET"])
def api_history_get():
    data = _read_json_file(HISTORY_FILE, [])
    if isinstance(data, list):
        entries = data
    elif isinstance(data, dict):
        entries = data.get("entries", data.get("history", []))
    else:
        entries = []
    return jsonify({"entries": entries})


@v1_bp.route("/api/history", methods=["DELETE"])
def api_history_delete_all():
    _write_json_file(HISTORY_FILE, [])
    return jsonify({"success": True, "deleted": "all"})


@v1_bp.route("/api/history/<int:idx>", methods=["DELETE"])
def api_history_delete_one(idx):
    data = _read_json_file(HISTORY_FILE, [])
    entries = data if isinstance(data, list) else data.get("entries", data.get("history", []))

    if idx < 0 or idx >= len(entries):
        return jsonify({"error": "Index out of range"}), 404

    entries.pop(idx)
    _write_json_file(HISTORY_FILE, entries)
    return jsonify({"success": True, "deleted_index": idx})


@v1_bp.route("/api/cost-stats", methods=["GET"])
def api_cost_stats():
    data = _read_json_file(HISTORY_FILE, [])
    entries = data if isinstance(data, list) else data.get("entries", [])

    total_tokens = 0
    total_cost = 0.0
    route_counts = {"claude": 0, "cheap_llm": 0, "split": 0}

    for entry in entries:
        tasks = entry.get("tasks", [{"route": entry.get("route", "claude")}])
        for t in tasks:
            r = t.get("route", "claude")
            tk = ROUTE_TOKENS_PER_TASK.get(r, DEFAULT_TOKENS_PER_TASK)
            total_tokens += tk
            total_cost += (tk / 1000) * ROUTE_COST_PER_1K.get(r, DEFAULT_COST_PER_1K)
            if r in route_counts:
                route_counts[r] += 1

    return jsonify({
        "total_sessions": len(entries),
        "total_tokens": total_tokens,
        "total_cost": round(total_cost, 4),
        "route_counts": route_counts,
    })


@v1_bp.route("/api/prompts", methods=["GET"])
def api_prompts_get():
    data = _read_json_file(PROMPTS_FILE, {"prompts": []})
    return jsonify(data)


@v1_bp.route("/api/feedback", methods=["GET"])
def api_feedback_get():
    data = _read_json_file(FEEDBACK_FILE, {"feedback": {}})
    return jsonify(data)


# ---------- POST endpoints ----------

@v1_bp.route("/api/route", methods=["POST"])
def api_route():
    body = request.get_json(silent=True) or {}
    request_text = body.get("request", "").strip()

    if not request_text:
        return jsonify({"error": "Empty request", "output": "", "tickets": []}), 400

    # Parse options from request body
    friendly = body.get("friendly", False)
    desktop_edit = body.get("desktop_edit", False)
    force_split = body.get("force_split", False)
    opus_only = body.get("opus_only", False)
    tickets_md = body.get("tickets_md", False)
    economy = (body.get("economy") or "strict").strip().lower()
    if economy not in ("strict", "balanced"):
        economy = "strict"
    phase = (body.get("phase") or "implement").strip().lower()
    if phase not in ("analyze", "implement"):
        phase = "implement"
    one_task = (body.get("one_task") or "").strip()
    merge = (body.get("merge") or "").strip()

    max_tickets_str = (body.get("max_tickets") or "0").strip()
    try:
        max_tickets_n = int(max_tickets_str) if max_tickets_str != "0" else 0
    except (ValueError, TypeError):
        max_tickets_n = 0

    min_tickets_str = (body.get("min_tickets") or "1").strip()
    try:
        min_tickets_n = int(min_tickets_str) if min_tickets_str != "0" else 0
    except (ValueError, TypeError):
        min_tickets_n = 0

    # Direct function call (no subprocess) — works on both local and Vercel
    if _HAS_LLM_ROUTER:
        try:
            router_out = _llm_route_text(
                request_text,
                desktop_edit=desktop_edit,
                economy=economy,
                phase=phase,
                opus_only=opus_only,
                max_tickets=max_tickets_n,
                merge_spec=merge,
                force_split=force_split,
                min_tickets=min_tickets_n,
            )

            if one_task:
                router_out = _filter_one_task(router_out, one_task)

            # Capture printed output
            buf = io.StringIO()
            with redirect_stdout(buf):
                if tickets_md:
                    print(_render_tickets_md(router_out, economy=economy, phase=phase))
                elif friendly:
                    _print_friendly(router_out, desktop_edit=desktop_edit,
                                    economy=economy, phase=phase, opus_only=opus_only)
                else:
                    _print_human(router_out, desktop_edit=desktop_edit,
                                 economy=economy, phase=phase, opus_only=opus_only)

            combined = buf.getvalue().strip()
        except Exception as e:
            return jsonify({"error": str(e), "output": "", "tickets": []})
    else:
        # Fallback: subprocess (local only, not Vercel-compatible)
        router = body.get("router", "").strip()
        candidates = find_router_candidates()
        candidate_paths = [os.path.abspath(c) for c in candidates]
        if not router or os.path.abspath(router) not in candidate_paths:
            return jsonify({"error": "Router not allowed", "output": "", "tickets": []}), 400

        cmd = [sys.executable, router]
        if friendly:
            cmd.append("--friendly")
        if desktop_edit:
            cmd.append("--desktop-edit")
        if force_split:
            cmd.append("--force-split")
        if opus_only:
            cmd.append("--opus-only")
        if tickets_md:
            cmd.append("--tickets-md")
        cmd.extend(["--economy", economy, "--phase", phase])
        if one_task:
            cmd.extend(["--one-task", one_task])
        if max_tickets_n:
            cmd.extend(["--max-tickets", str(max_tickets_n)])
        if min_tickets_n:
            cmd.extend(["--min-tickets", str(min_tickets_n)])
        if merge:
            cmd.extend(["--merge", merge])
        cmd.append(request_text)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd(), timeout=120)
        except subprocess.TimeoutExpired:
            return jsonify({"error": "Router timed out (120s)", "output": "", "tickets": []})
        except Exception as e:
            return jsonify({"error": str(e), "output": "", "tickets": []})

        out = (result.stdout or "").strip()
        err = (result.stderr or "").strip()
        combined = out
        if err:
            combined += "\n\n--- STDERR ---\n" + err

    translate_status = ""
    if body.get("translate_en", False):
        combined = translate_non_code_to_english(combined)
        api_key = os.environ.get("GROQ_API_KEY", "").strip()
        if api_key:
            try:
                combined = translate_output_via_groq(combined, api_key)
                translate_status = "ok"
            except Exception as e:
                translate_status = f"groq_error: {e}"
        else:
            translate_status = "no_api_key"

    tickets = detect_ticket_ids(combined)

    resp = {
        "output": combined,
        "tickets": tickets,
        "error": "",
        "translate_status": translate_status,
    }

    return jsonify(resp)


@v1_bp.route("/api/extract-block", methods=["POST"])
def api_extract_block():
    body = request.get_json(silent=True) or {}

    output = body.get("output", "")
    ticket = (body.get("ticket") or "A").strip().upper()
    translate_groq = body.get("translate_groq", False)
    append_rules = body.get("append_rules", True)

    if not output:
        return jsonify({"block": "", "success": False})

    block = extract_claude_ready_block_from_output(output, ticket)
    if not block:
        return jsonify({"block": "", "success": False})

    block = block.strip()

    if "Ticket " in block:
        block = slice_single_ticket_from_block(block, ticket).strip()

    if "Ticket " not in block:
        recovered = recover_ticket_chunk_from_output(output, ticket)
        if recovered:
            block = block.rstrip() + "\n\n" + recovered + "\n"

    if translate_groq:
        api_key = os.environ.get("GROQ_API_KEY", "").strip()
        if api_key:
            if "Ticket " in block:
                try:
                    tickets_map, original_kr = extract_tickets_from_claude_block(block)
                    if tickets_map:
                        en_map = rewrite_tickets_to_english_via_groq(tickets_map, original_kr, api_key)
                        en_map.pop("__KR__", None)
                        block = apply_english_tickets_to_claude_block(block, en_map)
                except Exception:
                    pass

            if _contains_korean(block):
                try:
                    block = translate_non_code_to_english(block)
                    block = _translate_remaining_korean(block, api_key)
                except Exception:
                    pass

    if append_rules:
        block = block.rstrip() + "\n" + IMPL_RULES_SUFFIX

    return jsonify({"block": block, "success": True})


@v1_bp.route("/api/prompts", methods=["POST"])
def api_prompts_save():
    body = request.get_json(silent=True) or {}
    prompts = body.get("prompts", [])
    _write_json_file(PROMPTS_FILE, {"prompts": prompts})
    return jsonify({"success": True, "count": len(prompts)})


@v1_bp.route("/api/feedback", methods=["POST"])
def api_feedback_save():
    body = request.get_json(silent=True) or {}
    feedback = body.get("feedback", {})
    _write_json_file(FEEDBACK_FILE, {"feedback": feedback})
    return jsonify({"success": True, "count": len(feedback)})
