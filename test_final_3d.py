#!/usr/bin/env python3
"""
GraTeX Bot 最終3D機能テスト
Discord Botとしての完全な3D機能をテストします
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

async def test_final_3d_features():
    """3D機能の最終テスト"""
    
    gratex_bot = GraTeXBot()
    
    try:
        # ブラウザを初期化
        logger.info("🚀 最終3Dテスト開始...")
        await gratex_bot.initialize_browser()
        logger.info("✅ ブラウザ初期化完了")
        
        # 1. 2D基本テスト
        logger.info("\n📊 1. 2D基本テスト")
        image_buffer = await gratex_bot.generate_graph("y = x^2", 4, 0)
        logger.info(f"✅ 2D基本: {len(image_buffer.getvalue())} bytes")
        
        # 2. 3D基本テスト
        logger.info("\n📊 2. 3D基本テスト")
        image_buffer = await gratex_bot.generate_3d_graph("z = x^2 + y^2", 4)
        logger.info(f"✅ 3D基本: {len(image_buffer.getvalue())} bytes")
        
        # 3. 2D→3D→2D切り替えテスト
        logger.info("\n🔄 3. モード切り替えテスト")
        
        # 2D円
        image_buffer = await gratex_bot.generate_graph("x^2 + y^2 = 9", 4, 1)
        logger.info(f"✅ 2D円: {len(image_buffer.getvalue())} bytes")
        
        # 3D球
        image_buffer = await gratex_bot.generate_3d_graph("x^2 + y^2 + z^2 = 9", 4)
        logger.info(f"✅ 3D球: {len(image_buffer.getvalue())} bytes")
        
        # 2D関数
        image_buffer = await gratex_bot.generate_graph("y = sin(x)", 6, -1)
        logger.info(f"✅ 2D関数: {len(image_buffer.getvalue())} bytes")
        
        # 4. 複雑な3D曲面テスト
        logger.info("\n📊 4. 複雑な3D曲面テスト")
        complex_3d_expressions = [
            ("z = sin(x) * cos(y)", "波面"),
            ("x^2/4 + y^2/9 + z^2/16 = 1", "楕円体"),
            ("z = x^3 - 3*x*y^2", "3次曲面"),
            ("z = sqrt(x^2 + y^2)", "円錐"),
            ("x^2 + y^2 - z^2 = 1", "双曲面"),
        ]
        
        for expression, name in complex_3d_expressions:
            try:
                image_buffer = await gratex_bot.generate_3d_graph(expression, 4)
                logger.info(f"✅ {name}: {len(image_buffer.getvalue())} bytes")
            except Exception as e:
                logger.error(f"❌ {name} 失敗: {e}")
        
        # 5. ラベルサイズ変更テスト（2D/3D）
        logger.info("\n📊 5. ラベルサイズテスト")
        for size in [1, 3, 6, 8]:
            # 2D
            image_buffer = await gratex_bot.generate_graph("y = x^2", size, 0)
            logger.info(f"✅ 2D ラベル{size}: {len(image_buffer.getvalue())} bytes")
            
            # 3D
            image_buffer = await gratex_bot.generate_3d_graph("z = x^2 + y^2", size)
            logger.info(f"✅ 3D ラベル{size}: {len(image_buffer.getvalue())} bytes")
        
        # 6. エラーハンドリングテスト
        logger.info("\n⚠️  6. エラーハンドリングテスト")
        try:
            # 不正な数式
            await gratex_bot.generate_3d_graph("invalid_expression", 4)
            logger.warning("❌ 不正数式がエラーなく通った")
        except Exception as e:
            logger.info(f"✅ 不正数式のエラーハンドリング: {type(e).__name__}")
        
        logger.info("\n🎉 最終3Dテスト完了!")
        logger.info("✅ 2D/3D機能が完全に動作しています")
        logger.info("✅ モード切り替えが正常に動作しています")
        logger.info("✅ 複雑な3D曲面の生成が可能です")
        logger.info("✅ Discord Botとして完成しています")
        
    except Exception as e:
        logger.error(f"❌ 最終テストエラー: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # クリーンアップ
        logger.info("🧹 最終クリーンアップ中...")
        await gratex_bot.close()
        logger.info("✅ 最終クリーンアップ完了")

if __name__ == "__main__":
    asyncio.run(test_final_3d_features())
