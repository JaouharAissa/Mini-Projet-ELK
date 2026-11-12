import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from elasticsearch import ApiError, TransportError
from flask import Blueprint, current_app, jsonify, request

bp = Blueprint("api", __name__)
log = logging.getLogger("webapp.api")

LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
SORT_FIELDS = {"date": "@timestamp", "level": "level", "service": "service"}


class BadParams(Exception):
    pass


def parse_params(args):
    try:
        page = max(int(args.get("page", 1)), 1)
        size = min(max(int(args.get("size", 50)), 1), 100)
    except ValueError:
        raise BadParams("page and size must be integers.")
    if page * size > 10000:
        raise BadParams("Cannot page beyond 10,000 results; refine your filters.")
    level = args.get("level", "").upper()
    if level and level not in LEVELS:
        raise BadParams("level must be one of: " + ", ".join(sorted(LEVELS)))
    sort = args.get("sort", "date")
    if sort not in SORT_FIELDS:
        raise BadParams("sort must be one of: " + ", ".join(SORT_FIELDS))
    order = args.get("order", "desc")
    if order not in ("asc", "desc"):
        raise BadParams("order must be asc or desc.")
    dates = {}
    for key in ("date_from", "date_to"):
        value = args.get(key, "").strip()
        if value:
            try:
                datetime.fromisoformat(value)
            except ValueError:
                raise BadParams(f"{key} must be an ISO date (YYYY-MM-DD).")
        dates[key] = value
    return {"q": args.get("q", "").strip(), "level": level,
            "service": args.get("service", "").strip(),
            "page": page, "size": size, "sort": sort, "order": order, **dates}


def build_query(p):
    must, flt = [], []
    if p["q"]:
        must.append({"simple_query_string": {
            "query": p["q"], "fields": ["message", "username", "event_type"],
            "default_operator": "and"}})
    if p["level"]:
        flt.append({"term": {"level": p["level"]}})
    if p["service"]:
        flt.append({"term": {"service": p["service"]}})
    if p["date_from"] or p["date_to"]:
        rng = {}
        if p["date_from"]:
            rng["gte"] = p["date_from"]
        if p["date_to"]:
            end = p["date_to"]
            rng["lte"] = end + "||/d" if len(end) == 10 else end  # whole last day
        flt.append({"range": {"@timestamp": rng}})
    if not must and not flt:
        return {"match_all": {}}
    return {"bool": {"must": must, "filter": flt}}


def run_search(p):
    ext = current_app.extensions
    key = "cache:search:" + hashlib.sha1(json.dumps(p, sort_keys=True).encode()).hexdigest()
    try:
        hit = ext["redis"].get(key)
        if hit:
            data = json.loads(hit)
            data["cached"] = True
            return data
    except Exception as exc:
        log.warning("Redis cache read failed: %s", exc)

    field = SORT_FIELDS[p["sort"]]
    sort = [{field: {"order": p["order"]}}]
    if field != "@timestamp":
        sort.append({"@timestamp": {"order": "desc"}})
    res = ext["es"].search(
        index=current_app.config["INDEX_PATTERN"], query=build_query(p), sort=sort,
        from_=(p["page"] - 1) * p["size"], size=p["size"], track_total_hits=True)
    data = {
        "total": res["hits"]["total"]["value"],
        "page": p["page"], "size": p["size"],
        "took_ms": res["took"],
        "hits": [{"id": h["_id"], **h["_source"]} for h in res["hits"]["hits"]],
        "cached": False,
    }
    try:
        ext["redis"].setex(key, current_app.config["CACHE_TTL"], json.dumps(data))
    except Exception as exc:
        log.warning("Redis cache write failed: %s", exc)
    return data


def save_history(p, total):
    try:
        current_app.extensions["db"].searches.insert_one({
            "params": {k: v for k, v in p.items() if v not in ("", None)},
            "total": total, "user": None, "created_at": datetime.now(timezone.utc)})
    except Exception as exc:
        log.warning("Could not save search history: %s", exc)


