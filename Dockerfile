FROM python:3.9-slim

WORKDIR /app

# 必要なパッケージのインストール
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# 必要なPythonパッケージのインストール
COPY requirements.txt .
RUN pip install -r requirements.txt

# Splashサーバーのインストール
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    libpq-dev \
    && pip3 install splash

# アプリケーションのコピー
COPY . .

# データディレクトリの作成
RUN mkdir -p /app/data

# ポートの公開
EXPOSE 8501 8050

# ヘルスチェック
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# 起動スクリプトの作成
RUN echo '#!/bin/bash\n\
splash &\n\
streamlit run app.py --server.port=8501 --server.address=0.0.0.0' > /app/start.sh && \
chmod +x /app/start.sh

# アプリケーションの起動
ENTRYPOINT ["/app/start.sh"] 