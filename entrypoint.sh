# entrypoint.sh（新規作成）
#!/bin/bash
set -x  # デバッグモードを有効化

echo "Starting Splash server..."
# Splashを起動
/app/start_splash.sh &
SPLASH_PID=$!

# Splashが起動するまで少し待機
echo "Waiting for Splash to start..."
sleep 10

# Splashのプロセスを確認
ps aux | grep splash

echo "Starting Streamlit server..."
# Streamlitを起動
streamlit run app.py --server.port=8501 --server.address=0.0.0.0

# Splashプロセスが終了した場合に、このスクリプトも終了する
wait $SPLASH_PID