import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

source = BASE_DIR / "app.db"
target_dir = BASE_DIR / "backups"
target_dir.mkdir(exist_ok=True)
target = target_dir / f"app_{datetime.now():%Y%m%d_%H%M%S}.db"

connection = sqlite3.connect(source)
backup = sqlite3.connect(target)
connection.backup(backup)
backup.close()
connection.close()
print(target)
