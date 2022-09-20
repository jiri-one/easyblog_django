from django.core.management.base import BaseCommand, CommandError
from subprocess import run, CalledProcessError
from os import getcwd, chdir
from datetime import datetime


class Command(BaseCommand):
    help = 'Redeploy whole blog from GitHub code'
    
    def add_arguments(self, parser):
        parser.add_argument('commit', type=str, nargs=1)

    def handle(self, *args, **options):
        commit = options['commit'][0]
        if getcwd() != '/srv/http/virtual/jiri.one':
            chdir('/srv/http/virtual/jiri.one')
        try: 
            run(f"git fetch R {commit}", shell=True, check=True)
            run(f"git reset --hard {commit}", shell=True, check=True)
            run("poetry install --no-root --with production", shell=True, check=True)
            run("poetry run python manage.py collectstatic --no-input", shell=True, check=True)
            run("systemctl --user restart gunicorn_jiri_one.socket", shell=True, check=True)
        except CalledProcessError as e:
            with open("logs/deploy_error.txt", "w+") as file:
                file.write(f"""
                    Log datetime: {datetime.now().isoformat()}
                    Command that was used to spawn the child process: {e.cmd}
                    Output of the child process {e.stdout}
                    Stderr out {e.stderr}
                    """)
            self.stdout.write(self.style.ERROR("Something went wrong in subprocess call! check logs/deploy_error.txt"))
            raise CommandError(e)
