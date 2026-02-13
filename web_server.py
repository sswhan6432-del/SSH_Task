#!/usr/bin/env python3
"""Local-only web server for LLM Router GUI.

stdlib-only: uses http.server, no Flask/FastAPI.
Serves static files from website/ and exposes REST API endpoints.

Usage:
    python3 web_server.py [--port 8080]
"""

import json
import os
import ssl
import sys
import subprocess
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
DEFAULT_PORT = 8080


class ReusableHTTPServer(HTTPServer):
    """HTTPServer with SO_REUSEADDR enabled to allow immediate port reuse."""

    allow_reuse_address = True

    def server_bind(self):
        """Override server_bind to enable socket reuse before binding."""
        import socket
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        super().server_bind()


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

        self._json_response({
            "output": combined,
            "tickets": tickets,
            "error": "",
            "translate_status": translate_status,
        })

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


def main():
    port = DEFAULT_PORT
    if "--port" in sys.argv:
        idx = sys.argv.index("--port")
        if idx + 1 < len(sys.argv):
            port = int(sys.argv[idx + 1])

    server = ReusableHTTPServer(("127.0.0.1", port), RouterHandler)
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
