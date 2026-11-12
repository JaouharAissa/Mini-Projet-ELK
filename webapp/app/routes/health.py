import time

from flask import Blueprint, current_app, jsonify

bp = Blueprint("health", __name__)


def _timed(fn):
    start = time.perf_counter()
    try:
        fn()
        status, error = "up", None
    except Exception as exc:
        status, error = "down", str(exc)[:200]
    result = {"status": status, "ms": round((time.perf_counter() - start) * 1000, 1)}
    if error:
        result["error"] = error
    return result


@bp.get("/health")
def health():
    ext = current_app.extensions
    checks = {
        "elasticsearch": _timed(lambda: ext["es"].info()),
        "mongodb": _timed(lambda: ext["mongo"].admin.command("ping")),
        "redis": _timed(lambda: ext["redis"].ping()),
    }
    down = [name for name, c in checks.items() if c["status"] == "down"]
    if not down:
        status = "healthy"
    elif len(down) == len(checks):
        status = "down"
    else:
        status = "degraded"
    return jsonify(status=status, checks=checks), (200 if status == "healthy" else 503)
