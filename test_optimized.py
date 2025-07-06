"""
最適化されたGraTeX Botのテストスクリプト（Desmos経由なし）
GraTeX内部APIを直接使用してテスト
"""

import asyncio
import base64
import logging
from playwright.async_api import async_playwright

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_gratex_direct_api():
    """GraTeX内部APIを直接使用してテスト"""
    
    test_expressions = [
        "x^2 + y^2 = 1",           # 円
        "y = sin(x)",              # サイン関数
        "r = cos(3θ)",             # 薔薇曲線
        "y = x^2",                 # 放物線
        "x^2/4 + y^2/9 = 1"        # 楕円
    ]
    
    playwright = await async_playwright().start()
    
    try:
        # ブラウザ起動
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-web-security'
            ]
        )
        
        page = await browser.new_page()
        
        for i, expression in enumerate(test_expressions):
            logger.info(f"\n=== テスト {i+1}: {expression} ===")
            
            try:
                # GraTeXページにアクセス
                await page.goto('https://teth-main.github.io/GraTeX/?wide=true&credit=true')
                await page.wait_for_load_state('networkidle')
                
                # GraTeX.calculator2Dが利用可能になるまで待機
                await page.wait_for_function(
                    "() => window.GraTeX && window.GraTeX.calculator2D",
                    timeout=10000
                )
                logger.info("GraTeX API が利用可能になりました")
                
                # LaTeX式をGraTeX Calculator APIで設定
                logger.info(f"LaTeX式を設定: {expression}")
                await page.evaluate(f"""
                    () => {{
                        if (window.GraTeX && window.GraTeX.calculator2D) {{
                            window.GraTeX.calculator2D.setExpression({{latex: `{expression}`}});
                            console.log("数式を設定しました:", `{expression}`);
                        }} else {{
                            throw new Error("GraTeX.calculator2D が利用できません");
                        }}
                    }}
                """)
                
                # 少し待機してグラフが描画されるのを待つ
                await asyncio.sleep(2)
                
                # ラベルサイズを設定（4に設定）
                try:
                    label_selects = await page.query_selector_all('select.form-control')
                    if len(label_selects) >= 2:
                        await label_selects[1].select_option('4')
                        logger.info("ラベルサイズを4に設定")
                except Exception as e:
                    logger.warning(f"ラベルサイズの設定に失敗: {e}")
                
                # Generateボタンをクリック
                logger.info("スクリーンショットボタンをクリック...")
                await page.click('#screenshot-button')
                
                # 画像生成完了を待機
                logger.info("画像生成を待機中...")
                await page.wait_for_function(
                    """
                    () => {
                        const previewImg = document.getElementById('preview');
                        return previewImg && previewImg.src && previewImg.src.length > 100;
                    }
                    """,
                    timeout=15000
                )
                
                # 生成された画像をid="preview"から取得
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
                    logger.info("✅ 画像データの取得に成功!")
                    logger.info(f"データサイズ: {len(image_data)} 文字")
                    
                    # 画像を保存
                    image_bytes = base64.b64decode(image_data.split(',')[1])
                    filename = f"test_optimized_{i+1}_{expression.replace(' ', '_').replace('=', 'eq').replace('/', 'div')}.png"
                    # ファイル名の無効文字を削除
                    filename = filename.replace('^', 'pow').replace('θ', 'theta').replace('+', 'plus')
                    
                    with open(filename, 'wb') as f:
                        f.write(image_bytes)
                    logger.info(f"画像を {filename} として保存しました")
                else:
                    logger.error("❌ 画像データの取得に失敗")
                
            except Exception as e:
                logger.error(f"テスト {i+1} でエラー: {e}")
                
        await browser.close()
        
    except Exception as e:
        logger.error(f"全体的なエラー: {e}")
        
    finally:
        await playwright.stop()

if __name__ == "__main__":
    logger.info("GraTeX 最適化版テストを開始...")
    asyncio.run(test_gratex_direct_api())
    logger.info("テスト完了!")
