import traceback
from time import sleep
from concurrent.futures import ThreadPoolExecutor
# django imports
from django.core.management import find_commands, load_command_class, call_command
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
# internal django imports
from models import TaskResult

from easycron import models

class Command(BaseCommand):
    help = 'Runs background tasks.'
    
    def run_task(self, name, app, cmd, schedule):
        while True:
            try:
                cmd_class = load_command_class(app, cmd)
            except ModuleNotFoundError as e:
                return False, e
            call_command(cmd_class, verbosity=0, interactive=False)
            # Create a new entry to database
            task_obj = TaskResult.objects.get_or_create(name=name)
            sleep(schedule.seconds)

    
    def handle(self, *args, **options):
        tasks_results = []
        with ThreadPoolExecutor() as executor:
            for task in getattr(settings, 'EASYCRON_TASKS', []):
                name, app, cmd, schedule = task['name'], task['app'], task['command'], task['schedule']
                latest_run = models.TaskResult.objects.filter(name=cmd).order_by('started_at').last()
                if ( not latest_run ) or ( latest_run.started_at + schedule < timezone.now() ):
                    # run in executor
                    executor.submit(self.run_task(name, app, cmd, schedule))
                    # Get handle function
                    
                    # Run it
                    func_output = io.StringIO()
                    default_stdout = sys.stdout
                    default_stderr = sys.stderr
                    sys.stdout = func_output
                    sys.stderr = func_output
                    try:
                        handle_func()
                    except Exception as err:
                        # Mark task failed
                        result.finished_at = timezone.now()
                        result.success = False
                        result.output = func_output.getvalue() + traceback.format_exc()
                        result.save(update_fields=['finished_at', 'success', 'output'])
                        # Try the next task
                        continue
                    finally:
                        sys.stdout = default_stdout
                        sys.stderr = default_stderr

                    # Mark task finished successfully
                    result.finished_at = timezone.now()
                    result.success = True
                    result.output = func_output.getvalue()
                    result.save(update_fields=['finished_at', 'success', 'output'])
