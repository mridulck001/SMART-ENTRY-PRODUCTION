import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

from flask import Flask, render_template, jsonify, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import config_map

# ── Extensions (initialized before app) ───────────────────────
db = SQLAlchemy()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["300 per hour", "60 per minute"],
)


def create_app(env: str = None) -> Flask:
    app = Flask(__name__)

    # ── Config ─────────────────────────────────────────────────
    env = env or os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config_map.get(env, config_map['default']))

    # ── Extensions ─────────────────────────────────────────────
    db.init_app(app)
    limiter.init_app(app)

    # ── Instance folder ────────────────────────────────────────
    os.makedirs(app.instance_path, exist_ok=True)

    # ── Logging ────────────────────────────────────────────────
    _configure_logging(app)

    # ── Blueprints ─────────────────────────────────────────────
    from app.routes.portal import portal_bp
    from app.routes.gate   import gate_bp
    from app.routes.manual import manual_bp
    from app.routes.admin  import admin_bp

    app.register_blueprint(portal_bp)
    app.register_blueprint(gate_bp)
    app.register_blueprint(manual_bp)
    app.register_blueprint(admin_bp)

    # ── Home route ─────────────────────────────────────────────
    @app.route('/')
    def home():
        return render_template('index.html')

    @app.route('/health')
    def health():
        """Health-check endpoint for load balancers / Docker."""
        try:
            db.session.execute(db.text('SELECT 1'))
            return jsonify({'status': 'ok', 'database': 'connected'}), 200
        except Exception as e:
            app.logger.error(f"Health check failed: {e}")
            return jsonify({'status': 'error', 'database': 'disconnected'}), 503

    @app.context_processor
    def inject_ui_context():
        endpoint = request.endpoint or ''
        section = 'general'
        if endpoint.startswith('gate.'):
            section = 'scanner'
        elif endpoint.startswith('admin.'):
            section = 'admin'

        return {
            'ui_section': section,
            'is_admin_session': bool(session.get('is_admin')),
            'current_year': datetime.now().year,
        }

    # ── Error handlers ─────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'status': 'error', 'message': 'Resource not found.'}), 404

    @app.errorhandler(429)
    def rate_limited(e):
        return jsonify({
            'status': 'error',
            'message': 'Too many requests. Please slow down.',
        }), 429

    @app.errorhandler(500)
    def server_error(e):
        app.logger.error(f"Unhandled server error: {e}")
        return jsonify({'status': 'error', 'message': 'Internal server error.'}), 500

    # ── Database tables ────────────────────────────────────────
    with app.app_context():
        db.create_all()

    return app


def _configure_logging(app: Flask):
    level = logging.DEBUG if app.debug else logging.INFO
    fmt   = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )

    # Console handler (always on)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)
    stream_handler.setLevel(level)

    # Rotating file handler
    log_dir = os.path.join(app.instance_path, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=5 * 1024 * 1024,   # 5 MB per file
        backupCount=5,
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(level)

    app.logger.handlers.clear()
    app.logger.addHandler(stream_handler)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(level)
    app.logger.propagate = False
