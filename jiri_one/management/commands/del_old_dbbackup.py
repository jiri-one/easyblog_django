import asyncio
from types import FunctionType
# django imports
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
# internal django imports
from easycron.models import TaskResult

class Command(BaseCommand):
    help = 'Delete old database backup files for jiri_one app'
        
    async def delete_old_db_files(self):
        db_backup_dir = settings.DB_BACKUP_DIR
        db_backup_files = sorted([file for file in db_backup_dir.iterdir()])
        print(db_backup_files)
        # if self.interactive:
            
        
    def add_arguments(self, parser):
        parser.add_argument('interactive', type=bool, required=False, default=True)
    
    def handle(self, *args, **options):
        self.interactive = options['interactive']
        self.stdout.write(self.style.NOTICE('Deleting old database backup files begins'))
        start_time = timezone.now()
        asyncio.run(self.delete_old_db_files())
        time = timezone.now() - start_time
        self.stdout.write(self.style.SUCCESS(f'Successfully have been writen/updated temperatures and it takes {time.seconds//60} minutes and {time.seconds%60} seconds.'))
        # if self.not_updated > 0:
        #     self.stdout.write(self.style.NOTICE(f'And {self.not_updated} temperatures were not updated.'))
