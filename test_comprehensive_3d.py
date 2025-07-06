#!/usr/bin/env python3
"""
GraTeX Bot 3D機能の包括的テストスクリプト
2D/3D切り替えとスラッシュコマンド機能をテストします
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

async def test_comprehensive_3d_features():
    """3D機能と2D/3D切り替えを包括的にテスト"""
    
    gratex_bot = GraTeXBot()
    
    try:
        # ブラウザを初期化
        logger.info("🚀 ブラウザを初期化中...")
        await gratex_bot.initialize_browser()
        logger.info("✅ ブラウザ初期化完了")
        
        # テスト1: 2Dグラフ生成
        logger.info("\n📊 テスト1: 2Dグラフ生成")
        latex_2d = "x^2 + y^2 = 25"
        image_buffer = await gratex_bot.generate_graph(latex_2d, label_size=4, zoom_level=0)
        logger.info(f"✅ 2Dグラフ生成成功: {len(image_buffer.getvalue())} bytes")
        
        # テスト2: 3Dグラフ生成
        logger.info("\n📊 テスト2: 3Dグラフ生成")
        latex_3d = "z = x^2 + y^2"
        image_buffer = await gratex_bot.generate_3d_graph(latex_3d, label_size=4)
        logger.info(f"✅ 3Dグラフ生成成功: {len(image_buffer.getvalue())} bytes")
        
        # テスト3: 2D→3D→2D切り替え
        logger.info("\n🔄 テスト3: モード切り替えテスト")
        
        # 2Dモードに切り替え
        result_2d = await gratex_bot.switch_to_2d_mode()
        logger.info(f"2Dモード切り替え: {result_2d}")
        
        # 2Dでグラフ生成
        image_buffer = await gratex_bot.generate_graph("y = sin(x)", label_size=6)
        logger.info(f"✅ 2Dモード後のグラフ生成: {len(image_buffer.getvalue())} bytes")
        
        # 3Dグラフ生成（自動的に3Dモードに切り替わる）
        image_buffer = await gratex_bot.generate_3d_graph("z = sin(x) * cos(y)", label_size=6)
        logger.info(f"✅ 3Dモード切り替え後のグラフ生成: {len(image_buffer.getvalue())} bytes")
        
        # 再び2Dモードに戻る
        result_2d = await gratex_bot.switch_to_2d_mode()
        logger.info(f"2Dモード復帰: {result_2d}")
        
        # テスト4: 様々な3D数式
        logger.info("\n📊 テスト4: 様々な3D数式")
        test_3d_expressions = [
            ("z = x^2 + y^2", "パラボロイド"),
            ("x^2 + y^2 + z^2 = 16", "球"),
            ("z = sin(sqrt(x^2 + y^2))", "波紋"),
            ("x^2/4 + y^2/9 + z^2/16 = 1", "楕円体"),
            ("z = x^3 - 3*x*y^2", "3次曲面"),
        ]
        
        for expression, description in test_3d_expressions:
            try:
                logger.info(f"3Dテスト: {description} - {expression}")
                image_buffer = await gratex_bot.generate_3d_graph(expression, label_size=4)
                logger.info(f"✅ {description} 生成成功: {len(image_buffer.getvalue())} bytes")
            except Exception as e:
                logger.error(f"❌ {description} 生成失敗: {e}")
        
        # テスト5: ラベルサイズテスト（3D）
        logger.info("\n📊 テスト5: 3Dラベルサイズテスト")
        for label_size in [1, 2, 4, 6, 8]:
            try:
                image_buffer = await gratex_bot.generate_3d_graph("z = x^2 - y^2", label_size=label_size)
                logger.info(f"✅ 3Dラベルサイズ{label_size}: {len(image_buffer.getvalue())} bytes")
            except Exception as e:
                logger.error(f"❌ 3Dラベルサイズ{label_size}失敗: {e}")
        
        logger.info("\n🎉 全ての包括的テスト完了!")
        
    except Exception as e:
        logger.error(f"❌ 包括的テストエラー: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # クリーンアップ
        logger.info("🧹 クリーンアップ中...")
        await gratex_bot.close()
        logger.info("✅ クリーンアップ完了")

if __name__ == "__main__":
    asyncio.run(test_comprehensive_3d_features())
