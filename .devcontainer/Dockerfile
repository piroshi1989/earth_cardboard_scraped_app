FROM mcr.microsoft.com/devcontainers/python:3.9

# 必要なパッケージをインストール
RUN apt-get update && apt-get install -y \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Pythonパッケージをインストール
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# 作業ディレクトリを設定
WORKDIR /workspace

# ユーザーを設定
USER vscode

# 開発ツールのインストール
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install streamlit --upgrade

# 開発用の設定
ENV PYTHONPATH=/workspace
ENV PYTHONUNBUFFERED=1 