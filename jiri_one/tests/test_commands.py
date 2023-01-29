from pathlib import Path
from io import StringIO
from django.core.management import call_command
from django.test import TestCase
import pytest
# internal django imports
from django.conf import settings
from jiri_one.models import Post, Author

# FIXTURES for tests
@pytest.fixture
def fix_me_post() -> Post:
    """Create a post with with bad html link."""
    author, _ = Author.objects.get_or_create(nick="Test", defaults={"nick": "Test", "first_name": "Test", "last_name": "Test"})
    content = """<a href="/soubory/soubor.neco">soubor</a>"""
    return Post.objects.create(title_cze="bad html", content_cze=content, author=author)

# TESTS

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


@pytest.mark.django_db
def test_fix_internal_urls(fix_me_post):
    out = StringIO()
    assert isinstance(fix_me_post, Post)
    assert "/soubory" in fix_me_post.content_cze
    call_command('fix_internal_urls', stdout=out)
    fix_me_post.refresh_from_db() # we need refresh this instance from DB
    assert "/soubory" not in fix_me_post.content_cze
    assert "/files" in fix_me_post.content_cze
