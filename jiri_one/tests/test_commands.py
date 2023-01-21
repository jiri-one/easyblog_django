from io import StringIO
from django.core.management import call_command
from django.test import TestCase
import pytest
from jiri_one.models import Post, Author


def test_del_old_dbbackup():
    out = StringIO()
    call_command('del_old_dbbackup', stdout=out)
    assert 'Deleting old database backup files begins\nNo more than 10 files were found, so there is nothing to delete.\n' == out.getvalue()
