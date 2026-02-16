#!/usr/bin/env python3
"""Flask application factory for SSH_WEB.

Serves static files from website/ and provides v1 (unauthenticated)
and v2 (authenticated enterprise) API endpoints.

Usage:
    python app.py [--port 8080]
"""

import os
import sys

from flask import Flask, request, send_from_directory
from flask_cors import CORS

from config import IS_VERCEL, WEBSITE_DIR


def create_app():
    app = Flask(__name__, static_folder=WEBSITE_DIR, static_url_path="")
    app.config["JSON_SORT_KEYS"] = False

    cors_origins = ["http://localhost:8080", "http://127.0.0.1:8080"]
    if IS_VERCEL:
        vercel_url = os.environ.get("VERCEL_URL", "")
        if vercel_url:
            cors_origins.append(f"https://{vercel_url}")
        cors_origins.append("https://*.vercel.app")
    CORS(app, origins=cors_origins)

    # Security + cache-control headers for all responses
    @app.after_request
    def add_security_headers(response):
        # Cache: allow static assets, disable for API
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        connect_src = "'self'"
        if IS_VERCEL:
            connect_src = "'self' https://*.vercel.app"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            f"connect-src {connect_src}; "
            "font-src 'self'"
        )
        return response

    # Register blueprints
    from api.v1 import v1_bp
    app.register_blueprint(v1_bp)

    # v2 enterprise API requires services/ (not available on Vercel)
    if not IS_VERCEL:
        try:
            from api.v2 import v2_bp
            app.register_blueprint(v2_bp)
        except ImportError:
            pass

    # Serve index
    @app.route("/")
    def serve_index():
        return send_from_directory(WEBSITE_DIR, "index.html")

    # Serve static HTML files
    @app.route("/<path:filename>")
    def serve_static(filename):
        return send_from_directory(WEBSITE_DIR, filename)

    return app


def main():
    port = 8080
    if "--port" in sys.argv:
        idx = sys.argv.index("--port")
        if idx + 1 < len(sys.argv):
            try:
                port = int(sys.argv[idx + 1])
            except ValueError:
                print(f"Invalid port: {sys.argv[idx + 1]}, using default 8080")

    app = create_app()

    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    print(f"SSH_WEB Flask server running at http://localhost:{port}")
    print(f"Serving files from {WEBSITE_DIR}")
    print(f"GROQ_API_KEY: {'set' if groq_key else 'NOT SET'}")
    print("API v1: /api/* (unauthenticated)")
    print("API v2: /api/v2/* (authenticated)")
    print("Press Ctrl+C to stop.\n")

    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
