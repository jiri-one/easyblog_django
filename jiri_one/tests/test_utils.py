from pathlib import Path
from datetime import datetime
# internal django imports
from django.conf import settings
# internal imports
from jiri_one.utils import create_new_file_name, jiri_one_db_file_rotate


def test_create_new_file_name(tmp_path: Path):
    """ If I put random name, this function will add ' (1)' to its name or increment (1) by one if that file exists
    """
    file = tmp_path / "random_name.json"
    assert "random_name (1).json" == create_new_file_name(file).name
    for counter in range(1,6):
        (tmp_path / f"random_name ({counter}).json").write_text("some text")
        assert f"random_name ({counter+1}).json" == create_new_file_name(file).name
        
def test_jiri_one_db_file_rotate(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "DB_BACKUP_DIR", tmp_path)
    latest_file = tmp_path / "db_jiri_one_latest.json"
    # check basic state, without db_jiri_one_latest.json file
    assert str(latest_file) == jiri_one_db_file_rotate()
    # check jiri_one_db_file_rotate function if file db_jiri_one_latest.json exists already
    latest_file.write_text("some text") # create latest_file
    mtime = latest_file.stat().st_mtime
    time_part = datetime.fromtimestamp(mtime).strftime('%y-%m-%d_%H:%M')
    new_file_name = tmp_path / f'db_jiri_one_{time_part}.json'
    latest_file.rename(new_file_name)
    jiri_one_db_file_rotate()
    assert new_file_name.exists()
    assert new_file_name.read_text() == "some text"
