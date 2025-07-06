"""
GraTeX Bot ズーム機能のテストスクリプト
"""

import asyncio
import base64
import logging
from playwright.async_api import async_playwright

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_zoom_functionality():
    """ズーム機能のテスト"""
    
    expression = "y = x^2"
    
    playwright = await async_playwright().start()
    
    try:
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-background-timer-throttling'
            ]
        )
        
        page = await browser.new_page()
        page.set_default_timeout(30000)
        
        # GraTeXページにアクセス
        await page.goto('https://teth-main.github.io/GraTeX/?wide=true&credit=true', 
                       wait_until='networkidle', timeout=30000)
        
        # GraTeX.calculator2Dが利用可能になるまで待機
        await page.wait_for_function(
            "() => window.GraTeX && window.GraTeX.calculator2D",
            timeout=15000
        )
        
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
        
        # 初期画像を生成
        logger.info("=== 初期画像生成 ===")
        await page.click('#screenshot-button')
        await page.wait_for_function(
            """
            () => {
                const previewImg = document.getElementById('preview');
                return previewImg && previewImg.src && previewImg.src.length > 100;
            }
            """,
            timeout=20000
        )
        
        # 初期画像を保存
        await save_current_image(page, "initial")
        
        # ズームイン操作をテスト
        logger.info("=== ズームイン テスト ===")
        await test_zoom_operation(page, 'in')
        
        # ズームアウト操作をテスト
        logger.info("=== ズームアウト テスト ===")
        await test_zoom_operation(page, 'out')
        
        await browser.close()
        
    except Exception as e:
        logger.error(f"テストエラー: {e}")
        
    finally:
        await playwright.stop()

async def test_zoom_operation(page, zoom_direction):
    """ズーム操作のテスト"""
    try:
        zoom_text = "拡大" if zoom_direction == 'in' else "縮小"
        logger.info(f"{zoom_text}操作を実行中...")
        
        if zoom_direction == 'in':
            # ズームインボタンを探してクリック
            zoom_result = await page.evaluate('''
                () => {
                    // Desmosのズームインボタンを探す
                    const selectors = [
                        'button.dcg-unstyled-button.dcg-action-zoomin.dcg-pillbox-btn-interior',
                        'button.dcg-action-zoomin',
                        'button[aria-label*="zoom in"]',
                        'button[title*="zoom in"]'
                    ];
                    
                    for (let selector of selectors) {
                        const button = document.querySelector(selector);
                        if (button) {
                            button.click();
                            console.log("ズームインボタンをクリック:", selector);
                            return true;
                        }
                    }
                    
                    // フォールバック: キーボードショートカット
                    const event = new KeyboardEvent('keydown', {
                        key: '+',
                        code: 'Equal',
                        ctrlKey: true,
                        bubbles: true
                    });
                    document.dispatchEvent(event);
                    console.log("キーボードショートカットでズームイン");
                    return false;
                }
            ''')
        else:
            # ズームアウトボタンを探してクリック
            zoom_result = await page.evaluate('''
                () => {
                    // Desmosのズームアウトボタンを探す
                    const selectors = [
                        'button.dcg-unstyled-button.dcg-action-zoomout.dcg-pillbox-btn-interior',
                        'button.dcg-action-zoomout',
                        'button[aria-label*="zoom out"]',
                        'button[title*="zoom out"]'
                    ];
                    
                    for (let selector of selectors) {
                        const button = document.querySelector(selector);
                        if (button) {
                            button.click();
                            console.log("ズームアウトボタンをクリック:", selector);
                            return true;
                        }
                    }
                    
                    // フォールバック: キーボードショートカット
                    const event = new KeyboardEvent('keydown', {
                        key: '-',
                        code: 'Minus',
                        ctrlKey: true,
                        bubbles: true
                    });
                    document.dispatchEvent(event);
                    console.log("キーボードショートカットでズームアウト");
                    return false;
                }
            ''')
        
        logger.info(f"{zoom_text}操作結果: {zoom_result}")
        
        # ズーム後に少し待機
        await asyncio.sleep(2)
        
        # 新しい画像を生成
        await page.click('#screenshot-button')
        await page.wait_for_function(
            """
            () => {
                const previewImg = document.getElementById('preview');
                return previewImg && previewImg.src && previewImg.src.length > 100;
            }
            """,
            timeout=20000
        )
        
        # ズーム後の画像を保存
        await save_current_image(page, f"zoom_{zoom_direction}")
        
        logger.info(f"✅ {zoom_text}操作完了")
        
    except Exception as e:
        logger.error(f"{zoom_text}操作エラー: {e}")

async def save_current_image(page, suffix):
    """現在の画像を保存"""
    try:
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
            image_bytes = base64.b64decode(image_data.split(',')[1])
            filename = f"test_zoom_{suffix}.png"
            
            with open(filename, 'wb') as f:
                f.write(image_bytes)
            logger.info(f"画像を {filename} として保存しました")
        else:
            logger.error(f"画像データの取得に失敗: {suffix}")
            
    except Exception as e:
        logger.error(f"画像保存エラー: {e}")

if __name__ == "__main__":
    logger.info("ズーム機能テストを開始...")
    asyncio.run(test_zoom_functionality())
    logger.info("テスト完了!")
