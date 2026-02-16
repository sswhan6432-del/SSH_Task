#!/usr/bin/env python3
"""Local-only web server for LLM Router GUI.

stdlib-only: uses http.server, no Flask/FastAPI.
Serves static files from website/ and exposes REST API endpoints.

Usage:
    python3 web_server.py [--port 8080]
"""

import hashlib
import json
import os
import re
import secrets
import ssl
import sys
import subprocess
import threading
import time
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


# ---------- Auth helpers ----------

AUTH_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
USERS_FILE = os.path.join(AUTH_DATA_DIR, "users.json")
SESSIONS_FILE = os.path.join(AUTH_DATA_DIR, "sessions.json")
SESSION_MAX_AGE = 30 * 24 * 3600  # 30 days in seconds
_sessions = {}  # { token: { user_id, name, email, created_at } }
_sessions_lock = threading.Lock()
_users_lock = threading.Lock()


def _load_users():
    os.makedirs(AUTH_DATA_DIR, exist_ok=True)
    if not os.path.isfile(USERS_FILE):
        return {"users": []}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_users(data):
    os.makedirs(AUTH_DATA_DIR, exist_ok=True)
    tmp = USERS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, USERS_FILE)


def _load_sessions():
    """Load persisted sessions from disk into memory."""
    global _sessions
    os.makedirs(AUTH_DATA_DIR, exist_ok=True)
    if not os.path.isfile(SESSIONS_FILE):
        return
    try:
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        now = time.time()
        with _sessions_lock:
            for token, info in data.items():
                if now - info.get("created_at", 0) < SESSION_MAX_AGE:
                    _sessions[token] = info
    except (json.JSONDecodeError, OSError):
        pass


def _persist_sessions():
    """Save current sessions to disk."""
    os.makedirs(AUTH_DATA_DIR, exist_ok=True)
    with _sessions_lock:
        data = dict(_sessions)
    tmp = SESSIONS_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, SESSIONS_FILE)
    except OSError:
        pass


def _hash_password(password, salt):
    """Hash password with PBKDF2-HMAC-SHA256 (600K iterations)."""
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations=600_000
    ).hex()


def _hash_password_legacy(password, salt):
    """Legacy SHA256 hash — used only for migration verification."""
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def _verify_and_migrate(user, password, users_data):
    """Verify password against current or legacy hash; auto-migrate if legacy.

    Returns True if password matches (and migrates hash if needed).
    """
    salt = user["salt"]
    stored_hash = user["password_hash"]

    # Try current PBKDF2 hash first
    if _hash_password(password, salt) == stored_hash:
        return True

    # Try legacy SHA256 hash
    if _hash_password_legacy(password, salt) == stored_hash:
        # Migrate to PBKDF2
        user["password_hash"] = _hash_password(password, salt)
        user["hash_scheme"] = "pbkdf2"
        _save_users(users_data)
        return True

    return False


def _create_session(user):
    token = secrets.token_hex(32)
    with _sessions_lock:
        _sessions[token] = {
            "user_id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "created_at": time.time(),
        }
    _persist_sessions()
    return token


def _validate_session(token):
    with _sessions_lock:
        info = _sessions.get(token)
    if not info:
        return None
    if time.time() - info.get("created_at", 0) >= SESSION_MAX_AGE:
        _remove_session(token)
        return None
    return info


def _remove_session(token):
    with _sessions_lock:
        _sessions.pop(token, None)
    _persist_sessions()


# Load persisted sessions on startup
_load_sessions()


