FROM ubuntu:20.04

# Установите переменные окружения для неинтерактивной установки
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Moscow

# Обновите пакеты и установите необходимые зависимости
RUN apt-get update && \
    apt-get install -y \
    autoconf \
    cmake \
    git \
    libffi-dev \
    libncurses5-dev \
    libncursesw5-dev \
    libssl-dev \
    libtinfo5 \
    libtool \
    openjdk-8-jdk \
    openssl \
    pkg-config \
    python3-pip \
    unzip \
    zip \
    zlib1g-dev && \
    pip3 install --user \
    buildozer==1.2.0 \
    cython==0.29.32 \
    virtualenv && \
    rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:${PATH}"

# Установите рабочую директорию
WORKDIR /app

# Установите стандартную команду для запуска
CMD ["/bin/bash"]