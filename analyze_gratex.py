import asyncio
from playwright.async_api import async_playwright
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def analyze_gratex_website():
    """GraTeXウェブサイトを詳細分析"""
    
    async with async_playwright() as p:
        try:
            # ブラウザ起動
            browser = await p.chromium.launch(
                headless=False,  # デバッグ用に表示
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                ]
            )
            
            page = await browser.new_page()
            
            # ページにアクセス
            logger.info("GraTeXページにアクセス中...")
            await page.goto('https://teth-main.github.io/GraTeX/?wide=true&credit=true')
            
            # ページ読み込み完了を待機
            await page.wait_for_load_state('networkidle')
            logger.info("ページ読み込み完了")
            
            # DOM要素を詳細調査
            logger.info("=== DOM要素の調査 ===")
            
            # 1. テキストエリア/入力フィールドを探す
            textareas = await page.query_selector_all('textarea')
            inputs = await page.query_selector_all('input[type="text"]')
            
            logger.info(f"見つかったtextarea: {len(textareas)}個")
            logger.info(f"見つかったtext input: {len(inputs)}個")
            
            # 各要素の詳細を取得
            for i, textarea in enumerate(textareas):
                placeholder = await textarea.get_attribute('placeholder')
                id_attr = await textarea.get_attribute('id')
                class_attr = await textarea.get_attribute('class')
                logger.info(f"Textarea {i}: id='{id_attr}', class='{class_attr}', placeholder='{placeholder}'")
            
            for i, input_elem in enumerate(inputs):
                placeholder = await input_elem.get_attribute('placeholder')
                id_attr = await input_elem.get_attribute('id')
                class_attr = await input_elem.get_attribute('class')
                logger.info(f"Input {i}: id='{id_attr}', class='{class_attr}', placeholder='{placeholder}'")
            
            # 2. Canvas要素を探す
            canvases = await page.query_selector_all('canvas')
            logger.info(f"見つかったcanvas: {len(canvases)}個")
            
            for i, canvas in enumerate(canvases):
                id_attr = await canvas.get_attribute('id')
                class_attr = await canvas.get_attribute('class')
                width = await canvas.get_attribute('width')
                height = await canvas.get_attribute('height')
                logger.info(f"Canvas {i}: id='{id_attr}', class='{class_attr}', size={width}x{height}")
            
            # 3. ボタン要素を探す
            buttons = await page.query_selector_all('button')
            logger.info(f"見つかったbutton: {len(buttons)}個")
            
            for i, button in enumerate(buttons):
                text = await button.inner_text()
                id_attr = await button.get_attribute('id')
                class_attr = await button.get_attribute('class')
                logger.info(f"Button {i}: id='{id_attr}', class='{class_attr}', text='{text}'")
            
            # 4. セレクト要素を探す
            selects = await page.query_selector_all('select')
            logger.info(f"見つかったselect: {len(selects)}個")
            
            for i, select in enumerate(selects):
                id_attr = await select.get_attribute('id')
                class_attr = await select.get_attribute('class')
                logger.info(f"Select {i}: id='{id_attr}', class='{class_attr}'")
                
                # オプションも確認
                options = await select.query_selector_all('option')
                for j, option in enumerate(options):
                    value = await option.get_attribute('value')
                    text = await option.inner_text()
                    logger.info(f"  Option {j}: value='{value}', text='{text}'")
            
            # 5. Desmosのiframe/embedを探す
            iframes = await page.query_selector_all('iframe')
            logger.info(f"見つかったiframe: {len(iframes)}個")
            
            for i, iframe in enumerate(iframes):
                src = await iframe.get_attribute('src')
                id_attr = await iframe.get_attribute('id')
                class_attr = await iframe.get_attribute('class')
                logger.info(f"Iframe {i}: id='{id_attr}', class='{class_attr}', src='{src}'")
            
            # 6. 実際に数式を入力してみる
            logger.info("=== 実際のテスト ===")
            
            # まずは最初に見つかったtextareaに入力してみる
            if textareas:
                test_latex = "x^2 + y^2 = 1"
                logger.info(f"テスト数式 '{test_latex}' を入力中...")
                
                # 最初のtextareaに入力
                await textareas[0].fill(test_latex)
                await page.wait_for_timeout(2000)
                
                # Generateボタンを探して押す
                generate_buttons = await page.query_selector_all('button')
                for button in generate_buttons:
                    text = await button.inner_text()
                    if 'Generate' in text or 'generate' in text:
                        logger.info(f"'{text}'ボタンをクリック")
                        await button.click()
                        break
                
                # 少し待って結果を確認
                await page.wait_for_timeout(5000)
                
                # Canvasから画像データを取得してみる
                if canvases:
                    logger.info("Canvas画像データの取得を試行...")
                    try:
                        image_data = await page.evaluate('''
                            () => {
                                const canvas = document.querySelector('canvas');
                                return canvas ? canvas.toDataURL('image/png') : null;
                            }
                        ''')
                        
                        if image_data:
                            logger.info("✅ 画像データの取得に成功!")
                            logger.info(f"データサイズ: {len(image_data)} 文字")
                        else:
                            logger.warning("❌ 画像データが取得できませんでした")
                            
                    except Exception as e:
                        logger.error(f"画像データ取得エラー: {e}")
            
            # ページのHTMLソースも一部確認
            logger.info("=== ページソースの確認 ===")
            content = await page.content()
            
            # Desmosに関する記述を探す
            if 'desmos' in content.lower():
                logger.info("✅ Desmosの記述を発見")
            if 'calculator' in content.lower():
                logger.info("✅ calculatorの記述を発見")
            if 'latex' in content.lower():
                logger.info("✅ LaTeXの記述を発見")
            
            # スクリーンショットを保存
            await page.screenshot(path='gratex_analysis.png')
            logger.info("スクリーンショットを保存しました: gratex_analysis.png")
            
            await browser.close()
            
        except Exception as e:
            logger.error(f"分析エラー: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(analyze_gratex_website())