def _search_response(history):
    try:
        params = parse_params(request.args)
        data = run_search(params)
    except BadParams as exc:
        return jsonify(error=str(exc)), 400
    except (ApiError, TransportError):
        log.exception("Elasticsearch query failed")
        return jsonify(error="Search backend unavailable."), 503
    if history:
        save_history(params, data["total"])
    return jsonify(data)


@bp.get("/search")
def search():
    return _search_response(history=True)


@bp.get("/api/v1/logs")
def list_logs():
    return _search_response(history=False)


@bp.get("/api/v1/logs/<log_id>")
def log_detail(log_id):
    try:
        res = current_app.extensions["es"].search(
            index=current_app.config["INDEX_PATTERN"],
            query={"ids": {"values": [log_id]}}, size=1)
    except (ApiError, TransportError):
        return jsonify(error="Search backend unavailable."), 503
    hits = res["hits"]["hits"]
    if not hits:
        return jsonify(error="Log not found."), 404
    return jsonify(id=hits[0]["_id"], index=hits[0]["_index"], **hits[0]["_source"])


def _iso(dt):
    return dt.isoformat() + "Z" if dt and dt.tzinfo is None else (dt.isoformat() if dt else None)


def _refresh_statuses(db, es, upload_dir, index):
    """A pending file is ingested once Elasticsearch holds all its logs.
    The webapp then deletes the file so Logstash cannot re-read it after a restart."""
    for d in db.files.find({"status": "pending"}):
        try:
            n = es.count(index=index, query={"match_phrase": {"uploaded_file": d["stored_name"]}})["count"]
        except Exception as exc:
            log.warning("Status check failed for %s: %s", d["stored_name"], exc)
            continue
        if n >= d["log_count"]:
            (Path(upload_dir) / d["type"] / d["stored_name"]).unlink(missing_ok=True)
            db.files.update_one({"_id": d["_id"]}, {"$set": {
                "status": "ingested", "ingested_at": datetime.now(timezone.utc)}})


@bp.get("/api/v1/files")
def list_files():
    db = current_app.extensions["db"]
    try:
        _refresh_statuses(db, current_app.extensions["es"], current_app.config["UPLOAD_DIR"], current_app.config["INDEX_PATTERN"])
        page = max(int(request.args.get("page", 1)), 1)
        size = min(max(int(request.args.get("size", 20)), 1), 100)
        query = {}
        if request.args.get("status"):
            query["status"] = request.args["status"]
        total = db.files.count_documents(query)
        docs = db.files.find(query).sort("uploaded_at", -1).skip((page - 1) * size).limit(size)
        files = []
        for d in docs:
            d["id"] = str(d.pop("_id"))
            d["uploaded_at"] = _iso(d.get("uploaded_at"))
            d["ingested_at"] = _iso(d.get("ingested_at"))
            files.append(d)
    except ValueError:
        return jsonify(error="page and size must be integers."), 400
    except Exception:
        log.exception("MongoDB query failed")
        return jsonify(error="Database unavailable."), 503
    return jsonify(total=total, page=page, size=size, files=files)


@bp.get("/api/v1/stats")
def stats():
    ext = current_app.extensions
    idx = current_app.config["INDEX_PATTERN"]
    try:
        es = ext["es"]
        return jsonify(
            total_logs=es.count(index=idx)["count"],
            logs_today=es.count(index=idx, query={"range": {"@timestamp": {"gte": "now/d"}}})["count"],
            error_logs=es.count(index=idx, query={"terms": {"level": ["ERROR", "CRITICAL"]}})["count"],
            files_uploaded=ext["db"].files.count_documents({}))
    except Exception:
        log.exception("Stats failed")
        return jsonify(error="Stats unavailable."), 503


@bp.get("/api/v1/searches")
def list_searches():
    docs = current_app.extensions["db"].searches.find().sort("created_at", -1).limit(20)
    out = [{"id": str(d["_id"]), "params": d["params"], "total": d["total"],
            "created_at": _iso(d["created_at"])} for d in docs]
    return jsonify(searches=out)
