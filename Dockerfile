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
    qtbase5-dev \
    qt5-qmake \
    libqt5webkit5-dev \
    libqt5webengine5 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# 必要なPythonパッケージのインストール
COPY requirements.txt .
RUN pip install -r requirements.txt

# PyQt5とその依存関係をインストール
RUN pip3 install PyQt5 PyQtWebEngine==5.15.6 PyQt5-Qt5 PyQt5-sip

# splash特有の依存関係を追加
RUN pip3 install splash==3.5.0
RUN pip3 install PyQtWebKit || echo "PyQtWebKit not available, using alternative"

# アプリケーションのコピー
COPY . .

# データディレクトリの作成
RUN mkdir -p /app/data

# Splashを起動するスクリプトを作成
RUN echo '#!/bin/bash\nxvfb-run --server-args="-screen 0 1024x768x24" splash -f luarun --disable-ui -p 8050 -h 0.0.0.0 --max-timeout 300 --slots 10' > /app/start_splash.sh && \
    chmod +x /app/start_splash.sh

# ポートの公開
EXPOSE 8501 8050

# ヘルスチェック
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# 起動コマンド
CMD /app/start_splash.sh & streamlit run app.py --server.port=8501 --server.address=0.0.0.0