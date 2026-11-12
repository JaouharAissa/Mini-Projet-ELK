import logging

from flask import Flask, jsonify

from .config import Config
from .services.clients import init_clients, startup_check


def create_app():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app = Flask(__name__)
    app.config.from_object(Config)

    init_clients(app)

    from .routes.api import bp as api_bp
    from .routes.health import bp as health_bp
    from .routes.main import bp as main_bp
    from .routes.upload import bp as upload_bp

    for bp in (main_bp, health_bp, upload_bp, api_bp):
        app.register_blueprint(bp)

    @app.errorhandler(413)
    def too_large(_):
        return jsonify(error=f"File too large (max {app.config['MAX_UPLOAD_MB']} MB)."), 413

    startup_check(app)
    return app
