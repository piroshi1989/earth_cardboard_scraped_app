FROM python:3.9-slim

WORKDIR /app

# 必要なパッケージのインストール
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    python3-pip \
    python3-dev \
    libpq-dev \
    python3-pyqt5 \
    python3-pyqt5.qtwebkit \
    && rm -rf /var/lib/apt/lists/*

# 必要なPythonパッケージのインストール
COPY requirements.txt .
RUN pip install -r requirements.txt

# Splashサーバーのインストール
RUN pip3 install splash

# アプリケーションのコピー
COPY . .

# データディレクトリの作成
RUN mkdir -p /app/data

# ポートの公開
EXPOSE 8501 8050

# ヘルスチェック
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health 