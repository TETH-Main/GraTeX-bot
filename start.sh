#!/bin/bash
# Railway startup script

echo "Starting GraTeX Bot..."
echo "Python version: $(python --version)"
echo "Chrome location: $(which chromium || which google-chrome || echo 'Chrome not found')"
echo "ChromeDriver location: $(which chromedriver || echo 'ChromeDriver not found')"

# 環境変数を表示 (デバッグ用)
echo "GOOGLE_CHROME_BIN: $GOOGLE_CHROME_BIN"
echo "CHROMEDRIVER_PATH: $CHROMEDRIVER_PATH"

# Botを起動
exec python main.py
