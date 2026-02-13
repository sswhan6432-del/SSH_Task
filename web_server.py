#!/usr/bin/env python3
"""Local-only web server for LLM Router GUI.

stdlib-only: uses http.server, no Flask/FastAPI.
Serves static files from website/ and exposes REST API endpoints.

Usage:
    python3 web_server.py [--port 8080]
"""

import json
import os
import re
import ssl
import sys
import subprocess
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

# Fix SSL certificate verification for Python 3.14+ on macOS
# Uses certifi CA bundle if available, otherwise falls back to default
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

# Import helpers from router_gui (module-level functions, no GUI instantiation)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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


def _translate_remaining_korean(text: str, api_key: str) -> str:
    """Translate any remaining Korean in specific lines while preserving structure.

    Rather than sending the whole block (which Groq may restructure),
    this identifies individual Korean lines and translates them in batch.
    """
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
            api_key=api_key,
            max_tokens=1000,
            temperature=0.0,
        )
    except Exception:
        return text

    # Parse translated lines
    import re
    for match in re.finditer(r"\[(\d+)\]\s*(.+)", result):
        idx = int(match.group(1))
        translated = match.group(2).strip()
        if 0 <= idx < len(lines) and translated:
            lines[idx] = translated

    return "\n".join(lines)

WEBSITE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "website")
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(DATA_DIR, "task_history.json")
PROMPTS_FILE = os.path.join(DATA_DIR, "prompts.json")
FEEDBACK_FILE = os.path.join(DATA_DIR, "feedback.json")
DEFAULT_PORT = 8080

# Thread-safe lock for file writes
_file_lock = threading.Lock()


def _read_json_file(path, default=None):
    """Read a JSON file safely, return default on failure."""
    if default is None:
        default = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write_json_file(path, data):
    """Write JSON file safely with lock."""
    with _file_lock:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


class ThreadedHTTPServer(HTTPServer):
    """HTTPServer with threading + SO_REUSEADDR for concurrent requests."""

    allow_reuse_address = True

    def server_bind(self):
        """Override server_bind to enable socket reuse before binding."""
        import socket
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        super().server_bind()

    def process_request(self, request, client_address):
        """Handle each request in a new thread for non-blocking I/O."""
        t = threading.Thread(target=self._handle_request_thread,
                             args=(request, client_address))
        t.daemon = True
        t.start()

    def _handle_request_thread(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)


