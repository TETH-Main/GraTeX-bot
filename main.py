import discord
from discord.ext import commands
import asyncio
import base64
import io
import os
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from PIL import Image
import re
import logging

# 環境変数を読み込み
load_dotenv()

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot設定
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

class GraTeXBot:
    def __init__(self):
        self.browser = None
        self.page = None
        
    async def initialize_browser(self):
        """Playwrightブラウザを初期化"""
        try:
            self.playwright = await async_playwright().start()
            
            # Railway環境用のブラウザ起動オプション
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding'
                ]
            )
            
            self.page = await self.browser.new_page()
            
            # タイムアウトを延長
            self.page.set_default_timeout(30000)
            
            # GraTeXページにアクセス（リトライ付き）
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await self.page.goto('https://teth-main.github.io/GraTeX/?wide=true&credit=true', 
                                        wait_until='networkidle', timeout=30000)
                    logger.info(f"GraTeXページへのアクセス成功 (試行 {attempt + 1})")
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    logger.warning(f"GraTeXページアクセス失敗 (試行 {attempt + 1}): {e}")
                    await asyncio.sleep(2)
            
            logger.info("ブラウザの初期化が完了しました")
            
        except Exception as e:
            logger.error(f"ブラウザの初期化に失敗: {e}")
            raise
    
    async def generate_graph(self, latex_expression, label_size=4):
        """LaTeX式からグラフ画像を生成（GraTeX内部API使用）"""
        try:
            if not self.page:
                await self.initialize_browser()
            
            # 現在のURLがGraTeXでない場合は移動
            current_url = self.page.url
            if 'teth-main.github.io/GraTeX' not in current_url:
                await self.page.goto('https://teth-main.github.io/GraTeX/?wide=true&credit=true')
                await self.page.wait_for_load_state('networkidle')
            
            # GraTeX.calculator2Dが利用可能になるまで待機
            await self.page.wait_for_function(
                "() => window.GraTeX && window.GraTeX.calculator2D",
                timeout=15000
            )
            
            # ラベルサイズを事前に設定
            if label_size in [1, 2, 3, 4, 6, 8]:
                try:
                    # name="labelSize"のselectを探す
                    label_select = await self.page.wait_for_selector('select[name="labelSize"]', timeout=5000)
                    await label_select.select_option(str(label_size))
                    logger.info(f"ラベルサイズを{label_size}に設定")
                except Exception as e:
                    logger.warning(f"ラベルサイズの設定に失敗、フォールバック: {e}")
                    # フォールバック: form-controlクラスのselectを使用
                    try:
                        label_selects = await self.page.query_selector_all('select.form-control')
                        if len(label_selects) >= 2:  # 2番目のselectがラベルサイズ
                            await label_selects[1].select_option(str(label_size))
                            logger.info(f"フォールバックでラベルサイズを{label_size}に設定")
                    except Exception as e2:
                        logger.warning(f"フォールバックも失敗: {e2}")
            
            # LaTeX式をGraTeX Calculator APIで直接設定
            logger.info(f"LaTeX式を設定: {latex_expression}")
            await self.page.evaluate(f"""
                () => {{
                    if (window.GraTeX && window.GraTeX.calculator2D) {{
                        window.GraTeX.calculator2D.setBlank();
                        window.GraTeX.calculator2D.setExpression({{latex: `{latex_expression}`}});
                        console.log("数式を設定しました:", `{latex_expression}`);
                    }} else {{
                        throw new Error("GraTeX.calculator2D が利用できません");
                    }}
                }}
            """)
            
            # 少し待機してグラフが描画されるのを待つ
            await asyncio.sleep(3)
            
            # Generateボタンをクリック
            logger.info("スクリーンショットボタンをクリック...")
            await self.page.click('#screenshot-button')
            
            # 画像生成完了を待機 - id="preview"のimgタグが更新されるまで待つ
            logger.info("画像生成を待機中...")
            await self.page.wait_for_function(
                """
                () => {
                    const previewImg = document.getElementById('preview');
                    return previewImg && previewImg.src && previewImg.src.length > 100;
                }
                """,
                timeout=20000
            )
            
            # 生成された画像をid="preview"から取得
            image_data = await self.page.evaluate('''
                () => {
                    const previewImg = document.getElementById('preview');
                    if (previewImg && previewImg.src) {
                        // imgのsrcがdata URLの場合はそのまま返す
                        if (previewImg.src.startsWith('data:')) {
                            return previewImg.src;
                        }
                        
                        // imgのsrcがblobやURLの場合は、canvasに描画してdata URLを取得
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
            
            if not image_data:
                # フォールバック: キャンバスから直接取得を試行
                logger.warning("preview imgから画像を取得できませんでした。キャンバスから取得を試行...")
                image_data = await self.page.evaluate('''
                    () => {
                        const allCanvas = document.querySelectorAll('canvas');
                        for (let canvas of allCanvas) {
                            if (canvas.width > 0 && canvas.height > 0) {
                                try {
                                    return canvas.toDataURL('image/png');
                                } catch (e) {
                                    continue;
                                }
                            }
                        }
                        return null;
                    }
                ''')
            
            if not image_data:
                raise Exception("画像の生成に失敗しました - preview imgもキャンバスも見つかりません")
            
            logger.info("✅ 画像データの取得に成功!")
            
            # base64データを画像に変換
            image_bytes = base64.b64decode(image_data.split(',')[1])
            return io.BytesIO(image_bytes)
            
        except Exception as e:
            logger.error(f"グラフ生成エラー: {e}")
            raise
    
    async def close(self):
        """リソースをクリーンアップ"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
        except Exception as e:
            logger.error(f"クリーンアップエラー: {e}")

    async def zoom_desmos_graph(self, zoom_direction):
        """GraTeX内のDesmosグラフをズームイン/アウト（ビューポート操作）"""
        try:
            # 現在のビューポートを取得
            current_viewport = await self.page.evaluate('''
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
            
            if not current_viewport:
                logger.warning("現在のビューポートを取得できませんでした")
                return False
            
            logger.info(f"現在のビューポート: {current_viewport}")
            
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
            
            # 新しいビューポートを設定
            result = await self.page.evaluate(f'''
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
            
            # ズーム操作後に少し待機
            await asyncio.sleep(1)
            
            return result
            
        except Exception as e:
            logger.error(f"Desmosズーム操作エラー: {e}")
            return False

# グローバルインスタンス
gratex_bot = GraTeXBot()

@bot.event
async def on_ready():
    """Bot起動時の処理"""
    logger.info(f'{bot.user} がログインしました!')
    try:
        await gratex_bot.initialize_browser()
        logger.info("GraTeX Bot の初期化が完了しました")
    except Exception as e:
        logger.error(f"初期化エラー: {e}")

@bot.command(name='gratex')
async def generate_latex_graph(ctx, latex_expression: str, label_size: int = 4):
    """
    LaTeX式からグラフを生成するコマンド（GraTeX内部API使用）
    
    使用例:
    !gratex "x^2 + y^2 = 1"
    !gratex "y = sin(x)" 3
    !gratex "r = cos(3θ)" 6
    """
    
    # パラメータ検証
    if label_size not in [1, 2, 3, 4, 6, 8]:
        await ctx.send("❌ ラベルサイズは 1, 2, 3, 4, 6, 8 のいずれかを指定してください")
        return
    
    # LaTeX式の簡単な検証
    if not latex_expression.strip():
        await ctx.send("❌ LaTeX式を入力してください")
        return
    
    try:
        # 処理中メッセージ
        processing_msg = await ctx.send("🎨 GraTeXでグラフを生成中...")
        
        # グラフ生成
        image_buffer = await gratex_bot.generate_graph(
            latex_expression, label_size
        )
        
        # Discord画像ファイルを作成
        file = discord.File(image_buffer, filename=f"gratex_graph.png")
        
        # 結果を送信
        embed = discord.Embed(
            title="📊 GraTeX グラフ",
            description=f"**LaTeX式:** `{latex_expression}`\n**ラベルサイズ:** {label_size}",
            color=0x00ff00
        )
        embed.set_image(url="attachment://gratex_graph.png")
        embed.set_footer(text="Powered by GraTeX")
        
        message = await ctx.send(file=file, embed=embed)
        
        # リアクションを追加（ラベルサイズ変更用 + ズーム機能）
        reactions = ['1⃣', '2⃣', '3⃣', '4⃣', '6⃣', '8⃣', '🔍', '🔭', '✅', '🚮']
        for reaction in reactions:
            await message.add_reaction(reaction)
        
        # 処理中メッセージを削除
        await processing_msg.delete()
        
        # リアクション処理を設定
        await setup_reaction_handler(ctx, message, latex_expression, label_size)
        
    except Exception as e:
        logger.error(f"グラフ生成エラー: {e}")
        await ctx.send(f"❌ グラフの生成に失敗しました: {str(e)}")
        
        # 処理中メッセージがある場合は削除
        try:
            await processing_msg.delete()
        except:
            pass

async def setup_reaction_handler(ctx, message, latex_expression, current_label_size):
    """リアクション処理のセットアップ"""
    
    def check(reaction, user):
        return (
            user == ctx.author and 
            reaction.message.id == message.id and
            str(reaction.emoji) in ['1⃣', '2⃣', '3⃣', '4⃣', '6⃣', '8⃣', '🔍', '🔭', '✅', '🚮']
        )
    
    timeout_duration = 300  # 5分
    
    while True:
        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=timeout_duration, check=check)
            emoji = str(reaction.emoji)
            
            if emoji == '🚮':
                # メッセージ削除
                await message.delete()
                break
                
            elif emoji == '✅':
                # 完了
                await message.clear_reactions()
                break
                
            elif emoji in ['1⃣', '2⃣', '3⃣', '4⃣', '6⃣', '8⃣']:
                # ラベルサイズ変更
                size_map = {'1⃣': 1, '2⃣': 2, '3⃣': 3, '4⃣': 4, '6⃣': 6, '8⃣': 8}
                new_label_size = size_map[emoji]
                
                if new_label_size != current_label_size:
                    await update_graph(message, latex_expression, new_label_size)
                    current_label_size = new_label_size
                    
            elif emoji == '🔍':
                # 拡大（ズームイン）
                await zoom_graph(message, latex_expression, current_label_size, 'in')
                
            elif emoji == '🔭':
                # 縮小（ズームアウト）
                await zoom_graph(message, latex_expression, current_label_size, 'out')
            
            # リアクションを削除
            await reaction.remove(user)
            
        except asyncio.TimeoutError:
            await message.clear_reactions()
            break
        except Exception as e:
            logger.error(f"リアクション処理エラー: {e}")
            break

async def update_graph(message, latex_expression, label_size):
    """グラフを更新"""
    try:
        # 新しいグラフを生成
        image_buffer = await gratex_bot.generate_graph(latex_expression, label_size)
        
        # 新しいファイルを作成
        file = discord.File(image_buffer, filename=f"gratex_graph_updated.png")
        
        # Embedを更新
        embed = discord.Embed(
            title="📊 GraTeX グラフ (更新済み)",
            description=f"**LaTeX式:** `{latex_expression}`\n**ラベルサイズ:** {label_size}",
            color=0x00ff00
        )
        embed.set_image(url="attachment://gratex_graph_updated.png")
        embed.set_footer(text="Powered by GraTeX")
        
        # メッセージを編集
        await message.edit(attachments=[file], embed=embed)
        
    except Exception as e:
        logger.error(f"グラフ更新エラー: {e}")

async def zoom_graph(message, latex_expression, label_size, zoom_direction):
    """グラフをズームイン/アウトして更新"""
    try:
        # Desmosでズーム操作を実行
        zoom_text = "拡大" if zoom_direction == 'in' else "縮小"
        logger.info(f"ビューポート{zoom_text}操作を実行中...")
        
        # ビューポート操作を実行
        zoom_result = await gratex_bot.zoom_desmos_graph(zoom_direction)
        
        if not zoom_result:
            logger.warning(f"ビューポート{zoom_text}操作が失敗しました")
            return
        
        # スクリーンショットボタンをクリックして新しい画像を生成
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
        
        # 生成された画像を取得
        image_data = await gratex_bot.page.evaluate('''
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
            # base64データを画像に変換
            image_bytes = base64.b64decode(image_data.split(',')[1])
            image_buffer = io.BytesIO(image_bytes)
            
            # 新しいファイルを作成
            file = discord.File(image_buffer, filename=f"gratex_graph_zoomed.png")
            
            # 変更後のビューポートを取得して表示
            new_viewport = await gratex_bot.page.evaluate('''
                () => {
                    if (window.GraTeX && window.GraTeX.calculator2D) {
                        try {
                            const state = window.GraTeX.calculator2D.getState();
                            return state.graph.viewport;
                        } catch (e) {
                            return null;
                        }
                    }
                    return null;
                }
            ''')
            
            viewport_info = ""
            if new_viewport:
                x_range = new_viewport.get('xmax', 0) - new_viewport.get('xmin', 0)
                y_range = new_viewport.get('ymax', 0) - new_viewport.get('ymin', 0)
                viewport_info = f"\n**表示範囲:** X: {x_range:.1f}, Y: {y_range:.1f}"
            
            # Embedを更新
            embed = discord.Embed(
                title=f"📊 GraTeX グラフ ({zoom_text}済み)",
                description=f"**LaTeX式:** `{latex_expression}`\n**ラベルサイズ:** {label_size}{viewport_info}",
                color=0x00ff00
            )
            embed.set_image(url="attachment://gratex_graph_zoomed.png")
            embed.set_footer(text="Powered by GraTeX")
            
            # メッセージを編集
            await message.edit(attachments=[file], embed=embed)
            
            logger.info(f"✅ ビューポート{zoom_text}操作完了")
        else:
            logger.error("ズーム後の画像取得に失敗")
        
    except Exception as e:
        logger.error(f"ズーム操作エラー: {e}")

@bot.event
async def on_command_error(ctx, error):
    """エラーハンドリング"""
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ LaTeX式を指定してください。例: `!gratex \"x^2 + y^2 = 1\"`")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ パラメータが正しくありません。")
    else:
        logger.error(f"コマンドエラー: {error}")
        await ctx.send("❌ エラーが発生しました。しばらく時間をおいて再試行してください。")

@bot.event
async def on_disconnect():
    """Bot切断時のクリーンアップ"""
    await gratex_bot.close()

# Keep-alive用サーバーを起動
from server import keep_alive

if __name__ == "__main__":
    # サーバーを起動
    keep_alive()
    
    # Botを起動
    token = os.getenv('TOKEN')
    if not token:
        raise ValueError("Discord Bot Token が設定されていません")
    
    try:
        bot.run(token)
    except KeyboardInterrupt:
        logger.info("Bot を停止しています...")
    finally:
        # クリーンアップ
        asyncio.run(gratex_bot.close())
