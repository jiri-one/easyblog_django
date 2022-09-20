from django.core.management.base import BaseCommand, CommandError
from subprocess import check_call, CalledProcessError
from os import getcwd, chdir


class Command(BaseCommand):
    help = 'Redeploy whole blog from GitHub code'

    def handle(self, *args, **options):
        if getcwd() != '/srv/http/virtual/jiri.one':
            chdir('/srv/http/virtual/jiri.one')
        try: 
            check_call(["git", "fetch"])
            check_call(["git", "reset", "--hard", "R/main"])
            check_call(["poetry", "run", "python", "manage.py", "collectstatic", "--no-input"])
            check_call(["systemctl", "--user", "restart", "gunicorn_jiri_one.socket"])
        except CalledProcessError as e:
            self.stdout.write(self.style.ERROR("Something went wrong in subprocess call!"))
            raise CommandError(e)
