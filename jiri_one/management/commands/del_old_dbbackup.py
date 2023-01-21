import asyncio
from argparse import BooleanOptionalAction
# django imports
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = 'Delete old database backup files for jiri_one app'
        
    async def delete_old_db_files(self):
        db_backup_dir = settings.DB_BACKUP_DIR
        # leave only the last 10 files, delete the rest
        db_backup_files = sorted([file for file in db_backup_dir.iterdir() if "db_jiri_one" in file.name and file.is_file()])
        if len(db_backup_files) > 10:
            db_backup_files = sorted(db_backup_files)
            del_files = db_backup_files[10:]
            delete = True
            if self.interactive:
                self.stdout.write(self.style.NOTICE(f'It was found {len(del_files)} files, those are {", ".join([file.name for file in del_files])}'))
                user_decision = input(f"Would you like to delete those files (yes for delete, anything else for preserve them):")
                if user_decision != "yes":
                    delete = False
            if delete:
                for del_file in del_files:
                    del_file.unlink()
        else:
            self.stdout.write(self.style.NOTICE('No more than 10 files were found, so there is nothing to delete.'))
        
    def add_arguments(self, parser):
        parser.add_argument('--interactive', default=True, action=BooleanOptionalAction)
    
    def handle(self, *args, **options):
        self.interactive = options.get('interactive')
        self.stdout.write(self.style.NOTICE('Deleting old database backup files begins'))
        asyncio.run(self.delete_old_db_files())
