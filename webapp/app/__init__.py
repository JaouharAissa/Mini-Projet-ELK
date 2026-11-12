import logging

from flask import Flask

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

    from .routes.health import bp as health_bp
    from .routes.main import bp as main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(health_bp)

    startup_check(app)
    return app
