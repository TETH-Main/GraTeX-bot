#!/usr/bin/env python3
"""
GraTeX Bot 3D機能のテストスクリプト
Desmos 3D機能の画像取得をテストします
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

async def test_3d_functionality():
    """3D機能をテスト"""
    
    gratex_bot = GraTeXBot()
    
    try:
        # ブラウザを初期化
        logger.info("🚀 ブラウザを初期化中...")
        await gratex_bot.initialize_browser()
        logger.info("✅ ブラウザ初期化完了")
        
        # 3D切り替えボタンを探す
        logger.info("\n🔍 3D切り替えボタンを探しています...")
        
        # version-3dのlabelを探す
        three_d_label = await gratex_bot.page.query_selector('label[for="version-3d"]')
        if three_d_label:
            logger.info("✅ 3D切り替えボタンを発見しました")
            
            # 3D切り替えボタンをクリック
            logger.info("🔄 3Dモードに切り替え中...")
            await three_d_label.click()
            
            # 切り替え完了を待機
            await asyncio.sleep(3)
            
            # 3Dモードが有効になったか確認
            logger.info("🧪 3Dモードの有効性を確認中...")
            
            # GraTeX.calculator3Dが利用可能か確認
            calculator_3d_available = await gratex_bot.page.evaluate('''
                () => {
                    return !!(window.GraTeX && window.GraTeX.calculator3D);
                }
            ''')
            
            if calculator_3d_available:
                logger.info("✅ GraTeX.calculator3D が利用可能です")
                
                # 3D数式をテスト
                logger.info("\n📊 3D数式をテスト中...")
                test_expressions = [
                    "z = x^2 + y^2",          # パラボロイド
                    "x^2 + y^2 + z^2 = 25",   # 球
                    "z = sin(x) * cos(y)",    # 波面
                ]
                
                for i, expression in enumerate(test_expressions, 1):
                    try:
                        logger.info(f"テスト{i}: {expression}")
                        
                        # 3D数式を設定
                        await gratex_bot.page.evaluate(f'''
                            () => {{
                                if (window.GraTeX && window.GraTeX.calculator3D) {{
                                    window.GraTeX.calculator3D.setBlank();
                                    window.GraTeX.calculator3D.setExpression({{latex: `{expression}`}});
                                    console.log("3D数式を設定しました:", `{expression}`);
                                    return true;
                                }} else {{
                                    console.error("GraTeX.calculator3D が利用できません");
                                    return false;
                                }}
                            }}
                        ''')
                        
                        # 少し待機
                        await asyncio.sleep(2)
                        
                        # スクリーンショットボタンをクリック
                        await gratex_bot.page.click('#screenshot-button')
                        
                        # 画像生成完了を待機
                        await gratex_bot.page.wait_for_function(
                            """
                            () => {
                                const previewImg = document.getElementById('preview');
                                return previewImg && previewImg.src && previewImg.src.length > 100;
                            }
                            """,
                            timeout=20000
                        )
                        
                        # 画像データを取得
                        image_data = await gratex_bot.page.evaluate('''
                            () => {
                                const previewImg = document.getElementById('preview');
                                if (previewImg && previewImg.src && previewImg.src.startsWith('data:')) {
                                    return previewImg.src;
                                }
                                return null;
                            }
                        ''')
                        
                        if image_data:
                            import base64
                            image_bytes = base64.b64decode(image_data.split(',')[1])
                            logger.info(f"✅ 3D画像生成成功: {len(image_bytes)} bytes")
                        else:
                            logger.warning(f"❌ 3D画像生成失敗: {expression}")
                            
                    except Exception as e:
                        logger.error(f"❌ 3D数式テストエラー ({expression}): {e}")
                
            else:
                logger.error("❌ GraTeX.calculator3D が利用できません")
                
        else:
            logger.error("❌ 3D切り替えボタンが見つかりません")
            
            # デバッグ用：利用可能なversion関連要素を探す
            logger.info("🔍 利用可能なversion関連要素を探しています...")
            version_elements = await gratex_bot.page.evaluate('''
                () => {
                    const elements = [];
                    
                    // version関連のすべての要素を探す
                    const versionElements = document.querySelectorAll('[class*="version"], [id*="version"], [for*="version"]');
                    versionElements.forEach(el => {
                        elements.push({
                            tag: el.tagName,
                            id: el.id,
                            className: el.className,
                            for: el.getAttribute('for'),
                            text: el.textContent?.trim()
                        });
                    });
                    
                    return elements;
                }
            ''')
            
            logger.info(f"発見された要素: {version_elements}")
        
        logger.info("\n🎉 3Dテスト完了!")
        
    except Exception as e:
        logger.error(f"❌ 3Dテストエラー: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # クリーンアップ
        logger.info("🧹 クリーンアップ中...")
        await gratex_bot.close()
        logger.info("✅ クリーンアップ完了")

if __name__ == "__main__":
    asyncio.run(test_3d_functionality())