class RouterHandler(SimpleHTTPRequestHandler):
    """HTTP handler: static files from website/ + JSON API."""

    allow_reuse_address = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEBSITE_DIR, **kwargs)

    # ---------- routing ----------

    def end_headers(self):
        """Set caching headers: no-cache for API, allow cache for static files."""
        path = urlparse(self.path).path
        if path.startswith("/api/"):
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        self.send_header("X-Content-Type-Options", "nosniff")
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
        if path == "/api/auth/me":
            return self._api_auth_me()
        if path == "/api/v2/analytics":
            return self._api_v2_analytics()
        if path == "/api/v2/budget":
            return self._api_v2_budget()
        if path == "/api/v2/stream":
            return self._api_v2_stream()

        # Default file: router.html
        if path == "/":
            self.path = "/router.html"

        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/api/route":
            return self._api_route()
        if path == "/api/blueprint":
            return self._api_blueprint()
        if path == "/api/extract-block":
            return self._api_extract_block()
        if path == "/api/prompts":
            return self._api_prompts_save()
        if path == "/api/feedback":
            return self._api_feedback_save()
        if path == "/api/auth/signup":
            return self._api_auth_signup()
        if path == "/api/auth/login":
            return self._api_auth_login()
        if path == "/api/auth/logout":
            return self._api_auth_logout()

        self._json_response({"error": "Not found"}, 404)

    def do_DELETE(self):
        path = urlparse(self.path).path

        if path == "/api/history":
            return self._api_history_delete_all()
        if path.startswith("/api/history/"):
            return self._api_history_delete_one(path)

        self._json_response({"error": "Not found"}, 404)

    # ---------- helpers ----------

    def _read_json_body(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
        except (ValueError, TypeError):
            return {}
        if length > 5 * 1024 * 1024:  # 5 MB limit
            return {}
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

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

    # ---------- Auth API ----------

    def _get_bearer_token(self):
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:].strip()
        return None

    def _api_auth_signup(self):
        try:
            body = self._read_json_body()
        except Exception as e:
            return self._json_response({"error": f"Bad JSON: {e}"}, 400)

        name = (body.get("name") or "").strip()
        email = (body.get("email") or "").strip().lower()
        password = body.get("password") or ""

        if not name or not email or not password:
            return self._json_response({"error": "Name, email and password required"}, 400)
        if len(password) < 6:
            return self._json_response({"error": "Password must be at least 6 characters"}, 400)
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            return self._json_response({"error": "Invalid email format"}, 400)

        with _users_lock:
            data = _load_users()
            if any(u["email"] == email for u in data["users"]):
                return self._json_response({"error": "Email already registered"}, 409)

            salt = secrets.token_hex(8)
            user = {
                "id": "u_" + secrets.token_hex(6),
                "name": name,
                "email": email,
                "password_hash": _hash_password(password, salt),
                "salt": salt,
                "hash_scheme": "pbkdf2",
                "created_at": time.time(),
            }
            data["users"].append(user)
            _save_users(data)

        token = _create_session(user)
        self._json_response({
            "ok": True,
            "token": token,
            "user": {"name": user["name"], "email": user["email"]},
        })

    def _api_auth_login(self):
        try:
            body = self._read_json_body()
        except Exception as e:
            return self._json_response({"error": f"Bad JSON: {e}"}, 400)

        email = (body.get("email") or "").strip().lower()
        password = body.get("password") or ""

        if not email or not password:
            return self._json_response({"error": "Email and password required"}, 400)

        with _users_lock:
            data = _load_users()
            user = next((u for u in data["users"] if u["email"] == email), None)

            if not user or not _verify_and_migrate(user, password, data):
                return self._json_response({"error": "Invalid email or password"}, 401)

        token = _create_session(user)
        self._json_response({
            "ok": True,
            "token": token,
            "user": {"name": user["name"], "email": user["email"]},
        })

    def _api_auth_me(self):
        token = self._get_bearer_token()
        if not token:
            return self._json_response({"error": "Not authenticated"}, 401)

        session = _validate_session(token)
        if not session:
            return self._json_response({"error": "Not authenticated"}, 401)

        self._json_response({
            "ok": True,
            "user": {"name": session["name"], "email": session["email"]},
        })

    def _api_auth_logout(self):
        token = self._get_bearer_token()
        if token:
            _remove_session(token)
        self._json_response({"ok": True})

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

        # Whitelist validation: router must be in known candidates
        candidates = find_router_candidates()
        candidate_paths = [os.path.abspath(c) for c in candidates]
        if not router or os.path.abspath(router) not in candidate_paths:
            return self._json_response({"error": "Router not allowed", "output": "", "tickets": []}, 400)
        if not request_text:
            return self._json_response({"error": "Empty request", "output": "", "tickets": []}, 400)

        # Build command
        # When v5 is enabled, force llm_router_v5.py which properly strips v5 flags
        # before falling back to v4. Using the user-selected v4 router directly with
        # v5 flags causes the v4 router to treat flag names as request text.
        v5_enabled = body.get("v5_enabled", False)
        if v5_enabled:
            v5_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "llm_router_v5.py")
            if os.path.isfile(v5_script):
                router = v5_script
            else:
                v5_enabled = False  # v5 script not found, disable v5

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

        # v5.0 NLP/ML flags (only added when router is llm_router_v5.py)
        if v5_enabled:
            cmd.append("--v5")
            if body.get("compress", True):
                cmd.append("--compress")
            cl = str(body.get("compression_level", 2)).strip()
            if cl in ("1", "2", "3"):
                cmd.extend(["--compression-level", cl])
            if body.get("intent_detect", True):
                cmd.append("--intent-detect")
            if body.get("smart_priority", True):
                cmd.append("--smart-priority")
            if body.get("show_stats", False):
                cmd.append("--show-stats")

        cmd.append(request_text)

        # Execute
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd(), timeout=120)
        except subprocess.TimeoutExpired:
            return self._json_response({"error": "Router timed out (120s)", "output": "", "tickets": []})
        except Exception as e:
            print(f"[ERROR] Router execution failed: {e}", file=sys.stderr)
            return self._json_response({"error": "Router execution failed", "output": "", "tickets": []})

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
            # Parse v5 output for stats (if available in output)
            # Try to extract stats from router output if available
            token_reduction_rate = 0.0
            original_tokens = 0
            compressed_tokens = 0
            processing_time_ms = 0.0
            intent_accuracy = 0.0
            priority_confidence = 0.0

            # Try to parse stats from output if in JSON format
            try:
                if combined.strip().startswith('{'):
                    data = json.loads(combined)
                    token_reduction_rate = data.get("token_reduction_rate", 0.0)
                    processing_time_ms = data.get("total_processing_time_ms", 0.0)

                    # Extract from tasks if available
                    tasks = data.get("tasks", [])
                    if tasks:
                        total_orig = sum(t.get("compression_result", {}).get("original_tokens", 0) for t in tasks)
                        total_comp = sum(t.get("compression_result", {}).get("compressed_tokens", 0) for t in tasks)
                        original_tokens = total_orig
                        compressed_tokens = total_comp

                        # Calculate average confidence
                        intent_scores = [t.get("intent_analysis", {}).get("confidence", 0) for t in tasks if t.get("intent_analysis")]
                        if intent_scores:
                            intent_accuracy = sum(intent_scores) / len(intent_scores)

                        priority_scores = [t.get("priority_score", {}).get("ml_confidence", 0) for t in tasks if t.get("priority_score")]
                        if priority_scores:
                            priority_confidence = sum(priority_scores) / len(priority_scores)
            except (json.JSONDecodeError, KeyError):
                pass  # Stats not available in output

            resp["v5_stats"] = {
                "enabled": True,
                "compress": body.get("compress", True),
                "compression_level": int(body.get("compression_level", 2)),
                "intent_detect": body.get("intent_detect", True),
                "smart_priority": body.get("smart_priority", True),
                "token_reduction_rate": token_reduction_rate,
                "original_tokens": original_tokens,
                "compressed_tokens": compressed_tokens,
                "processing_time_ms": processing_time_ms,
                "intent_accuracy": intent_accuracy,
                "priority_confidence": priority_confidence,
            }

        self._json_response(resp)

    def _api_blueprint(self):
        """Generate AI-powered project blueprint using Groq API."""
        try:
            body = self._read_json_body()
        except Exception as e:
            return self._json_response({"error": f"Bad JSON: {e}"}, 400)

        idea = body.get("idea", "").strip()
        if not idea:
            return self._json_response({"error": "No idea provided"}, 400)

        api_key = os.environ.get("GROQ_API_KEY", "").strip()
        if not api_key:
            return self._json_response({"error": "GROQ_API_KEY not set"}, 500)

        system_prompt = """You are a senior software architect. The user gives you a short project idea. You must generate a detailed implementation blueprint with exactly 10 phases.

OUTPUT FORMAT (strict JSON array):
[
  {
    "letter": "A",
    "title": "Phase title (5-8 words)",
    "summary": "One-line description of this phase",
    "description": "A short English one-line summary describing what this phase does (e.g. 'Set up project structure and choose the tech stack')",
    "prompt": "A detailed, Claude-ready prompt (200-400 words) that someone can copy and paste into Claude AI to get working code for this phase. Include specific technologies, file names, data structures, API endpoints, and implementation details. Be extremely specific to the project idea."
  },
  ...
]

The 10 phases MUST be:
A: Project Overview & Tech Stack Selection
B: Database Schema & Data Model Design
C: Authentication & User Management
D: Core Feature #1 (the primary unique feature of this project)
E: Core Feature #2 (secondary key feature)
F: UI/UX Pages & Component Design
G: REST API Endpoints & Backend Logic
H: Search, Filter & Data Display
I: Admin Dashboard & Analytics
J: Testing, Security, SEO & Deployment

CRITICAL LANGUAGE RULE:
ALL fields ("letter", "title", "summary", "description", "prompt") MUST be written ONLY in English.
Even if the user input is in Korean, Chinese, Japanese, or any non-English language, you MUST write every single field in English.
NEVER output Korean, Japanese, Chinese, or any non-English characters in any field. This is a hard requirement.

RULES:
- Each prompt must be SPECIFIC to the project idea, not generic
- Include actual table names, field names, component names relevant to the project
- Mention specific tech recommendations (e.g., "Use Next.js with Tailwind CSS because...")
- The prompt should be self-contained - Claude should be able to implement it without additional context
- If the input is in Korean, include the Korean project name in the prompts for context but write the rest in English
- Return ONLY the JSON array, no other text"""

        user_msg = f"Project idea: {idea}"

        try:
            result = _groq_chat(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                api_key=api_key,
                max_tokens=4000,
                temperature=0.7,
            )

            # Parse JSON from response
            # Handle potential markdown code blocks
            cleaned = result.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                cleaned = re.sub(r"\s*```$", "", cleaned)

            tickets = json.loads(cleaned)

            # Validate structure
            if not isinstance(tickets, list) or len(tickets) == 0:
                raise ValueError("Invalid blueprint format")

            # Ensure all tickets have required fields
            letters = "ABCDEFGHIJ"
            for i, t in enumerate(tickets):
                if "letter" not in t:
                    t["letter"] = letters[i] if i < len(letters) else str(i + 1)
                if "title" not in t:
                    t["title"] = f"Phase {t['letter']}"
                if "prompt" not in t:
                    t["prompt"] = t.get("summary", "")
                if "summary" not in t:
                    t["summary"] = t["title"]
                # Map "description" field to "summary_ko" for frontend
                if "description" in t:
                    t["summary_ko"] = t["description"]
                elif "summary_ko" not in t:
                    t["summary_ko"] = t["summary"]

            self._json_response({"tickets": tickets, "error": ""})

        except json.JSONDecodeError as e:
            # Fallback: return the raw text as a single ticket
            self._json_response({
                "error": f"Failed to parse AI response: {e}",
                "raw": result if 'result' in dir() else "",
            }, 500)
        except Exception as e:
            self._json_response({"error": f"Groq API error: {e}"}, 500)

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

    def _api_history_delete_all(self):
        _write_json_file(HISTORY_FILE, [])
        self._json_response({"success": True, "deleted": "all"})

    def _api_history_delete_one(self, path):
        # path = /api/history/<index>
        try:
            idx = int(path.split("/")[-1])
        except (ValueError, IndexError):
            self._json_response({"error": "Invalid index"}, 400)
            return

        data = _read_json_file(HISTORY_FILE, [])
        entries = data if isinstance(data, list) else data.get("entries", data.get("history", []))

        if idx < 0 or idx >= len(entries):
            self._json_response({"error": "Index out of range"}, 404)
            return

        removed = entries.pop(idx)
        _write_json_file(HISTORY_FILE, entries)
        self._json_response({"success": True, "deleted_index": idx})

    # ---------- Cost Stats API ----------

    # ---------- V2 Analytics (Claude Code integration) ----------

    def _api_v2_analytics(self):
        """Return analytics from Claude Code stats-cache.json + session-meta."""
        from urllib.parse import parse_qs
        query = parse_qs(urlparse(self.path).query)
        period = (query.get("period") or ["24h"])[0]

        stats_path = os.path.expanduser("~/.claude/stats-cache.json")
        meta_dir = os.path.expanduser("~/.claude/usage-data/session-meta/")

        # Load stats cache
        stats = {}
        try:
            with open(stats_path, "r", encoding="utf-8") as f:
                stats = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        # --- Burn rate from daily activity ---
        daily = stats.get("dailyActivity", [])
        daily_tokens = stats.get("dailyModelTokens", [])
        model_usage = stats.get("modelUsage", {})

        # Period filter
        import datetime
        now = datetime.datetime.now()
        period_map = {"1h": 0.042, "24h": 1, "7d": 7, "30d": 30}
        days_back = period_map.get(period, 1)

        cutoff = (now - datetime.timedelta(days=days_back)).strftime("%Y-%m-%d")

        filtered_daily = [d for d in daily if d.get("date", "") >= cutoff]
        filtered_tokens = [d for d in daily_tokens if d.get("date", "") >= cutoff]

        total_messages = sum(d.get("messageCount", 0) for d in filtered_daily)
        total_sessions = sum(d.get("sessionCount", 0) for d in filtered_daily)
        total_tool_calls = sum(d.get("toolCallCount", 0) for d in filtered_daily)

        # Token totals from filtered daily model tokens
        total_tokens = 0
        model_dist = {}
        for d in filtered_tokens:
            for model, toks in d.get("tokensByModel", {}).items():
                total_tokens += toks
                short = model.split("-")[1] if "-" in model else model  # e.g. "opus", "sonnet", "haiku"
                model_dist[short] = model_dist.get(short, 0) + toks

        # Cost estimation (per 1K output tokens)
        cost_rates = {
            "opus": 0.075, "sonnet": 0.015, "haiku": 0.005,
        }
        total_cost = 0.0
        for model, toks in model_dist.items():
            rate = cost_rates.get(model, 0.015)
            total_cost += (toks / 1000) * rate

        # Daily token rate
        num_days = max(1, len(filtered_daily))
        daily_token_rate = total_tokens / num_days
        monthly_projection = daily_token_rate * 30
        monthly_cost_projection = (total_cost / num_days) * 30

        # --- Heatmap + fallback tokens from session-meta ---
        heatmap = [[0] * 24 for _ in range(7)]
        meta_sessions = 0
        meta_tokens = 0
        try:
            for fname in os.listdir(meta_dir):
                if not fname.endswith(".json"):
                    continue
                fpath = os.path.join(meta_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        sess = json.load(f)
                    st = sess.get("start_time", "")
                    if not st:
                        continue
                    dt = datetime.datetime.fromisoformat(st.replace("Z", "+00:00"))
                    local_dt = dt.astimezone()
                    if local_dt.strftime("%Y-%m-%d") < cutoff:
                        continue
                    dow = local_dt.weekday()  # 0=Mon
                    hour = local_dt.hour
                    msg_count = sess.get("user_message_count", 0) + sess.get("assistant_message_count", 0)
                    heatmap[dow][hour] += max(1, msg_count)
                    meta_sessions += 1
                    meta_tokens += sess.get("input_tokens", 0) + sess.get("output_tokens", 0)
                except (json.JSONDecodeError, ValueError, KeyError):
                    continue
        except FileNotFoundError:
            pass

        # Fallback: if stats-cache had no data for this period, use session-meta tokens
        if total_tokens == 0 and meta_tokens > 0:
            total_tokens = meta_tokens
            total_cost = (meta_tokens / 1000) * 0.015  # estimate with sonnet rate
            model_dist = {"mixed": meta_tokens}
            total_sessions = meta_sessions
            num_days = max(1, days_back) if days_back >= 1 else 1
            daily_token_rate = total_tokens / num_days
            monthly_projection = daily_token_rate * 30
            monthly_cost_projection = (total_cost / num_days) * 30

        # --- Latency from session-meta (estimate from duration/messages) ---
        latencies = []
        try:
            for fname in os.listdir(meta_dir):
                if not fname.endswith(".json"):
                    continue
                fpath = os.path.join(meta_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        sess = json.load(f)
                    st = sess.get("start_time", "")
                    if st and st[:10] >= cutoff:
                        dur = sess.get("duration_minutes", 0)
                        msgs = sess.get("assistant_message_count", 1) or 1
                        avg_ms = int((dur * 60 * 1000) / msgs) if dur > 0 else 0
                        if avg_ms > 0:
                            latencies.append(avg_ms)
                except (json.JSONDecodeError, ValueError, KeyError):
                    continue
        except FileNotFoundError:
            pass

        latencies.sort()
        p50 = latencies[len(latencies) // 2] if latencies else 0
        p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0
        p99 = latencies[int(len(latencies) * 0.99)] if latencies else 0

        # --- Cost trends ---
        cost_trends = []
        for d in filtered_tokens:
            day_cost = 0.0
            for model, toks in d.get("tokensByModel", {}).items():
                short = model.split("-")[1] if "-" in model else model
                rate = cost_rates.get(short, 0.015)
                day_cost += (toks / 1000) * rate
            cost_trends.append({"date": d.get("date", ""), "cost": round(day_cost, 4)})

        self._json_response({
            "burn_rate": {
                "total_tokens": total_tokens,
                "total_cost": round(total_cost, 4),
                "request_count": total_sessions,
                "daily_token_rate": int(daily_token_rate),
                "monthly_projection": int(monthly_projection),
                "monthly_cost_projection": round(monthly_cost_projection, 2),
            },
            "heatmap": heatmap,
            "latency": {"p50": p50, "p95": p95, "p99": p99},
            "cost_trends": cost_trends,
            "model_distribution": model_dist,
        })

    def _api_v2_budget(self):
        """Return token budget info from Claude Code stats."""
        stats_path = os.path.expanduser("~/.claude/stats-cache.json")
        try:
            with open(stats_path, "r", encoding="utf-8") as f:
                stats = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return self._json_response({"budgets": []})

        # Estimate monthly budget from usage pattern
        daily_tokens = stats.get("dailyModelTokens", [])
        if not daily_tokens:
            return self._json_response({"budgets": []})

        # Sum last 30 days
        recent = daily_tokens[-30:]
        total_used = 0
        for d in recent:
            for toks in d.get("tokensByModel", {}).values():
                total_used += toks

        # Estimate monthly limit from Anthropic plan (Max plan = ~$200/month equivalent)
        monthly_limit = 50_000_000  # 50M tokens estimate for Max plan
        usage_pct = min(100, (total_used / monthly_limit) * 100) if monthly_limit > 0 else 0

        self._json_response({
            "budgets": [{
                "name": "Claude Code Monthly",
                "used": total_used,
                "limit": monthly_limit,
                "usage_pct": round(usage_pct, 1),
                "period": "monthly",
            }]
        })

    def _api_v2_stream(self):
        """Server-Sent Events stream with file-watching for real-time updates."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        import time as _time

        meta_dir = os.path.expanduser("~/.claude/usage-data/session-meta/")
        stats_path = os.path.expanduser("~/.claude/stats-cache.json")

        # Snapshot current state
        try:
            known_files = set(os.listdir(meta_dir))
        except FileNotFoundError:
            known_files = set()
        try:
            stats_mtime = os.path.getmtime(stats_path)
        except FileNotFoundError:
            stats_mtime = 0

        # Send connected event
        self.wfile.write(b"event: connected\ndata: {}\n\n")
        self.wfile.flush()

        poll_interval = 3  # seconds
        heartbeat_counter = 0

        try:
            while True:
                _time.sleep(poll_interval)
                heartbeat_counter += poll_interval
                changed = False

                # Check for new session-meta files
                try:
                    current_files = set(os.listdir(meta_dir))
                    new_files = current_files - known_files
                    if new_files:
                        known_files = current_files
                        for fname in new_files:
                            if not fname.endswith(".json"):
                                continue
                            try:
                                fpath = os.path.join(meta_dir, fname)
                                with open(fpath, "r", encoding="utf-8") as f:
                                    sess = json.load(f)
                                event_data = json.dumps({
                                    "type": "new_session",
                                    "input_tokens": sess.get("input_tokens", 0),
                                    "output_tokens": sess.get("output_tokens", 0),
                                    "model": sess.get("model", "unknown"),
                                    "duration": sess.get("duration_minutes", 0),
                                })
                                self.wfile.write(f"event: session_update\ndata: {event_data}\n\n".encode())
                                changed = True
                            except (json.JSONDecodeError, OSError):
                                continue
                except FileNotFoundError:
                    pass

                # Check if stats-cache was updated
                try:
                    new_mtime = os.path.getmtime(stats_path)
                    if new_mtime > stats_mtime:
                        stats_mtime = new_mtime
                        self.wfile.write(b"event: stats_updated\ndata: {}\n\n")
                        changed = True
                except FileNotFoundError:
                    pass

                if changed:
                    self.wfile.flush()
                elif heartbeat_counter >= 15:
                    # Heartbeat every 15s if no changes
                    heartbeat_counter = 0
                    self.wfile.write(b"event: heartbeat\ndata: {}\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass  # Client disconnected

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
            try:
                port = int(sys.argv[idx + 1])
            except ValueError:
                print(f"Invalid port: {sys.argv[idx + 1]}, using default {DEFAULT_PORT}")


    server = ThreadedHTTPServer(("127.0.0.1", port), RouterHandler)
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    print(f"Router Web UI running at http://localhost:{port}")
    print(f"Serving files from {WEBSITE_DIR}")
    print(f"GROQ_API_KEY: {'set' if groq_key else 'NOT SET — translation disabled'}")
    print("Press Ctrl+C to stop.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