class RouterHandler(SimpleHTTPRequestHandler):
    """HTTP handler: static files from website/ + JSON API."""

    allow_reuse_address = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEBSITE_DIR, **kwargs)

    # ---------- routing ----------

    def end_headers(self):
        """Disable browser caching for all responses."""
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/api/routers":
            return self._api_routers()
        if path == "/api/preflight":
            return self._api_preflight()
        if path == "/api/history":
            return self._api_history_get()
        if path == "/api/prompts":
            return self._api_prompts_get()
        if path == "/api/feedback":
            return self._api_feedback_get()
        if path == "/api/cost-stats":
            return self._api_cost_stats()

        # Default file: router.html
        if path == "/":
            self.path = "/router.html"

        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/api/route":
            return self._api_route()
        if path == "/api/extract-block":
            return self._api_extract_block()
        if path == "/api/prompts":
            return self._api_prompts_save()
        if path == "/api/feedback":
            return self._api_feedback_save()

        self._json_response({"error": "Not found"}, 404)

    # ---------- helpers ----------

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw)

    def _json_response(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # Suppress default access logs
    def log_message(self, fmt, *args):
        try:
            if args and "/api/" in str(args[0]):
                super().log_message(fmt, *args)
        except (TypeError, AttributeError):
            pass  # Suppress logs on error

    # ---------- API endpoints ----------

    def _api_routers(self):
        candidates = find_router_candidates()
        items = []
        base_dir = os.path.dirname(os.path.abspath(__file__))
        for p in candidates:
            items.append({
                "path": p,
                "name": os.path.basename(p),
                "rel": os.path.relpath(p, base_dir),
            })
        self._json_response({"routers": items})

    def _api_preflight(self):
        status = git_status_summary(os.getcwd())
        groq_key = os.environ.get("GROQ_API_KEY", "").strip()
        self._json_response({
            "status": status,
            "groq_key": bool(groq_key),
        })

    def _api_route(self):
        try:
            body = self._read_json_body()
        except Exception as e:
            return self._json_response({"error": f"Bad JSON: {e}"}, 400)

        router = body.get("router", "").strip()
        request_text = body.get("request", "").strip()

        if not router or not os.path.isfile(router):
            return self._json_response({"error": "Router file not found", "output": "", "tickets": []}, 400)
        if not request_text:
            return self._json_response({"error": "Empty request", "output": "", "tickets": []}, 400)

        # Build command
        cmd = [sys.executable, router]

        if body.get("friendly", False):
            cmd.append("--friendly")
        if body.get("desktop_edit", False):
            cmd.append("--desktop-edit")
        if body.get("force_split", False):
            cmd.append("--force-split")
        if body.get("opus_only", False):
            cmd.append("--opus-only")

        tickets_md = body.get("tickets_md", False)
        save_tickets = (body.get("save_tickets") or "").strip()
        if save_tickets:
            cmd.extend(["--save-tickets", save_tickets])
        elif tickets_md:
            cmd.append("--tickets-md")

        economy = (body.get("economy") or "strict").strip()
        cmd.extend(["--economy", economy])

        phase = (body.get("phase") or "implement").strip()
        cmd.extend(["--phase", phase])

        one_task = (body.get("one_task") or "").strip()
        if one_task:
            cmd.extend(["--one-task", one_task])

        max_tickets = (body.get("max_tickets") or "0").strip()
        if max_tickets and max_tickets != "0":
            cmd.extend(["--max-tickets", max_tickets])

        min_tickets = (body.get("min_tickets") or "1").strip()
        if min_tickets and min_tickets != "0":
            cmd.extend(["--min-tickets", min_tickets])

        merge = (body.get("merge") or "").strip()
        if merge:
            cmd.extend(["--merge", merge])

        # v5.0 NLP/ML flags
        if body.get("v5_enabled", False):
            cmd.append("--v5")
            if body.get("compress", True):
                cmd.append("--compress")
            cl = str(body.get("compression_level", 2)).strip()
            if cl in ("1", "2", "3"):
                cmd.extend(["--compression-level", cl])
            if body.get("show_stats", False):
                cmd.append("--show-stats")

        cmd.append(request_text)

        # Execute
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd(), timeout=120)
        except subprocess.TimeoutExpired:
            return self._json_response({"error": "Router timed out (120s)", "output": "", "tickets": []})
        except Exception as e:
            return self._json_response({"error": str(e), "output": "", "tickets": []})

        out = (result.stdout or "").strip()
        err = (result.stderr or "").strip()
        combined = out
        if err:
            combined += "\n\n--- STDERR ---\n" + err

        # Optional: translate output to English
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
                    print(f"[WARN] Groq translation failed: {e}", file=sys.stderr)
            else:
                translate_status = "no_api_key"
                print("[WARN] GROQ_API_KEY not set — skipping Groq translation", file=sys.stderr)

        # Detect tickets
        tickets = detect_ticket_ids(combined)

        # Build response
        resp = {
            "output": combined,
            "tickets": tickets,
            "error": "",
            "translate_status": translate_status,
        }

        # Add v5.0 stats if v5 was enabled
        if body.get("v5_enabled", False):
            resp["v5_stats"] = {
                "enabled": True,
                "compress": body.get("compress", True),
                "compression_level": int(body.get("compression_level", 2)),
            }

        self._json_response(resp)

    def _api_extract_block(self):
        try:
            body = self._read_json_body()
        except Exception as e:
            return self._json_response({"error": f"Bad JSON: {e}", "block": "", "success": False}, 400)

        output = body.get("output", "")
        ticket = (body.get("ticket") or "A").strip().upper()
        translate_groq = body.get("translate_groq", False)
        append_rules = body.get("append_rules", True)

        if not output:
            return self._json_response({"block": "", "success": False})

        # Extract block
        block = extract_claude_ready_block_from_output(output, ticket)
        if not block:
            return self._json_response({"block": "", "success": False})

        block = block.strip()

        # Slice single ticket if multiple present
        if "Ticket " in block:
            block = slice_single_ticket_from_block(block, ticket).strip()

        # Fallback recovery
        if "Ticket " not in block:
            recovered = recover_ticket_chunk_from_output(output, ticket)
            if recovered:
                block = block.rstrip() + "\n\n" + recovered + "\n"

        # Change log stub removed — CLAUDE.md already defines logging rules

        # Optional Groq translation
        if translate_groq:
            api_key = os.environ.get("GROQ_API_KEY", "").strip()
            if api_key:
                # Pass 1: Translate ticket bodies
                if "Ticket " in block:
                    try:
                        tickets_map, original_kr = extract_tickets_from_claude_block(block)
                        if tickets_map:
                            en_map = rewrite_tickets_to_english_via_groq(tickets_map, original_kr, api_key)
                            en_map.pop("__KR__", None)  # Web UI: omit Korean original line
                            block = apply_english_tickets_to_claude_block(block, en_map)
                    except Exception as e:
                        print(f"[WARN] Groq ticket translation failed: {e}", file=sys.stderr)

                # Pass 2: Translate any remaining Korean (Change log stub, etc.)
                if _contains_korean(block):
                    try:
                        block = translate_non_code_to_english(block)
                        block = _translate_remaining_korean(block, api_key)
                    except Exception as e:
                        print(f"[WARN] Groq final translation pass failed: {e}", file=sys.stderr)

        # Append implementation rules
        if append_rules:
            block = block.rstrip() + "\n" + IMPL_RULES_SUFFIX

        self._json_response({"block": block, "success": True})

    # ---------- History API ----------

    def _api_history_get(self):
        data = _read_json_file(HISTORY_FILE, [])
        # task_history.json can be a list or dict with "entries" key
        if isinstance(data, list):
            entries = data
        elif isinstance(data, dict):
            entries = data.get("entries", data.get("history", []))
        else:
            entries = []
        self._json_response({"entries": entries})

    # ---------- Cost Stats API ----------

    def _api_cost_stats(self):
        data = _read_json_file(HISTORY_FILE, [])
        entries = data if isinstance(data, list) else data.get("entries", [])

        cost_per_1k = {"claude": 0.015, "cheap_llm": 0.0005, "split": 0.008}
        tokens_per_task = {"claude": 2000, "cheap_llm": 500, "split": 1200}

        total_tokens = 0
        total_cost = 0.0
        route_counts = {"claude": 0, "cheap_llm": 0, "split": 0}

        for entry in entries:
            tasks = entry.get("tasks", [{"route": entry.get("route", "claude")}])
            for t in tasks:
                r = t.get("route", "claude")
                tk = tokens_per_task.get(r, 1000)
                total_tokens += tk
                total_cost += (tk / 1000) * cost_per_1k.get(r, 0.01)
                if r in route_counts:
                    route_counts[r] += 1

        self._json_response({
            "total_sessions": len(entries),
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 4),
            "route_counts": route_counts,
        })

    # ---------- Prompts API ----------

    def _api_prompts_get(self):
        data = _read_json_file(PROMPTS_FILE, {"prompts": []})
        self._json_response(data)

    def _api_prompts_save(self):
        try:
            body = self._read_json_body()
        except Exception as e:
            return self._json_response({"error": f"Bad JSON: {e}"}, 400)

        prompts = body.get("prompts", [])
        _write_json_file(PROMPTS_FILE, {"prompts": prompts})
        self._json_response({"success": True, "count": len(prompts)})

    # ---------- Feedback API ----------

    def _api_feedback_get(self):
        data = _read_json_file(FEEDBACK_FILE, {"feedback": {}})
        self._json_response(data)

    def _api_feedback_save(self):
        try:
            body = self._read_json_body()
        except Exception as e:
            return self._json_response({"error": f"Bad JSON: {e}"}, 400)

        feedback = body.get("feedback", {})
        _write_json_file(FEEDBACK_FILE, {"feedback": feedback})
        self._json_response({"success": True, "count": len(feedback)})


def main():
    port = DEFAULT_PORT
    if "--port" in sys.argv:
        idx = sys.argv.index("--port")
        if idx + 1 < len(sys.argv):
            port = int(sys.argv[idx + 1])

    server = ThreadedHTTPServer(("127.0.0.1", port), RouterHandler)
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    print(f"Router Web UI running at http://localhost:{port}")
    print(f"Serving files from {WEBSITE_DIR}")
    print(f"GROQ_API_KEY: {'set (' + groq_key[:4] + '...)' if groq_key else 'NOT SET — translation disabled'}")
    print("Press Ctrl+C to stop.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
