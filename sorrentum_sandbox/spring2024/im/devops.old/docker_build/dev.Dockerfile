#
#
#
# TODO(gp): This seems for both PostgreSQL and the app?
FROM python:3.7-slim-buster

RUN apt-get update && \
    apt-get install gcc -y && \
    apt-get install python-dev -y && \
    apt-get install libpq-dev -y && \
    apt-get install postgresql-client -y && \
    apt-get purge gcc -y

# TODO(gp): Replace with poetry.
COPY devops/docker_build/requirements.txt .
# TODO(gp): Use venv.
RUN pip install -r requirements.txt

WORKDIR /app
