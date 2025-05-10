FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    python3-pip \
    python3-dev \
    libpq-dev \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y \
    # 追加のビルド依存関係
    pkg-config \
    # Chromeと依存関係
    chromium \
    chromium-driver \
    # 日本語フォント
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -fv

# 必要なPythonパッケージのインストール
COPY requirements.txt .
RUN pip install -r requirements.txt

# 必要なパッケージをインストール
RUN pip install \
    streamlit \
    pandas \
    numpy \
    requests \
    beautifulsoup4 \
    selenium \
    selenium-wire \
    webdriver_manager \
    python-dotenv \
    mysql-connector-python \
    urllib3 \
    blinker \ 
    mitmproxy

# アプリケーションのコピー
COPY . .

# データディレクトリの作成
RUN mkdir -p /app/data

# ポートの公開
EXPOSE 8501

# ヘルスチェック
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# エントリポイントを設定
ENTRYPOINT ["sh", "-c", "streamlit run app.py --server.port ${PORT:-8504} --server.address 0.0.0.0"]
