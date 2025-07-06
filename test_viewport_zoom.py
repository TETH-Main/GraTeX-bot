"""
GraTeX ビューポート操作によるズーム機能のテストスクリプト
"""

import asyncio
import base64
import logging
from playwright.async_api import async_playwright

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_viewport_zoom():
    """ビューポート操作によるズーム機能のテスト"""
    
    expression = "x^2 + y^2 = 1"
    
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
        
        # 初期ビューポートを取得
        initial_viewport = await get_current_viewport(page)
        logger.info(f"初期ビューポート: {initial_viewport}")
        
        # 初期画像を保存
        await save_current_image(page, "viewport_initial")
        
        # ズームイン操作をテスト
        logger.info("=== ビューポート ズームイン テスト ===")
        await test_viewport_zoom_operation(page, 'in')
        
        # ズームアウト操作をテスト
        logger.info("=== ビューポート ズームアウト テスト ===")
        await test_viewport_zoom_operation(page, 'out')
        
        # 極端なズームテスト
        logger.info("=== 極端なズームテスト ===")
        await test_extreme_zoom(page)
        
        await browser.close()
        
    except Exception as e:
        logger.error(f"テストエラー: {e}")
        
    finally:
        await playwright.stop()

async def get_current_viewport(page):
    """現在のビューポートを取得"""
    return await page.evaluate('''
        () => {
            if (window.GraTeX && window.GraTeX.calculator2D) {
                try {
                    const state = window.GraTeX.calculator2D.getState();
                    return state.graph.viewport;
                } catch (e) {
                    console.error("ビューポート取得エラー:", e);
                    return null;
                }
            }
            return null;
        }
    ''')

async def test_viewport_zoom_operation(page, zoom_direction):
    """ビューポート操作によるズームテスト"""
    try:
        zoom_text = "拡大" if zoom_direction == 'in' else "縮小"
        logger.info(f"ビューポート{zoom_text}操作を実行中...")
        
        # 現在のビューポートを取得
        current_viewport = await get_current_viewport(page)
        if not current_viewport:
            logger.error("ビューポート取得失敗")
            return
        
        logger.info(f"変更前ビューポート: {current_viewport}")
        
        # 新しいビューポートを計算
        xmin = current_viewport.get('xmin', -10)
        xmax = current_viewport.get('xmax', 10)
        ymin = current_viewport.get('ymin', -10)
        ymax = current_viewport.get('ymax', 10)
        
        # 現在の範囲の中心と幅/高さを計算
        x_center = (xmin + xmax) / 2
        y_center = (ymin + ymax) / 2
        x_range = xmax - xmin
        y_range = ymax - ymin
        
        if zoom_direction == 'in':
            # ズームイン：範囲を半分にする（拡大）
            new_x_range = x_range / 2
            new_y_range = y_range / 2
        else:
            # ズームアウト：範囲を2倍にする（縮小）
            new_x_range = x_range * 2
            new_y_range = y_range * 2
        
        # 新しいビューポートを計算
        new_xmin = x_center - new_x_range / 2
        new_xmax = x_center + new_x_range / 2
        new_ymin = y_center - new_y_range / 2
        new_ymax = y_center + new_y_range / 2
        
        logger.info(f"新しいビューポート: xmin={new_xmin}, xmax={new_xmax}, ymin={new_ymin}, ymax={new_ymax}")
        
        # ビューポートを設定
        result = await page.evaluate(f'''
            () => {{
                if (window.GraTeX && window.GraTeX.calculator2D) {{
                    try {{
                        window.GraTeX.calculator2D.setMathBounds({{
                            left: {new_xmin},
                            right: {new_xmax},
                            bottom: {new_ymin},
                            top: {new_ymax}
                        }});
                        console.log("ビューポートを設定しました");
                        return true;
                    }} catch (e) {{
                        console.error("ビューポート設定エラー:", e);
                        return false;
                    }}
                }}
                return false;
            }}
        ''')
        
        logger.info(f"ビューポート設定結果: {result}")
        
        # 設定後に少し待機
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
        
        # 変更後のビューポートを確認
        updated_viewport = await get_current_viewport(page)
        logger.info(f"変更後ビューポート: {updated_viewport}")
        
        # 画像を保存
        await save_current_image(page, f"viewport_zoom_{zoom_direction}")
        
        logger.info(f"✅ ビューポート{zoom_text}操作完了")
        
    except Exception as e:
        logger.error(f"ビューポート{zoom_text}操作エラー: {e}")

async def test_extreme_zoom(page):
    """極端なズームのテスト"""
    try:
        # 非常に小さな範囲に設定（大幅拡大）
        logger.info("極小範囲設定テスト...")
        await page.evaluate('''
            () => {
                if (window.GraTeX && window.GraTeX.calculator2D) {
                    window.GraTeX.calculator2D.setMathBounds({
                        left: -0.5,
                        right: 0.5,
                        bottom: -0.5,
                        top: 0.5
                    });
                }
            }
        ''')
        
        await asyncio.sleep(2)
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
        
        await save_current_image(page, "viewport_extreme_in")
        
        # 非常に大きな範囲に設定（大幅縮小）
        logger.info("極大範囲設定テスト...")
        await page.evaluate('''
            () => {
                if (window.GraTeX && window.GraTeX.calculator2D) {
                    window.GraTeX.calculator2D.setMathBounds({
                        left: -50,
                        right: 50,
                        bottom: -50,
                        top: 50
                    });
                }
            }
        ''')
        
        await asyncio.sleep(2)
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
        
        await save_current_image(page, "viewport_extreme_out")
        
        logger.info("✅ 極端なズームテスト完了")
        
    except Exception as e:
        logger.error(f"極端なズームテストエラー: {e}")

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
            filename = f"test_{suffix}.png"
            
            with open(filename, 'wb') as f:
                f.write(image_bytes)
            logger.info(f"画像を {filename} として保存しました")
        else:
            logger.error(f"画像データの取得に失敗: {suffix}")
            
    except Exception as e:
        logger.error(f"画像保存エラー: {e}")

if __name__ == "__main__":
    logger.info("ビューポート操作ズーム機能テストを開始...")
    asyncio.run(test_viewport_zoom())
    logger.info("テスト完了!")
