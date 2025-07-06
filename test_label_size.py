"""
リアクション機能を含む修正されたGraTeX Botのテストスクリプト
"""

import asyncio
import base64
import logging
from playwright.async_api import async_playwright

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_label_size_changes():
    """ラベルサイズ変更のテスト"""
    
    expression = "x^2 + y^2 = 1"
    label_sizes = [1, 2, 3, 4, 6, 8]
    
    playwright = await async_playwright().start()
    
    try:
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding'
            ]
        )
        
        page = await browser.new_page()
        page.set_default_timeout(30000)
        
        for size in label_sizes:
            logger.info(f"\n=== ラベルサイズ {size} でテスト ===")
            
            try:
                # GraTeXページにアクセス
                await page.goto('https://teth-main.github.io/GraTeX/?wide=true&credit=true', 
                               wait_until='networkidle', timeout=30000)
                
                # GraTeX.calculator2Dが利用可能になるまで待機
                await page.wait_for_function(
                    "() => window.GraTeX && window.GraTeX.calculator2D",
                    timeout=15000
                )
                
                # ラベルサイズを設定
                try:
                    # name="labelSize"のselectを探す
                    label_select = await page.wait_for_selector('select[name="labelSize"]', timeout=5000)
                    await label_select.select_option(str(size))
                    logger.info(f"ラベルサイズを{size}に設定")
                except Exception as e:
                    logger.warning(f"name=\"labelSize\"での設定失敗、フォールバック: {e}")
                    # フォールバック
                    try:
                        label_selects = await page.query_selector_all('select.form-control')
                        if len(label_selects) >= 2:
                            await label_selects[1].select_option(str(size))
                            logger.info(f"フォールバックでラベルサイズを{size}に設定")
                    except Exception as e2:
                        logger.warning(f"フォールバックも失敗: {e2}")
                
                # LaTeX式を設定
                await page.evaluate(f"""
                    () => {{
                        if (window.GraTeX && window.GraTeX.calculator2D) {{
                            window.GraTeX.calculator2D.setBlank();
                            window.GraTeX.calculator2D.setExpression({{latex: `{expression}`}});
                            console.log("数式を設定しました:", `{expression}`);
                        }}
                    }}
                """)
                
                await asyncio.sleep(3)
                
                # Generateボタンをクリック
                await page.click('#screenshot-button')
                
                # 画像生成を待機
                await page.wait_for_function(
                    """
                    () => {
                        const previewImg = document.getElementById('preview');
                        return previewImg && previewImg.src && previewImg.src.length > 100;
                    }
                    """,
                    timeout=20000
                )
                
                # 画像データを取得
                image_data = await page.evaluate('''
                    () => {
                        const previewImg = document.getElementById('preview');
                        if (previewImg && previewImg.src) {
                            if (previewImg.src.startsWith('data:')) {
                                return previewImg.src;
                            }
                            
                            const canvas = document.createElement('canvas');
                            const ctx = canvas.getContext('2d');
                            
                            canvas.width = previewImg.naturalWidth || previewImg.width;
                            canvas.height = previewImg.naturalHeight || previewImg.height;
                            
                            ctx.drawImage(previewImg, 0, 0);
                            return canvas.toDataURL('image/png');
                        }
                        
                        return null;
                    }
                ''')
                
                if image_data:
                    logger.info(f"✅ ラベルサイズ {size} の画像生成成功!")
                    
                    # 画像を保存
                    image_bytes = base64.b64decode(image_data.split(',')[1])
                    filename = f"test_label_size_{size}.png"
                    
                    with open(filename, 'wb') as f:
                        f.write(image_bytes)
                    logger.info(f"画像を {filename} として保存しました")
                else:
                    logger.error(f"❌ ラベルサイズ {size} の画像生成失敗")
                
            except Exception as e:
                logger.error(f"ラベルサイズ {size} でエラー: {e}")
                
        await browser.close()
        
    except Exception as e:
        logger.error(f"全体的なエラー: {e}")
        
    finally:
        await playwright.stop()

if __name__ == "__main__":
    logger.info("ラベルサイズ変更テストを開始...")
    asyncio.run(test_label_size_changes())
    logger.info("テスト完了!")
