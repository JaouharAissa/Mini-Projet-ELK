#!/usr/bin/env python3
"""Generate fake security logs (CSV + JSON lines) for the ELK project."""
import argparse
import csv
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from faker import Faker

fake = Faker()

# (service, event_type, level, message template)
EVENTS = [
    ("auth", "login_success", "INFO", "User {user} logged in"),
    ("auth", "login_failed", "WARNING", "Failed login attempt for {user}"),
    ("auth", "logout", "INFO", "User {user} logged out"),
    ("ids", "sql_injection_attempt", "CRITICAL", "SQL injection pattern detected in request"),
    ("ids", "port_scan", "ERROR", "Port scan detected from source"),
    ("firewall", "firewall_block", "WARNING", "Connection blocked by firewall rule"),
    ("firewall", "firewall_allow", "DEBUG", "Connection allowed by firewall rule"),
    ("webapp", "sensitive_file_access", "WARNING", "Access to confidential resource by {user}"),
    ("audit", "admin_action", "INFO", "Administrator {user} changed a configuration"),
    ("audit", "config_change", "INFO", "Configuration modified by {user}"),
]
WEIGHTS = [30, 25, 10, 3, 3, 10, 8, 4, 4, 3]
USERS = ["admin", "root", "jaouhar", "analyst1", "analyst2", "svc_backup", "guest", "dbadmin"]


def make_event(ts, ip=None, forced=None):
    service, etype, level, tpl = forced or random.choices(EVENTS, WEIGHTS)[0]
    user = random.choice(USERS)
    return {
        "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "level": level,
        "service": service,
        "event_type": etype,
        "src_ip": ip or fake.ipv4_public(),
        "username": user,
        "message": tpl.format(user=user),
    }


def generate(n, days):
    now = datetime.now(timezone.utc)
    events = []
    for _ in range(n):
        ts = now - timedelta(seconds=random.randint(0, days * 86400))
        events.append(make_event(ts))

    # Simulated brute-force attacks: same IP, many failed logins within minutes
    failed = next(e for e in EVENTS if e[1] == "login_failed")
    for _ in range(max(3, n // 500)):
        ip = fake.ipv4_public()
        start = now - timedelta(seconds=random.randint(0, days * 86400))
        for i in range(random.randint(6, 15)):
            events.append(make_event(start + timedelta(seconds=i * 20), ip, failed))

    events.sort(key=lambda e: e["timestamp"])
    return events


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-n", "--count", type=int, default=2000)
    p.add_argument("-d", "--days", type=int, default=7)
    p.add_argument("-o", "--out", default="sample_logs")
    a = p.parse_args()

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    events = generate(a.count, a.days)
    cols = ["timestamp", "level", "service", "event_type", "src_ip", "username", "message"]

    with open(out / "security_logs.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(events)

    with open(out / "security_logs.json", "w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")

    print(f"{len(events)} events written to {out}/security_logs.csv and .json")


if __name__ == "__main__":
    main()
