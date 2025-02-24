FROM python:3.9

WORKDIR /root

RUN mkdir "data" "logs" "devops"

COPY files/data.json /root/data/data.json
COPY src /root/src
COPY utilities /root/utilities
COPY common /root/common
COPY devops/requirements.txt /root/devops/requirements.txt
COPY devops/.env /root/devops/.env

RUN pip install -r /root/devops/requirements.txt

ENV PYTHONPATH /root
ENV DOTENV_FILE /root/devops/.env
ENV DATA_FILE /root/data/data.json

# CMD ["python", "src/download_to_csv.py", "--target_dir", "/var/lib/app/data/", "--use_api", "False"]
# CMD ["python", "src/download_to_csv.py", "--target_dir", "/var/lib/app/data/", "--use_api", "True"]
CMD ["python", "src/download_to_csv.py",
        "--start_timestamp", "2021-09-21",
        "--end_timestamp", "2021-10-21",
        "--target_dir", "/var/lib/app/data/",
        "--use_api", "True"]

# CMD ["python", "src/download_to_db.py", "--target_table", "google_trends_data", "--use_api", "False"]
# CMD ["python", "src/download_to_db.py", "--target_table", "google_trends_data", "--use_api", "True"]
CMD ["python", "src/download_to_db.py",
    "--start_timestamp", "2021-09-21",
    "--end_timestamp", "2021-10-21",
    "--target_table", "google_trends_data",
     "--use_api", "True"]

# CMD ["python", "src/load_and_validate.py"]
# CMD ["python", "src/load_validate_transform.py"]

