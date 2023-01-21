from io import StringIO
from django.core.management import call_command
from django.test import TestCase

class ClosepollTest(TestCase):
    def test_del_old_dbbackup(self):
        out = StringIO()
        call_command('del_old_dbbackup', stdout=out)
        self.assertIn('Deleting old database backup files begins\nNo more than 10 files were found, so there is nothing to delete.\n', out.getvalue())
