from flask import Blueprint

bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    return "<h1>Log Monitor</h1><p>Hello World. The API is running. See <a href='/health'>/health</a>.</p>"
