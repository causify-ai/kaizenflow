FROM sorrentum/sorrentum:latest
WORKDIR /code

RUN pip3 install \
    dask[complete] \
    fastparquet

# Config.
ADD etc_sudoers /install/
COPY etc_sudoers /etc/sudoers
COPY bashrc /var/lib/postgresql/.bashrc

# Set the environment variable for the database connection URL
ENV DATABASE_URL=postgresql://postgres:postgres@db/db

# Expose ports
EXPOSE 5432
EXPOSE 8000
EXPOSE 8077

ADD requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . . 
# COPY ../../help /code
# COPY ../../../help help

COPY download_coingecko.py download_coingecko.py
COPY download_to_csv_cg.py download_to_csv_cg.py
COPY db_coingecko.py db_coingecko.py
COPY dowonload_to_db.py dowonload_to_db.py

ENV PYTHONPATH "${PYTHONPATH}:/code/"
CMD ["python", "-u", "dowonload_to_db.py"]
