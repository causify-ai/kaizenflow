FROM apache/airflow:2.2.2

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

# Update pip.
RUN /usr/local/bin/python -m pip install --upgrade pip

# google_trends specific modules
RUN pip3 install google_search_results pandas psycopg2_binary python-dotenv dask matplotlib pmdarima statsmodels


RUN pip3 install \
    apache-airflow-providers-http==2.0.1 \
    apache-airflow-providers-postgres==2.2.0
