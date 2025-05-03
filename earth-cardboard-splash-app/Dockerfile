FROM scrapinghub/splash:3.5

# 必要なディレクトリを作成
RUN mkdir -p /etc/splash/filters && \
    touch /etc/splash/filters/.keep

# ポートを公開
EXPOSE 8050

# アプリケーションを起動
CMD ["python3", "-m", "splash.server", "--port", "8050", "--disable-browser-caches", "--disable-private-mode", "--filters-path", "/etc/splash/filters"] 