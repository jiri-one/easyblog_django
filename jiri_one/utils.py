from datetime import datetime
from pathlib import Path
from django.conf import settings


def create_new_file_name(new_file_name: Path):
    counter = 1
    name = new_file_name.stem
    suffix = new_file_name.suffix
    while True:
        new_name = name + f" ({counter}){suffix}"
        new_file_name = new_file_name.parent / new_name
        if new_file_name.exists():
            counter += 1
        else:
            return new_file_name
    

def jiri_one_db_file_rotate():
    db_backup_dir = getattr(settings, 'DB_BACKUP_DIR', Path(__file__).parent / "db_backup")
    db_backup_dir.mkdir(exist_ok=True)
    # rename the original lastest file
    lastest_file = db_backup_dir / "db_jiri_one_latest.json"
    if lastest_file.exists():
        mtime = lastest_file.stat().st_mtime
        time_part = datetime.fromtimestamp(mtime).strftime('%y-%m-%d_%H:%M')
        new_file_name = db_backup_dir / f'db_jiri_one_{time_part}.json'
        if new_file_name.exists():
            new_file_name = create_new_file_name(new_file_name)
            print(new_file_name)
        lastest_file.rename(new_file_name)
    return f"{str(db_backup_dir)}/db_jiri_one_latest.json"
