import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

import schedule

BACKUP_DIR = Path(os.getenv("BACKUP_DIR", "/backups"))
DB_HOST = os.getenv("DB_HOST", "db")
DB_USER = os.getenv("DB_USER", "maslul")
DB_NAME = os.getenv("DB_NAME", "maslul")
KEEP = int(os.getenv("BACKUP_KEEP", "10"))


def backup():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = BACKUP_DIR / f"{ts}.sql.gz"
    result = subprocess.run(
        f"pg_dump -U {DB_USER} -h {DB_HOST} {DB_NAME} | gzip > {out}",
        shell=True,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"[{ts}] backup ok: {out}", flush=True)
        prune()
    else:
        print(f"[{ts}] backup failed: {result.stderr}", flush=True)
        out.unlink(missing_ok=True)


def prune():
    backups = sorted(BACKUP_DIR.glob("*.sql.gz"), reverse=True)
    for old in backups[KEEP:]:
        old.unlink()
        print(f"pruned {old}", flush=True)


backup()
schedule.every(1).hour.do(backup)

while True:
    schedule.run_pending()
    time.sleep(30)
