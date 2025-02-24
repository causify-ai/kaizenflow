#FROM ubuntu:20.04
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND noninteractive

RUN apt-get -y update
RUN apt-get -y upgrade

# Install system utilities.
RUN apt install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    gnupg \
    make \
    sudo \
    systemctl \
    vim \
    xz-utils

# Install Python.
RUN apt-get update && apt install -y --no-install-recommends \
    python3 \
    python3-dev \
    python3-pip \
    jupyter-notebook \
    virtualenv \
    vim

# Install node.js
#RUN curl -sL https://deb.nodesource.com/setup_10.x | sudo -E bash - && \
#  sudo apt-get install -y nodejs
RUN curl -LO https://nodejs.org/dist/v18.0.0/node-v18.0.0-linux-x64.tar.xz && \
    tar -xf node-v18.0.0-linux-x64.tar.xz && \
    bash -c "cp -r node-v18.0.0-linux-x64/{bin,include,lib,share} /usr/"

# Install Truffle.
RUN npm install -g truffle

# Install Ganache.
RUN npm install -g ganache

# Install Ganache GUI.
#RUN apt-get install -y wget libgtk-3-dev libgtkextra-dev libgconf2-dev libnss3 libasound2 libxtst-dev libxss1 libx11-6 libx11-xcb-dev
## From https://github.com/trufflesuite/ganache-ui/releases
#RUN wget https://github.com/trufflesuite/ganache-ui/releases/download/v2.5.4/ganache-2.5.4-linux-x86_64.AppImage
#RUN chmod +x ganache-2.5.4-linux-x86_64.AppImage
#RUN ./ganache-2.5.4-linux-x86_64.AppImage --appimage-extract
#RUN rm ganache-2.5.4-linux-x86_64.AppImage
#ENV DISPLAY=:0
#EXPOSE 7545
##ENTRYPOINT ["./squashfs-root/AppRun"]
#
## Install VNC.
##RUN apt-get install -y git x11vnc
#RUN apt install tightvncserver
#EXPOSE 5920

# Install openzeppelin.
#RUN npm install -g openzeppelin-solidity
RUN npm install -g @openzeppelin/contracts

# Install Geth.
RUN apt install -y software-properties-common && \
    add-apt-repository -y ppa:ethereum/ethereum && \
    apt-get update && \
    apt-get install -y ethereum && \
    geth version

# Install solc.
RUN add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y solc

# Install Python packages.
RUN pip3 install \
    jupyter \
    pandas \
    matplotlib \
    yapf \
    ipython \
    jupyter-contrib-core \
    jupyter-contrib-nbextensions

RUN mkdir /install
ADD install_jupyter_extensions.sh /install
RUN /install/install_jupyter_extensions.sh

# Install crypto packages.
RUN pip3 install \
    eth-brownie \
    eth_tester \
    etherscan-python \
    py-solc-x \
    uniswap-python \
    web3

#RUN brownie pm install OpenZeppelin/openzeppelin-contracts@3.0.0
RUN brownie pm install OpenZeppelin/openzeppelin-contracts@4.8.0

# Config.
ADD etc_sudoers /install/
COPY etc_sudoers /etc/sudoers
ADD create_users.sh /install/
RUN /bin/bash -c "/install/create_users.sh"
COPY bashrc /root/.bashrc

# Dapp.
EXPOSE 3000
# Ganache.
EXPOSE 7545
EXPOSE 8545
# Jupyter.
EXPOSE 8888
