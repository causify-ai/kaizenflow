FROM 083233266530.dkr.ecr.us-east-2.amazonaws.com/base-python3.7-slim:1.0.0 as base

FROM base as builder

WORKDIR /wheels
COPY devops/requirements.txt ./
RUN pip install -U pip && pip wheel -r ./requirements.txt

FROM base

ENV PYTHONUNBUFFERED=1
COPY --from=builder /wheels /wheels
RUN pip install -U pip && \
    pip install -r /wheels/requirements.txt -f /wheels && \
    rm -rf /wheels && \
    rm -rf /root/.cache/pip/* 

WORKDIR /app
COPY . .
