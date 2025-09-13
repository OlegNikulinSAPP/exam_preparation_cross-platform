FROM ubuntu:20.04

# Установите переменные окружения для неинтерактивной установки
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Moscow

# Обновите пакеты и установите необходимые зависимости
RUN apt-get update && \
    apt-get install -y \
    python3-pip \
    git \
    zip \
    unzip \
    openjdk-8-jdk \
    autoconf \
    libtool \
    pkg-config \
    zlib1g-dev \
    libncurses5-dev \
    libncursesw5-dev \
    libtinfo5 \
    cmake \
    libffi-dev \
    libssl-dev \
    cython3 \
    && rm -rf /var/lib/apt/lists/*

# Установите Buildozer и дополнительные Python-пакеты
RUN pip3 install --user buildozer cython
ENV PATH="/root/.local/bin:${PATH}"

# Установите рабочую директорию
WORKDIR /app

# Установите стандартную команду для запуска
CMD ["/bin/bash"]