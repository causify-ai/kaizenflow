
FROM apache/airflow:2.5.3
WORKDIR /code
ADD requirements.txt requirements.txt
#RUN pip install -r requirements.txt
#RUN export DOCKER_DEFAULT_PLATFORM=linux/amd64
#COPY app.py app.py
COPY helpers helpers
COPY Anomaly.ipynb Anomaly.ipynb
COPY dask_db.py dask_db.py
COPY ../../../../common common
#COPY ../../../common/__init__.py __init__.py

COPY download_yahoo.py download_yahoo.py
COPY download_to_csv_yahoo.py download_to_csv_yahoo.py
COPY db_yahoo.py db_yahoo.py
COPY download_db_yahoo.py download_db_yahoo.py

COPY Latest_Data.py Latest_Data.py
COPY api.py api.py
ENV PYTHONPATH "${PYTHONPATH}:/code/"

RUN pip install --user --upgrade pip
RUN pip install --no-cache-dir --user -r requirements.txt

