FROM apache/airflow:2.8.0-python3.9

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

# Add (optional) Python libraries.
#https://airflow.apache.org/docs/apache-airflow/stable/extra-packages-ref.html?highlight=snowflake

USER airflow

# Update pip.
RUN /usr/local/bin/python -m pip install --upgrade pip
RUN /usr/local/bin/python -m pip install prophet

# Install Python packages.
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
    dask \
    prophet \
    distributed \
    dask_xgboost \
    xgboost \
    dask_ml \
    dask_xgboost \
    yapf

# Part of the original DockerFile.
RUN pip3 install \
    python-dotenv \
    apache-airflow-providers-http \
    apache-airflow-providers-postgres
