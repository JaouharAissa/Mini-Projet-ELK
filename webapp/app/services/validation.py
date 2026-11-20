"""Validation of uploaded log files (format, structure, content)."""
import csv
import ipaddress
import json
import re
from pathlib import Path

ALLOWED_EXTENSIONS = {".csv", ".json", ".txt"}
EXPECTED_COLUMNS = ["timestamp", "level", "service", "event_type",
                    "src_ip", "username", "message"]
PREVIEW_LINES = 10

# Same field order as the grok pattern in elk/logstash/pipeline/txt.conf
TXT_LINE = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}\S*) "
    r"(?P<level>[A-Za-z]+) (?P<service>\S+) (?P<event_type>\S+) "
    r"(?P<src_ip>\S+) (?P<username>\S+) (?P<message>.+)$"
)


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


def _validate_txt(path):
    count, preview = 0, []
    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.rstrip("\r\n")
            if not line.strip():
                continue
            m = TXT_LINE.match(line)
            if not m:
                raise ValidationError(
                    f"Line {line_no}: expected '<timestamp> <level> <service> "
                    "<event_type> <src_ip> <username> <message>'.")
            ip = m.group("src_ip")
            try:
                ipaddress.ip_address(ip)
            except ValueError:
                raise ValidationError(f"Line {line_no}: invalid IP address {ip}.")
            count += 1
            if len(preview) < PREVIEW_LINES:
                preview.append(m.groupdict())
    if count == 0:
        raise ValidationError("The TXT file contains no events.")
    return count, preview


PARSERS = {".csv": _validate_csv, ".json": _validate_json, ".txt": _validate_txt}


def validate_file(path: Path, ext: str):
    """Return (number_of_logs, first_10_rows). Raise ValidationError if invalid."""
    try:
        return PARSERS[ext](path)
    except UnicodeDecodeError:
        raise ValidationError("The file is not valid UTF-8 text.")
