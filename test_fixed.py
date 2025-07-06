import asyncio
from playwright.async_api import async_playwright
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_fixed_gratex():
    """修正されたGraTeXの動作をテスト"""
    
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
            
            # Step 1: Desmosでグラフを作成
            logger.info("=== Step 1: Desmosでグラフ作成 ===")
            desmos_page = await browser.new_page()
            await desmos_page.goto('https://www.desmos.com/calculator')
            await desmos_page.wait_for_load_state('networkidle')
            
            # LaTeX式を入力
            test_latex = "x^2 + y^2 = 1"
            logger.info(f"LaTeX式 '{test_latex}' をDesmosに入力中...")
            
            # 式入力エリアを探す
            expression_input = await desmos_page.wait_for_selector('.dcg-mq-editable-field', timeout=10000)
            await expression_input.click()
            await expression_input.type(test_latex)
            
            # 少し待機
            await asyncio.sleep(3)
            
            # URLを取得
            current_url = desmos_page.url
            logger.info(f"Desmos URL: {current_url}")
            
            # ハッシュを抽出
            if '#' in current_url:
                hash_value = current_url.split('#')[1]
                logger.info(f"抽出されたハッシュ: {hash_value}")
            else:
                hash_value = current_url
                logger.info("ハッシュが見つからないため、完全なURLを使用")
            
            await desmos_page.close()
            
            # Step 2: GraTeXでハッシュを使用
            logger.info("=== Step 2: GraTeXで画像生成 ===")
            gratex_page = await browser.new_page()
            await gratex_page.goto('https://teth-main.github.io/GraTeX/?wide=true&credit=true')
            await gratex_page.wait_for_load_state('networkidle')
            
            # ハッシュを入力
            logger.info(f"ハッシュ '{hash_value}' をGraTeXに入力中...")
            await gratex_page.fill('#desmos-hash', hash_value)
            
            # ラベルサイズを設定（4に設定）
            label_selects = await gratex_page.query_selector_all('select.form-control')
            if len(label_selects) >= 2:
                await label_selects[1].select_option('4')
                logger.info("ラベルサイズを4に設定")
            
            # Generateボタンをクリック
            logger.info("Generateボタンをクリック...")
            await gratex_page.click('#screenshot-button')
            
            # 画像生成完了を待機
            logger.info("画像生成を待機中...")
            await asyncio.sleep(8)  # 長めに待機
            
            # 生成された画像を取得
            logger.info("画像データを取得中...")
            image_data = await gratex_page.evaluate('''
                () => {
                    // 全てのキャンバスを確認
                    const allCanvas = document.querySelectorAll('canvas');
                    console.log('Found', allCanvas.length, 'canvas elements');
                    
                    for (let i = 0; i < allCanvas.length; i++) {
                        const canvas = allCanvas[i];
                        console.log(`Canvas ${i}: ${canvas.width}x${canvas.height}, class: ${canvas.className}`);
                        
                        if (canvas.width > 0 && canvas.height > 0) {
                            try {
                                const dataURL = canvas.toDataURL('image/png');
                                if (dataURL && dataURL.length > 100) {
                                    console.log(`Successfully captured canvas ${i}`);
                                    return dataURL;
                                }
                            } catch (e) {
                                console.log(`Error capturing canvas ${i}:`, e);
                            }
                        }
                    }
                    
                    return null;
                }
            ''')
            
            if image_data:
                logger.info("✅ 画像データの取得に成功!")
                logger.info(f"データサイズ: {len(image_data)} 文字")
                
                # 画像を保存
                import base64
                image_bytes = base64.b64decode(image_data.split(',')[1])
                with open('test_gratex_output.png', 'wb') as f:
                    f.write(image_bytes)
                logger.info("画像を test_gratex_output.png として保存しました")
                
            else:
                logger.error("❌ 画像データを取得できませんでした")
                
                # デバッグ: ページの状態を確認
                page_content = await gratex_page.content()
                if 'error' in page_content.lower():
                    logger.error("ページにエラーメッセージが含まれています")
            
            # スクリーンショットを保存
            await gratex_page.screenshot(path='test_gratex_page.png')
            logger.info("ページのスクリーンショットを保存しました: test_gratex_page.png")
            
            await gratex_page.close()
            await browser.close()
            
        except Exception as e:
            logger.error(f"テストエラー: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(test_fixed_gratex())
