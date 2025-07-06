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
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            self.page = await self.browser.new_page()
            
            # GraTeXページにアクセス
            await self.page.goto('https://teth-main.github.io/GraTeX/?wide=true&credit=true')
            await self.page.wait_for_load_state('networkidle')
            
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
                timeout=10000
            )
            
            # ラベルサイズを事前に設定
            if label_size in [1, 2, 2.5, 3, 4, 6, 8]:
                try:
                    label_selects = await self.page.query_selector_all('select.form-control')
                    if len(label_selects) >= 2:  # 2番目のselectがラベルサイズ
                        await label_selects[1].select_option(str(label_size))
                        logger.info(f"ラベルサイズを{label_size}に設定")
                except Exception as e:
                    logger.warning(f"ラベルサイズの設定に失敗: {e}")
            
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
            await asyncio.sleep(2)
            
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
                timeout=15000
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
        
        # リアクションを追加（ラベルサイズ変更用）
        reactions = ['1⃣', '2⃣', '3⃣', '4⃣', '6⃣', '8⃣', '✅', '🚮']
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
            str(reaction.emoji) in ['1⃣', '2⃣', '3⃣', '4⃣', '6⃣', '8⃣', '✅', '🚮']
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
        image_buffer = await gratex_bot.generate_graph(latex_expression, label_size, 0)
        
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
