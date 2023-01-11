from datetime import datetime
from pathlib import Path
from django.conf import settings

def jiri_one_db_file_name():
    db_backup_dir = getattr(settings, 'DB_BACKUP_DIR', Path(__file__).parent / "db_backup")
    db_backup_dir.mkdir(exist_ok=True)
    db_backup_dir = str(db_backup_dir)
    return datetime.now().strftime(f"{db_backup_dir}/db_jiri_one_%y-%m-%d_%H:%M.json")
