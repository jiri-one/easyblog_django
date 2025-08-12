FROM python:alpine
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /code/src
COPY ./src /code/src
COPY ./pyproject.toml /code
COPY ./LICENSE.txt /code
WORKDIR /code
RUN pip install .
RUN pip uninstall -y easyblog-django
WORKDIR /code/src
RUN python utils/new_secret_key.py
RUN python manage.py collectstatic --noinput
RUN python manage.py migrate --noinput
