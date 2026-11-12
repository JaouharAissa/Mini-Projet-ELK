import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from ..services.validation import ALLOWED_EXTENSIONS, ValidationError, validate_file

bp = Blueprint("upload", __name__)
log = logging.getLogger("webapp.upload")


def _receive():
    """Save the posted file to the tmp folder. Return (tmp_path, ext, original_name)."""
    f = request.files.get("file")
    if not f or not f.filename:
        raise ValidationError("No file received (form field name must be 'file').")
    original = secure_filename(f.filename)
    ext = Path(original).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError("Unsupported format. Allowed: " + ", ".join(sorted(ALLOWED_EXTENSIONS)))
    tmp_dir = Path(current_app.config["UPLOAD_DIR"]) / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / f"{uuid.uuid4().hex}{ext}"
    f.save(tmp_path)
    return tmp_path, ext, original


@bp.post("/api/v1/upload/preview")
def preview():
    """Validate a file and return its first 10 rows, without ingesting it."""
    try:
        tmp, ext, original = _receive()
    except ValidationError as exc:
        return jsonify(error=str(exc)), 400
    try:
        count, rows = validate_file(tmp, ext)
    except ValidationError as exc:
        return jsonify(error=str(exc)), 422
    finally:
        tmp.unlink(missing_ok=True)
    return jsonify(filename=original, log_count=count, preview=rows)


@bp.post("/upload")
def upload():
    cfg = current_app.config
    try:
        tmp, ext, original = _receive()
    except ValidationError as exc:
        return jsonify(error=str(exc)), 400
    try:
        count, _ = validate_file(tmp, ext)
    except ValidationError as exc:
        tmp.unlink(missing_ok=True)
        return jsonify(error=str(exc)), 422

    kind = ext[1:]
    dest = Path(cfg["UPLOAD_DIR"]) / kind / tmp.name
    os.replace(tmp, dest)  # atomic: Logstash only sees complete files

    doc = {
        "filename": original,
        "stored_name": tmp.name,
        "type": kind,
        "size_bytes": dest.stat().st_size,
        "log_count": count,
        "status": "pending",
        "uploaded_at": datetime.now(timezone.utc),
        "uploaded_by": None,
    }
    try:
        result = current_app.extensions["db"].files.insert_one(doc)
    except Exception:
        log.exception("Could not save file metadata")
        return jsonify(error="File accepted but metadata could not be saved."), 503

    log.info("Uploaded %s (%d logs)", original, count)
    return jsonify(id=str(result.inserted_id), filename=original,
                   log_count=count, status="pending"), 201
