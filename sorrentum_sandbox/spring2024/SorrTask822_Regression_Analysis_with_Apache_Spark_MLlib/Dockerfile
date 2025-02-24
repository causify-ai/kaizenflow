FROM python:3.11.8-slim as python_build

WORKDIR /app

COPY MLlib.py /app
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update
RUN apt-get install -y default-jdk

EXPOSE 8888

CMD ["python", "MLlib.py"]
