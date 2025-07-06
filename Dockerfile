# Railway.app用設定ファイル
# https://docs.railway.app/reference/dockerfile

FROM python:3.11-slim

# システムパッケージの更新とPlaywright用依存関係をインストール
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリを設定
WORKDIR /app

# 依存関係ファイルをコピー
COPY requirements.txt .

# Python依存関係をインストール
RUN pip install --no-cache-dir -r requirements.txt

# Playwrightブラウザをインストール
RUN playwright install chromium
RUN playwright install-deps chromium

# アプリケーションファイルをコピー
COPY . .

# ポート設定
EXPOSE $PORT

# アプリケーション起動
CMD ["python", "main.py"]
