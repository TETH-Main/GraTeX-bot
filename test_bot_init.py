#!/usr/bin/env python3
"""
Discord Bot初期化テスト
"""

import asyncio
import logging
from main import bot, gratex_bot

# ログレベルを設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_bot_initialization():
    """Bot初期化のテスト"""
    print("=== Bot初期化テスト ===")
    
    try:
        # ブラウザ状態確認機能のテスト
        print("1. ブラウザ状態確認機能をテスト...")
        await gratex_bot.ensure_browser_ready()
        print("✓ ブラウザ状態確認成功")
        
        # ブラウザクリーンアップ機能のテスト
        print("2. ブラウザクリーンアップ機能をテスト...")
        await gratex_bot.cleanup_browser()
        print("✓ ブラウザクリーンアップ成功")
        
        # 再初期化テスト
        print("3. ブラウザ再初期化をテスト...")
        await gratex_bot.ensure_browser_ready()
        print("✓ ブラウザ再初期化成功")
        
        # 最終クリーンアップ
        await gratex_bot.cleanup_browser()
        print("✓ 最終クリーンアップ完了")
        
        print("\n=== すべてのテストが成功しました ===")
        
    except Exception as e:
        print(f"✗ テスト失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_bot_initialization())
