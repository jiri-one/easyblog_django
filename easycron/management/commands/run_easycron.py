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
    help = 'Runs background tasks.'
    
    def run_task(self, task):
        name, app, cmd, schedule = task['name'], task['app'], task['command'], task['schedule']
        args = []
        for arg in task['args']:
            if isinstance(arg, FunctionType):
                arg = arg()
            args.append(arg)
        while True:
            latest_run = TaskResult.objects.filter(name=name).order_by('started_at').last()
            if ( not latest_run ) or ( latest_run.started_at + schedule < timezone.now() ):
                # Create a new entry or get entry from database
                task_obj = TaskResult.objects.create(name=name)
                try:
                    cmd_class = load_command_class(app, cmd)
                    call_command(cmd_class, *args)
                except ModuleNotFoundError as e: # TODO: more exceptions
                    output = e
                    # Mark task as failed
                    task_obj.success = False
                else: # if no exception
                    # Mark task finished successfully
                    task_obj.success = True
                    output = 'OK'
                finally: # allways call this code
                    task_obj.finished_at = timezone.now()
                    task_obj.output = output
                    task_obj.save(update_fields=['finished_at', 'success', 'output'])
                    sleep(schedule.seconds)
            else:
                # + 1 is here only for sure, that next time the task will be run
                sleep(schedule.seconds - (timezone.now() - latest_run.started_at).seconds + 1)
    
    async def process_tasks(self):
        loop = asyncio.get_running_loop()
        tasks_results = dict()
        for task in getattr(settings, 'EASYCRON_TASKS', []):
            # asyncio.sleep(2)
            task_name = task['name']
            tasks_results[task_name] = await loop.run_in_executor(None, self.run_task, task)
            # 


                
                # Run it
                # func_output = io.StringIO()
                # default_stdout = sys.stdout
                # default_stderr = sys.stderr
                # sys.stdout = func_output
                # sys.stderr = func_output
                # try:
                #     handle_func()
                # except Exception as err:
                #     # Mark task failed
                #     result.finished_at = timezone.now()
                #     result.success = False
                #     result.output = func_output.getvalue() + traceback.format_exc()
                #     result.save(update_fields=['finished_at', 'success', 'output'])
                #     # Try the next task
                #     continue
                # finally:
                #     sys.stdout = default_stdout
                #     sys.stderr = default_stderr

                # # Mark task finished successfully
                # result.finished_at = timezone.now()
                # result.success = True
                # result.output = func_output.getvalue()
                # result.save(update_fields=['finished_at', 'success', 'output'])

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Temperature update has been started. There is lot of data to be updated, please be patient ...'))
        start_time = timezone.now()
        asyncio.run(self.process_tasks())
        time = timezone.now() - start_time
        self.stdout.write(self.style.SUCCESS(f'Successfully have been writen/updated temperatures and it takes {time.seconds//60} minutes and {time.seconds%60} seconds.'))
        # if self.not_updated > 0:
        #     self.stdout.write(self.style.NOTICE(f'And {self.not_updated} temperatures were not updated.'))
