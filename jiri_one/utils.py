from datetime import datetime
from pathlib import Path
from django.conf import settings

def jiri_one_db_file_rotate():
    db_backup_dir = getattr(settings, 'DB_BACKUP_DIR', Path(__file__).parent / "db_backup")
    db_backup_dir.mkdir(exist_ok=True)
    # rename the original lastest file
    lastest_file = db_backup_dir / "db_jiri_one_latest.json"
    if lastest_file.exists():
        mtime = lastest_file.stat().st_mtime
        time_part = datetime.fromtimestamp(mtime).strftime('%y-%m-%d_%H:%M')
        new_file_name = db_backup_dir / f'db_jiri_one_{time_part}.json'
        lastest_file.rename(new_file_name)
        assert not lastest_file.exists()
    # leave only the last 10 files, delete the rest
    db_files_in_dir = [file for file in db_backup_dir if "db_jiri_one" in file.name and file.is_file()]
    if len(db_files_in_dir) > 10:
        db_files_in_dir = sorted(db_files_in_dir)
        del_files = db_files_in_dir[0:9]
        for del_file in del_files:
            del_file.unlink()   
    return f"{str(db_backup_dir)}/db_jiri_one_latest.json"
