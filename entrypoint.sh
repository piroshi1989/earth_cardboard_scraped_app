# entrypoint.sh（新規作成）
#!/bin/bash
set -x  # デバッグモードを有効化

echo "Starting Splash server..."
# Splashを起動
splash --listen 0.0.0.0 --port 8050 --verbosity 1 &
SPLASH_PID=$!

# Splashが起動するまで少し待機
echo "Waiting for Splash to start..."
sleep 10

# Splashのプロセスを確認
echo "Checking Splash process..."
ps aux | grep splash

# Splashのポートがリッスンしているか確認
echo "Checking if Splash is listening..."
netstat -tuln | grep 8050

echo "Starting Streamlit server..."
# Streamlitを起動
streamlit run app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true

# Splashプロセスが終了した場合に、このスクリプトも終了する
wait $SPLASH_PID