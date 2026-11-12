"""Connections to Elasticsearch, MongoDB and Redis."""
import logging

import redis
from elasticsearch import Elasticsearch
from pymongo import MongoClient

log = logging.getLogger("webapp.clients")


def init_clients(app):
    cfg = app.config
    app.extensions["es"] = Elasticsearch(cfg["ELASTICSEARCH_URL"], request_timeout=5)
    mongo = MongoClient(cfg["MONGO_URI"], serverSelectionTimeoutMS=3000)
    app.extensions["mongo"] = mongo
    app.extensions["db"] = mongo[cfg["MONGO_DB"]]
    app.extensions["redis"] = redis.Redis(
        host=cfg["REDIS_HOST"],
        port=cfg["REDIS_PORT"],
        password=cfg["REDIS_PASSWORD"],
        decode_responses=True,
        socket_timeout=3,
        socket_connect_timeout=3,
    )


def startup_check(app):
    """Log connectivity of each dependency at startup (never crash the app)."""
    ext = app.extensions
    checks = {
        "elasticsearch": lambda: ext["es"].info(),
        "mongodb": lambda: ext["mongo"].admin.command("ping"),
        "redis": lambda: ext["redis"].ping(),
    }
    for name, fn in checks.items():
        try:
            fn()
            log.info("%s: connection OK", name)
        except Exception as exc:
            log.error("%s: connection FAILED (%s)", name, exc)
