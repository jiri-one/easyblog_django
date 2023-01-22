# easyblog_django
New main site for my blog with Django (Python) like a backend, PostgreSQL like a database and some pure JavaScript like a frontend. You can see results on [https://jiri.one](https://jiri.one).

PyTest based Django tests status: [![Django Tests (PyTest)](https://github.com/jiri-one/easyblog_django/actions/workflows/tests.yml/badge.svg)](https://github.com/jiri-one/easyblog_django/actions/workflows/tests.yml)

Tox based tests status (PyTest, MyPy, PyFlakes): [![Tox Tests](https://github.com/jiri-one/easyblog_django/actions/workflows/tox_tests.yml/badge.svg)](https://github.com/jiri-one/easyblog_django/actions/workflows/tox_tests.yml)

Tests coverage: [![Tests Coverage](https://github.com/jiri-one/easyblog_django/.github/coverage.svg)](https://github.com/jiri-one/easyblog_django/)

Main features of blog:
- extensively tested (PyTest and PyTest Django)
- for code are used linters and checkers (MyPy and PyFlakes)
- automatic deploy to server witch GitHub WebHooks (every tag is automaticaly deployed to server)
