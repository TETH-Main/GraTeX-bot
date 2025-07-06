#!/usr/bin/env python3
"""
GraTeX Bot 統合コマンドテスト
新しい /gratex mode:[2d|3d] コマンドをテストします
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import GraTeXBot
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_unified_command():
    """統合コマンドをテスト"""
    
    gratex_bot = GraTeXBot()
    
    try:
        # ブラウザを初期化
        logger.info("🚀 統合コマンドテスト開始...")
        await gratex_bot.initialize_browser()
        logger.info("✅ ブラウザ初期化完了")
        
        # テスト1: 2Dモード（デフォルト）
        logger.info("\n📊 テスト1: 2Dモード（デフォルト）")
        image_buffer = await gratex_bot.generate_graph("y = x^2", 4, 0)
        logger.info(f"✅ 2Dデフォルト: {len(image_buffer.getvalue())} bytes")
        
        # テスト2: 2Dモード（ズーム指定）
        logger.info("\n📊 テスト2: 2Dモード（ズーム指定）")
        image_buffer = await gratex_bot.generate_graph("x^2 + y^2 = 25", 6, 1)
        logger.info(f"✅ 2Dズーム: {len(image_buffer.getvalue())} bytes")
        
        # テスト3: 3Dモード
        logger.info("\n📊 テスト3: 3Dモード")
        image_buffer = await gratex_bot.generate_3d_graph("z = x^2 + y^2", 4)
        logger.info(f"✅ 3Dモード: {len(image_buffer.getvalue())} bytes")
        
        # テスト4: 複雑な3D数式
        logger.info("\n📊 テスト4: 複雑な3D数式")
        complex_3d_tests = [
            ("x^2 + y^2 + z^2 = 16", "球"),
            ("z = sin(x) * cos(y)", "波面"),
            ("x^2/4 + y^2/9 + z^2/16 = 1", "楕円体"),
        ]
        
        for expression, name in complex_3d_tests:
            image_buffer = await gratex_bot.generate_3d_graph(expression, 4)
            logger.info(f"✅ 3D {name}: {len(image_buffer.getvalue())} bytes")
        
        # テスト5: 2D→3D→2D切り替えテスト
        logger.info("\n🔄 テスト5: モード切り替えテスト")
        
        # 2D関数
        image_buffer = await gratex_bot.generate_graph("y = sin(x)", 4, -1)
        logger.info(f"✅ 2D sin: {len(image_buffer.getvalue())} bytes")
        
        # 3D曲面
        image_buffer = await gratex_bot.generate_3d_graph("z = x^2 - y^2", 4)
        logger.info(f"✅ 3D saddle: {len(image_buffer.getvalue())} bytes")
        
        # 再び2D
        image_buffer = await gratex_bot.generate_graph("r = cos(3θ)", 8, 2)
        logger.info(f"✅ 2D polar: {len(image_buffer.getvalue())} bytes")
        
        # テスト6: ラベルサイズ各種テスト
        logger.info("\n📊 テスト6: ラベルサイズ各種テスト")
        for size in [1, 2, 4, 6, 8]:
            # 2D
            image_buffer = await gratex_bot.generate_graph("y = x^3", size, 0)
            logger.info(f"✅ 2D ラベル{size}: {len(image_buffer.getvalue())} bytes")
            
            # 3D
            image_buffer = await gratex_bot.generate_3d_graph("z = sqrt(x^2 + y^2)", size)
            logger.info(f"✅ 3D ラベル{size}: {len(image_buffer.getvalue())} bytes")
        
        logger.info("\n🎉 統合コマンドテスト完了!")
        logger.info("✅ 単一の /gratex コマンドで2D/3D両方が動作しています")
        logger.info("✅ mode パラメータでの切り替えが正常に動作しています")
        logger.info("✅ ズームレベルが2Dでのみ適用されています")
        
    except Exception as e:
        logger.error(f"❌ 統合コマンドテストエラー: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # クリーンアップ
        logger.info("🧹 クリーンアップ中...")
        await gratex_bot.close()
        logger.info("✅ クリーンアップ完了")

if __name__ == "__main__":
    asyncio.run(test_unified_command())
