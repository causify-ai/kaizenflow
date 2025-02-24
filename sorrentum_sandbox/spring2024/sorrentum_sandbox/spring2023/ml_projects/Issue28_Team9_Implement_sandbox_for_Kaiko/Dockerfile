FROM apache/airflow:2.5.3

USER root

RUN apt-get update -yqq && \
    apt-get install -y \
      jupyter-notebook \
      libpq-dev \
      postgresql \
      postgresql-contrib \
      python3-dev \
      python3-pip \
      vim

USER airflow
RUN /usr/local/bin/python -m pip install --upgrade pip

RUN pip3 install \
    ipython \
    ipython-sql \
    jupyter \
    jupyter-contrib-core \
    jupyter-contrib-nbextensions \
    praw \
    psycopg2 \
    pymongo \
    s3fs \
    seaborn \
    tqdm \
    yapf \
    kaiko

RUN pip3 install \
    python-dotenv \
    apache-airflow-providers-http==2.0.1 \
    apache-airflow-providers-postgres==2.2.0
    

COPY . /opt/airflow/
