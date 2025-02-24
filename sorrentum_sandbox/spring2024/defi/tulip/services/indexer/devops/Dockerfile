FROM python:3.7-slim
RUN mkdir /app
ADD ./events_indexer.py /app
ADD ./TulipABI.json /app
WORKDIR /app
ENV PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y gcc python3-dev libpq-dev
RUN pip install web3==5.31.3
RUN pip install psycopg2
CMD ["python", "events_indexer.py"]