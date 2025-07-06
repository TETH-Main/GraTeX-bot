#!/usr/bin/env python3
"""
GraTeX Bot スラッシュコマンドのテストスクリプト
スラッシュコマンドの機能をシミュレーションしてテストします
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

async def test_slash_command_features():
    """スラッシュコマンドの機能をテスト"""
    
    gratex_bot = GraTeXBot()
    
    try:
        # ブラウザを初期化
        logger.info("🚀 ブラウザを初期化中...")
        await gratex_bot.initialize_browser()
        logger.info("✅ ブラウザ初期化完了")
        
        # テスト1: 基本的なグラフ生成（デフォルトパラメータ）
        logger.info("\n📊 テスト1: 基本グラフ生成 (デフォルト)")
        latex_expression = "x^2 + y^2 = 25"
        image_buffer = await gratex_bot.generate_graph(latex_expression)
        logger.info(f"✅ グラフ生成成功: {len(image_buffer.getvalue())} bytes")
        
        # テスト2: ラベルサイズ変更
        logger.info("\n📊 テスト2: ラベルサイズ変更 (6)")
        image_buffer = await gratex_bot.generate_graph(latex_expression, label_size=6)
        logger.info(f"✅ ラベルサイズ6のグラフ生成成功: {len(image_buffer.getvalue())} bytes")
        
        # テスト3: ズームレベル指定（拡大）
        logger.info("\n📊 テスト3: ズームレベル+2 (拡大)")
        image_buffer = await gratex_bot.generate_graph(latex_expression, zoom_level=2)
        logger.info(f"✅ ズーム+2のグラフ生成成功: {len(image_buffer.getvalue())} bytes")
        logger.info(f"現在のズームレベル: {gratex_bot.current_zoom_level}")
        
        # テスト4: ズームレベル指定（縮小）
        logger.info("\n📊 テスト4: ズームレベル-1 (縮小)")
        image_buffer = await gratex_bot.generate_graph(latex_expression, zoom_level=-1)
        logger.info(f"✅ ズーム-1のグラフ生成成功: {len(image_buffer.getvalue())} bytes")
        logger.info(f"現在のズームレベル: {gratex_bot.current_zoom_level}")
        
        # テスト5: 複雑な数式
        logger.info("\n📊 テスト5: 複雑な数式")
        complex_latex = "\\sin(x) + \\cos(y) = 0"
        image_buffer = await gratex_bot.generate_graph(complex_latex, label_size=8, zoom_level=1)
        logger.info(f"✅ 複雑な数式のグラフ生成成功: {len(image_buffer.getvalue())} bytes")
        
        # テスト6: ズーム操作のテスト
        logger.info("\n🔍 テスト6: ズーム操作")
        
        # 拡大テスト
        logger.info("拡大操作...")
        zoom_result = await gratex_bot.zoom_desmos_graph('in')
        logger.info(f"拡大結果: {zoom_result}, 現在のズームレベル: {gratex_bot.current_zoom_level}")
        
        # 縮小テスト
        logger.info("縮小操作...")
        zoom_result = await gratex_bot.zoom_desmos_graph('out')
        logger.info(f"縮小結果: {zoom_result}, 現在のズームレベル: {gratex_bot.current_zoom_level}")
        
        # ズームレベル制限テスト
        logger.info("\n⚠️  テスト7: ズームレベル制限")
        gratex_bot.current_zoom_level = 3  # 最大値に設定
        zoom_result = await gratex_bot.zoom_desmos_graph('in')  # さらに拡大を試行
        logger.info(f"最大ズーム時の拡大試行結果: {zoom_result}, ズームレベル: {gratex_bot.current_zoom_level}")
        
        gratex_bot.current_zoom_level = -3  # 最小値に設定
        zoom_result = await gratex_bot.zoom_desmos_graph('out')  # さらに縮小を試行
        logger.info(f"最小ズーム時の縮小試行結果: {zoom_result}, ズームレベル: {gratex_bot.current_zoom_level}")
        
        # テスト8: apply_zoom_level の直接テスト
        logger.info("\n🎯 テスト8: apply_zoom_level直接テスト")
        for zoom_level in [-3, -1, 0, 1, 3]:
            result = await gratex_bot.apply_zoom_level(zoom_level)
            logger.info(f"ズームレベル {zoom_level}: {result}")
        
        logger.info("\n🎉 全てのテスト完了!")
        
    except Exception as e:
        logger.error(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # クリーンアップ
        logger.info("🧹 クリーンアップ中...")
        await gratex_bot.close()
        logger.info("✅ クリーンアップ完了")

if __name__ == "__main__":
    asyncio.run(test_slash_command_features())
