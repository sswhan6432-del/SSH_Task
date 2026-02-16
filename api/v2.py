"""v2 Enterprise API Blueprint.

Authenticated endpoints with rate limiting, token budget management,
priority queue routing, analytics, and SSE real-time updates.
"""

import json
import os
import sys
import subprocess
import time
import threading
import queue as stdlib_queue

from flask import Blueprint, request, jsonify, Response, stream_with_context

from api.auth import require_api_key, generate_api_key, list_keys, revoke_key
from api.middleware import rate_limiter, log_request
from services.token_budget import budget_manager, count_tokens
from services.model_registry import model_registry
from services.queue_manager import queue_manager
from services.analytics import get_dashboard_data
from services.audit_log import audit_logger

v2_bp = Blueprint("v2", __name__, url_prefix="/api/v2")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from router_gui import find_router_candidates

# SSE subscribers
_sse_subscribers: list[stdlib_queue.Queue] = []
_sse_lock = threading.Lock()


def _broadcast_sse(event: str, data: dict):
    """Send SSE event to all subscribers."""
    msg = f"event: {event}\ndata: {json.dumps(data)}\n\n"
    with _sse_lock:
        dead = []
        for q in _sse_subscribers:
            try:
                q.put_nowait(msg)
            except stdlib_queue.Full:
                dead.append(q)
        for q in dead:
            _sse_subscribers.remove(q)


# ---------- Health ----------

@v2_bp.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "version": "2.0",
        "timestamp": time.time(),
        "queue_size": queue_manager.size(),
    })


# ---------- Models ----------

@v2_bp.route("/models", methods=["GET"])
def models():
    return jsonify({"models": model_registry.list_all()})


# ---------- SSE Stream ----------

@v2_bp.route("/stream", methods=["GET"])
def sse_stream():
    """Server-Sent Events endpoint for real-time dashboard updates.

    NOTE: Intentionally unauthenticated — SSE connections cannot send
    custom headers, so browser EventSource cannot attach Bearer tokens.
    Read-only metrics only; no sensitive data exposed.
    """
    q = stdlib_queue.Queue(maxsize=50)
    with _sse_lock:
        _sse_subscribers.append(q)

    def generate():
        try:
            # Send initial data
            yield f"event: connected\ndata: {json.dumps({'status': 'connected'})}\n\n"
            while True:
                try:
                    msg = q.get(timeout=30)
                    yield msg
                except stdlib_queue.Empty:
                    # Heartbeat
                    yield f"event: heartbeat\ndata: {json.dumps({'time': time.time()})}\n\n"
        except GeneratorExit:
            pass
        finally:
            with _sse_lock:
                if q in _sse_subscribers:
                    _sse_subscribers.remove(q)

    return Response(
        stream_with_context(generate()),
        content_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ---------- Authenticated Endpoints ----------

@v2_bp.route("/route", methods=["POST"])
@require_api_key
def route_task():
    """Queue-enabled routing with budget check and token counting."""
    start = time.time()
    body = request.get_json(silent=True) or {}
    key_meta = getattr(request, "api_key_meta", {})
    key_hash = key_meta.get("hash", "unknown")

    # Rate limit check
    if not rate_limiter.check_rpm(key_hash):
        log_request(key_hash, "/api/v2/route", "POST", status_code=429)
        return jsonify({"error": "Rate limit exceeded (RPM)"}), 429

    request_text = body.get("request", "").strip()
    if not request_text:
        return jsonify({"error": "Empty request"}), 400

    # Count input tokens
    input_tokens = count_tokens(request_text)

    # Budget check
    budget_name = body.get("budget", "")
    if budget_name:
        budget = budget_manager.get(budget_name)
        if budget and budget.remaining < input_tokens:
            return jsonify({"error": f"Budget '{budget_name}' exhausted ({budget.remaining} tokens remaining)"}), 402

    # Token rate limit check
    if not rate_limiter.check_tokens(key_hash, input_tokens):
        log_request(key_hash, "/api/v2/route", "POST", tokens=input_tokens, status_code=429)
        return jsonify({"error": "Token rate limit exceeded (hourly)"}), 429

    # Model selection
    model_id = body.get("model", "claude-sonnet")
    model = model_registry.get(model_id)
    if not model:
        return jsonify({"error": f"Unknown model: {model_id}"}), 400

    # Enqueue task
    priority = body.get("priority", 5)
    queue_item = queue_manager.enqueue(
        payload={"request": request_text, "model": model_id, **body},
        priority=priority,
    )
    if not queue_item:
        return jsonify({"error": "Queue full, try again later"}), 503

    # Process (dequeue and execute)
    item = queue_manager.dequeue()
    if not item:
        return jsonify({"error": "Queue processing error"}), 500

    # Execute via subprocess (same as v1)
    router = body.get("router", "").strip()
    candidates = find_router_candidates()
    candidate_paths = [os.path.abspath(c) for c in candidates]

    if not router or os.path.abspath(router) not in candidate_paths:
        # Use first available router
        if candidates:
            router = candidates[0]
        else:
            return jsonify({"error": "No router available"}), 500

    cmd = [sys.executable, router]
    economy = body.get("economy", "strict")
    cmd.extend(["--economy", economy])
    cmd.append(request_text)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd(), timeout=120)
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Router timed out (120s)"}), 504
    except Exception as e:
        import logging
        logging.error(f"Router execution failed: {e}")
        return jsonify({"error": "Router execution failed"}), 500

    out = (result.stdout or "").strip()
    err = (result.stderr or "").strip()
    combined = out
    if err:
        combined += "\n\n--- STDERR ---\n" + err

    # Count output tokens
    output_tokens = count_tokens(combined)
    total_tokens = input_tokens + output_tokens

    # Budget consumption
    alert = None
    if budget_name:
        alert = budget_manager.consume(budget_name, total_tokens)

    # Cost calculation
    cost = model.cost_estimate(input_tokens, output_tokens)

    # Record token usage
    _record_usage(input_tokens, output_tokens, cost, model_id, key_hash)

    latency = (time.time() - start) * 1000
    log_request(key_hash, "/api/v2/route", "POST", tokens=total_tokens, latency_ms=latency)

    # SSE broadcast
    _broadcast_sse("route_complete", {
        "model": model_id,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost": round(cost, 6),
        "latency_ms": round(latency, 1),
    })

    if alert:
        _broadcast_sse("budget_alert", {"message": alert})

    resp = {
        "output": combined,
        "tokens": {
            "input": input_tokens,
            "output": output_tokens,
            "total": total_tokens,
        },
        "cost": round(cost, 6),
        "model": model_id,
        "latency_ms": round(latency, 1),
        "budget_alert": alert,
    }
    return jsonify(resp)


