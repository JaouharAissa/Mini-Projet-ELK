"""Validation of uploaded log files (format, structure, content)."""
import csv
import json
from pathlib import Path

ALLOWED_EXTENSIONS = {".csv", ".json"}
EXPECTED_COLUMNS = ["timestamp", "level", "service", "event_type",
                    "src_ip", "username", "message"]
PREVIEW_LINES = 10


class ValidationError(Exception):
    pass


def _validate_csv(path):
    count, preview = 0, []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            raise ValidationError("The CSV file is empty.")
        if header != EXPECTED_COLUMNS:
            raise ValidationError(
                "Invalid CSV header. Expected columns: " + ", ".join(EXPECTED_COLUMNS))
        for line_no, row in enumerate(reader, start=2):
            if len(row) != len(header):
                raise ValidationError(
                    f"Line {line_no}: {len(row)} columns found, {len(header)} expected.")
            count += 1
            if len(preview) < PREVIEW_LINES:
                preview.append(dict(zip(header, row)))
    if count == 0:
        raise ValidationError("The CSV file contains no data rows.")
    return count, preview


def _validate_json(path):
    count, preview = 0, []
    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValidationError(f"Line {line_no}: invalid JSON ({exc.msg}).")
            if not isinstance(obj, dict):
                raise ValidationError(f"Line {line_no}: each line must be a JSON object.")
            count += 1
            if len(preview) < PREVIEW_LINES:
                preview.append(obj)
    if count == 0:
        raise ValidationError("The JSON file contains no events.")
    return count, preview


def validate_file(path: Path, ext: str):
    """Return (number_of_logs, first_10_rows). Raise ValidationError if invalid."""
    try:
        return _validate_csv(path) if ext == ".csv" else _validate_json(path)
    except UnicodeDecodeError:
        raise ValidationError("The file is not valid UTF-8 text.")
