# syntax = docker/dockerfile:experimental

FROM ubuntu:20.04 AS builder
FROM python:3.10-slim-buster
ENV DEBIAN_FRONTEND noninteractive

RUN apt-get -y update
RUN apt-get -y upgrade
RUN apt-get -y install gcc python3-dev

RUN apt install -y --no-install-recommends --fix-missing \
    sudo \
    curl \
    gnupg \
    git \
    vim

ENV INSTALL_DIR=/alpha_vantage
WORKDIR $INSTALL_DIR

COPY requirements.txt .
COPY models models/
COPY api api/
COPY processing processing/
COPY .env .
COPY main.ipynb .

RUN pip3 install -r requirements.txt