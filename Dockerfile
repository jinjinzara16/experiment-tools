FROM ubuntu:20.04

RUN sed -i 's/kr.archive.ubuntu.com/mirror.kakao.com/g' /etc/apt/sources.list

ENV DEBIAN_FRONTEND="noninteractive"

RUN apt-get update && \
    apt-get install -y \
    build-essential \
    wget \
    git \
    sudo vim \
    pkg-config \
    libtool libtool-bin \
    automake autoconf \
    python3 python3-dev python3-pip \
    bison flex \
    zlib1g-dev \
    clang \
    llvm \
    llvm-dev && \
    rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir torch numpy

RUN mkdir -p /setup /fuzzer /script /output

COPY AFL /fuzzer/AFL
COPY AFL-PPO /fuzzer/AFL-PPO
COPY setup/  /setup
COPY script/ /script

RUN /setup/install_fuzzer.sh

RUN /setup/build_afl_binutils.sh

RUN /setup/build_ppo_binutils.sh

RUN chmod 777 /output

WORKDIR /

ARG GID
ARG UID
RUN groupadd -o -g $GID user
RUN useradd -m -s /bin/bash -o -u $UID -g $GID user
RUN echo "user ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
USER user
