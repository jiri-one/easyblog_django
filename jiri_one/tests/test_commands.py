from pathlib import Path
from io import StringIO
from django.core.management import call_command
from django.test import TestCase
import pytest
# internal django imports
from django.conf import settings
from jiri_one.models import Post, Author


def test_del_old_dbbackup_without_files(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "DB_BACKUP_DIR", tmp_path)
    out = StringIO()
    call_command('del_old_dbbackup', stdout=out)
    assert 'Deleting old database backup files begins\nNo more than 10 files were found, so there is nothing to delete.\n' == out.getvalue()

def test_del_old_dbbackup_with_fourteen_files(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "DB_BACKUP_DIR", tmp_path)
    # create 14 db_jiri_one_XXX.json files
    for c in range(1,15):
        c = str(c).zfill(2)
        (tmp_path / f"db_jiri_one_23-01-{c}_10:35.json").write_text("some text")   
    out = StringIO()
    assert len([x for x in tmp_path.iterdir()]) == 14
    call_command('del_old_dbbackup', interactive=False, stdout=out)
    assert len([x for x in tmp_path.iterdir()]) == 10