_usage_lock = threading.Lock()


def _record_usage(input_tokens: int, output_tokens: int, cost: float,
                  model_id: str, key_hash: str):
    """Record token usage for analytics (thread-safe atomic write)."""
    usage_file = os.path.join(BASE_DIR, "data", "token_usage.json")
    entry = {
        "timestamp": time.time(),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "tokens": input_tokens + output_tokens,
        "cost": round(cost, 6),
        "model": model_id,
        "key_hash": key_hash[:12] if key_hash else "unknown",
        "latency_ms": 0,
    }

    with _usage_lock:
        os.makedirs(os.path.dirname(usage_file), exist_ok=True)
        try:
            with open(usage_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            data = []

        data.append(entry)
        if len(data) > 10000:
            data = data[-10000:]

        # Atomic write via temp file + rename
        tmp_file = usage_file + ".tmp"
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_file, usage_file)
        except OSError:
            # Fallback: direct write
            try:
                with open(usage_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            except OSError:
                pass


# ---------- Analytics ----------

@v2_bp.route("/analytics", methods=["GET"])
@require_api_key
def analytics():
    """Dashboard analytics data."""
    period = request.args.get("period", "24h")
    if period not in ("1h", "24h", "7d", "30d"):
        period = "24h"
    data = get_dashboard_data(period)
    return jsonify(data)


# ---------- Budget ----------

@v2_bp.route("/budget", methods=["GET"])
@require_api_key
def budget_list():
    """List all budgets."""
    return jsonify({"budgets": budget_manager.summary()})


@v2_bp.route("/budget", methods=["POST"])
@require_api_key
def budget_create():
    """Create or update a budget."""
    body = request.get_json(silent=True) or {}
    name = body.get("name", "").strip()
    limit = body.get("limit", 0)
    period = body.get("period", "monthly")

    if not name or limit <= 0:
        return jsonify({"error": "name and positive limit required"}), 400

    budget = budget_manager.create(name, limit, period)
    return jsonify({"budget": budget.to_dict()}), 201


@v2_bp.route("/budget/<name>", methods=["DELETE"])
@require_api_key
def budget_delete(name):
    """Delete a budget."""
    if budget_manager.delete(name):
        return jsonify({"deleted": True})
    return jsonify({"error": "Budget not found"}), 404


# ---------- Queue ----------

@v2_bp.route("/queue", methods=["GET"])
@require_api_key
def queue_status():
    """Queue status."""
    return jsonify(queue_manager.status())


# ---------- API Keys ----------

@v2_bp.route("/keys", methods=["POST"])
@require_api_key
def create_key():
    """Generate a new API key."""
    body = request.get_json(silent=True) or {}
    name = body.get("name", "unnamed")
    result = generate_api_key(name)
    return jsonify(result), 201


@v2_bp.route("/keys", methods=["GET"])
@require_api_key
def get_keys():
    """List all API keys."""
    return jsonify({"keys": list_keys()})


# ---------- Audit Log ----------

@v2_bp.route("/audit", methods=["GET"])
@require_api_key
def get_audit_log():
    """Get recent audit log entries."""
    limit = request.args.get("limit", 100, type=int)
    return jsonify({"entries": audit_logger.get_recent(limit)})
