from bottle import route, run, Bottle
import threading
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bottleアプリケーション
app = Bottle()

@app.route('/')
def home():
    """ヘルスチェック用エンドポイント"""
    return {
        "status": "alive",
        "service": "GraTeX Discord Bot",
        "message": "Bot is running successfully!"
    }

@app.route('/health')
def health():
    """詳細なヘルスチェック"""
    return {
        "status": "healthy",
        "service": "GraTeX Bot Keep-Alive Server",
        "version": "1.0.0"
    }

def run_server():
    """サーバーを実行"""
    try:
        # Railway環境では PORT 環境変数を使用
        import os
        port = int(os.environ.get('PORT', 8080))
        
        logger.info(f"Keep-alive サーバーをポート {port} で起動中...")
        app.run(host='0.0.0.0', port=port, debug=False, quiet=True)
        
    except Exception as e:
        logger.error(f"サーバー起動エラー: {e}")

def keep_alive():
    """バックグラウンドでサーバーを起動"""
    try:
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        logger.info("Keep-alive サーバーがバックグラウンドで起動しました")
        
    except Exception as e:
        logger.error(f"Keep-alive サーバーの起動に失敗: {e}")

if __name__ == "__main__":
    # 直接実行された場合はサーバーのみを起動
    run_server()
