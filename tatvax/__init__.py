"""TatvaX v2.5: a multilingual AI tutor, assessment platform and AI school companion (TatvAI)."""

import logging
import os
from dataclasses import dataclass

from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from . import admin, api, assignments, db, knowledge, reports, review, todos, users
from .ai import AIService
from .config import build_config
from .quiz import QuizMaster
from .security import limiter, require_json_for_writes
from .translation import Translator
from .tutor import Tutor

__version__ = "2.6.0"


@dataclass
class Services:
    ai: AIService
    translator: Translator
    tutor: Tutor
    quizmaster: QuizMaster


CONTENT_SECURITY_POLICY = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",  # React style props and KaTeX inline styles
    "font-src 'self' data:",
    "worker-src 'self'",
    "img-src 'self' data:",
    "media-src 'self' blob:",
    "connect-src 'self'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
])


def _use_system_certificates() -> None:
    """Verify HTTPS with the operating system's trust store instead of Python's bundled one,
    so school or antivirus TLS proxies trusted by the OS don't break translation and AI calls."""
    try:
        import truststore

        truststore.inject_into_ssl()
    except ImportError:
        pass


def create_app(overrides: dict | None = None) -> Flask:
    _use_system_certificates()
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    app = Flask(__name__, static_folder=None)  # the React build is served by the routes below
    app.config.update(build_config(overrides))
    app.config["VERSION"] = __version__
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if os.environ.get("TATVAX_BEHIND_PROXY"):
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    db.init_db(app.config["DATABASE"])
    limiter.configure(app.config["DATABASE"] if app.config.get("SHARED_RATE_LIMIT") else None)
    conn = db.connect(app.config["DATABASE"])
    try:
        imported = knowledge.seed_documents(conn, app.config["CONTENT_DIR"])
        if imported:
            app.logger.info("Imported %d documents into the content library", imported)
        added = review.backfill(conn)
        if added:
            app.logger.info("Added %d past mistakes to learners' review decks", added)
    finally:
        conn.close()

    ai = AIService(app.config["NVIDIA_API_KEY"], app.config["AI_MODEL"], allowed=app.config["AI_ALLOWED"])
    conn = db.connect(app.config["DATABASE"])
    try:
        ai.load({row["key"]: row["value"] for row in conn.execute("SELECT key, value FROM settings")})
    finally:
        conn.close()
    translator = Translator(ai)
    app.extensions["tatvax"] = Services(
        ai=ai,
        translator=translator,
        tutor=Tutor(ai, translator),
        quizmaster=QuizMaster(ai, translator, app.config["CONTENT_DIR"]),
    )
    app.logger.info(
        "AI tutor: %s", f"{ai.state.provider.name} ({ai.model})" if ai.available else "off - add a free NVIDIA API key in the teacher console"
    )

    app.register_blueprint(users.bp)
    app.register_blueprint(api.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(todos.bp)
    app.register_blueprint(review.bp)
    app.register_blueprint(assignments.student_bp)
    app.register_blueprint(assignments.teacher_bp)
    app.register_blueprint(reports.bp)
    app.before_request(require_json_for_writes)
    app.teardown_appcontext(db.close_db)

    register_frontend(app)

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("Permissions-Policy", "microphone=(self), camera=(), geolocation=()")
        if request.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.errorhandler(404)
    def not_found(exc):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Not found"}), 404
        return exc

    @app.errorhandler(413)
    def too_large(_exc):
        return jsonify({"error": "That request is too large"}), 413

    @app.errorhandler(500)
    def server_error(_exc):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Something went wrong on our side. Please try again."}), 500
        return "Something went wrong on our side. Please try again.", 500

    return app


FRONTEND_MISSING = """<!doctype html><meta charset="utf-8"><title>TatvaX</title>
<body style="font-family:system-ui;max-width:640px;margin:80px auto;padding:0 16px;line-height:1.6">
<h1>The TatvaX frontend hasn't been built yet</h1>
<p>Build the React app once, then reload this page:</p>
<pre style="background:#f0eee8;padding:12px">cd frontend
npm install
npm run build</pre>
<p>For frontend development, run <code>npm run dev</code> in <code>frontend/</code> and open
<a href="http://localhost:5173">http://localhost:5173</a> instead.</p></body>"""


def register_frontend(app: Flask) -> None:
    """Serve the built React app (frontend/dist) with client-side routing."""
    dist = Path(app.config["FRONTEND_DIST"])

    @app.get("/assets/<path:filename>")
    def assets(filename):
        # Vite puts a content hash in every asset name, so they can be cached for a year.
        response = send_from_directory(dist / "assets", filename, max_age=31536000)
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response

    @app.get("/", defaults={"path": ""})
    @app.get("/<path:path>")
    def spa(path):
        if path.startswith("api/"):
            return jsonify({"error": "Not found"}), 404
        if not (dist / "index.html").exists():
            return FRONTEND_MISSING, 503
        candidate = (dist / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(dist.resolve()):
            response = send_from_directory(dist, path, max_age=0)
        else:
            response = send_from_directory(dist, "index.html", max_age=0)  # client-side route
        response.headers["Cache-Control"] = "no-cache"
        return response
