import traceback
import asyncio
from time import sleep
from types import FunctionType
# django imports
from django.core.management import find_commands, load_command_class, call_command
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
# internal django imports
from easycron.models import TaskResult

class Command(BaseCommand):
    help = 'Delete old database backup files for jiri_one app'
        
    async def delete_old_db_files(self):
        

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Deleting old database backup files begins'))
        start_time = timezone.now()
        asyncio.run(self.delete_old_db_files())
        time = timezone.now() - start_time
        self.stdout.write(self.style.SUCCESS(f'Successfully have been writen/updated temperatures and it takes {time.seconds//60} minutes and {time.seconds%60} seconds.'))
        # if self.not_updated > 0:
        #     self.stdout.write(self.style.NOTICE(f'And {self.not_updated} temperatures were not updated.'))
