#!/bin/bash
set -x  # デバッグモードを有効化

echo "Starting Splash server on 0.0.0.0:8050..."
# Splashを0.0.0.0:8050で起動
splash --listen 0.0.0.0 --port 8050 --max-timeout 3600 --verbosity 1 