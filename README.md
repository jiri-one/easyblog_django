# easyblog_django
New main site for my blog with Django (Python) like a backend, PostgreSQL like a database and some pure JavaScript like a frontend. You can see results on [https://jiri.one](https://jiri.one).

PyTest based Django tests status: [![Django Tests (PyTest)](https://github.com/jiri-one/easyblog_django/actions/workflows/tests.yml/badge.svg)](https://github.com/jiri-one/easyblog_django/actions/workflows/tests.yml)

Tox based tests status (PyTest, PyRight, Ruff): [![Tox Tests](https://github.com/jiri-one/easyblog_django/actions/workflows/tox_tests.yml/badge.svg)](https://github.com/jiri-one/easyblog_django/actions/workflows/tox_tests.yml)

Main features of blog:
- extensively tested (PyTest and PyTest Django)
- for code are used linters and checkers (MyPy and PyFlakes)
- automatic deploy to server witch GitHub WebHooks (every tag is automatically deployed to server)

## How to run it
I use this blog in Podman containers, so you can run it with Podman or Docker too:
You can run whole blog with one command:
`podman-compose --podman-run-args='--replace' -f compose.yaml up -d`
Or you can run only database itself:
`podman-compose --podman-run-args='--replace' -f compose.yaml up db -d`

- copy the sql data to container
  
`podman cp easyblog_django_25-06-22.sql easyblog_django_db_1:/init.sql`

- inport sql data to PostgreSQL
  
`podman exec -it easyblog_django_db_1 psql -U jiri -d easyblog_django -f /init.sql`
