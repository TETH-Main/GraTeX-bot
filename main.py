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
    
    async def generate_graph(self, latex_expression, label_size=4, zoom_level=0):
        """LaTeX式からグラフ画像を生成"""
        try:
            if not self.page:
                await self.initialize_browser()
            
            # LaTeX式を入力
            await self.page.fill('textarea[placeholder*="LaTeX"]', latex_expression)
            
            # ラベルサイズを設定
            if label_size in [2, 3, 4, 6]:
                await self.page.select_option('select#labelSize', str(label_size))
            
            # ズームレベルを調整
            if zoom_level != 0:
                zoom_button = 'button#zoomIn' if zoom_level > 0 else 'button#zoomOut'
                for _ in range(abs(zoom_level)):
                    await self.page.click(zoom_button)
                    await asyncio.sleep(0.1)
            
            # 描画完了を待機
            await asyncio.sleep(2)
            
            # base64画像を取得
            image_data = await self.page.evaluate('''
                () => {
                    const canvas = document.querySelector('canvas');
                    return canvas ? canvas.toDataURL('image/png') : null;
                }
            ''')
            
            if not image_data:
                raise Exception("画像の生成に失敗しました")
            
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
async def generate_latex_graph(ctx, latex_expression: str, label_size: int = 4, zoom_level: int = 0):
    """
    LaTeX式からグラフを生成するコマンド
    
    使用例:
    !gratex "\\cos x \\le \\cos y"
    !gratex "x^2 + y^2 = 1" 3 2
    """
    
    # パラメータ検証
    if label_size not in [2, 3, 4, 6]:
        await ctx.send("❌ ラベルサイズは 2, 3, 4, 6 のいずれかを指定してください")
        return
    
    if abs(zoom_level) > 10:
        await ctx.send("❌ ズームレベルは -10 から 10 の範囲で指定してください")
        return
    
    # LaTeX式の簡単な検証
    if not latex_expression.strip():
        await ctx.send("❌ LaTeX式を入力してください")
        return
    
    try:
        # 処理中メッセージ
        processing_msg = await ctx.send("🎨 グラフを生成中...")
        
        # グラフ生成
        image_buffer = await gratex_bot.generate_graph(
            latex_expression, label_size, zoom_level
        )
        
        # Discord画像ファイルを作成
        file = discord.File(image_buffer, filename=f"gratex_graph.png")
        
        # 結果を送信
        embed = discord.Embed(
            title="📊 GraTeX グラフ",
            description=f"**LaTeX式:** `{latex_expression}`\n**ラベルサイズ:** {label_size}\n**ズーム:** {zoom_level}",
            color=0x00ff00
        )
        embed.set_image(url="attachment://gratex_graph.png")
        
        message = await ctx.send(file=file, embed=embed)
        
        # リアクションを追加
        reactions = ['2⃣', '3⃣', '4⃣', '6⃣', '🔎', '🔭', '✅', '🚮']
        for reaction in reactions:
            await message.add_reaction(reaction)
        
        # 処理中メッセージを削除
        await processing_msg.delete()
        
        # リアクション処理を設定
        await setup_reaction_handler(ctx, message, latex_expression, label_size, zoom_level)
        
    except Exception as e:
        logger.error(f"グラフ生成エラー: {e}")
        await ctx.send(f"❌ グラフの生成に失敗しました: {str(e)}")

async def setup_reaction_handler(ctx, message, latex_expression, current_label_size, current_zoom):
    """リアクション処理のセットアップ"""
    
    def check(reaction, user):
        return (
            user == ctx.author and 
            reaction.message.id == message.id and
            str(reaction.emoji) in ['2⃣', '3⃣', '4⃣', '6⃣', '🔎', '🔭', '✅', '🚮']
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
                
            elif emoji in ['2⃣', '3⃣', '4⃣', '6⃣']:
                # ラベルサイズ変更
                size_map = {'2⃣': 2, '3⃣': 3, '4⃣': 4, '6⃣': 6}
                new_label_size = size_map[emoji]
                
                if new_label_size != current_label_size:
                    await update_graph(message, latex_expression, new_label_size, current_zoom)
                    current_label_size = new_label_size
                
            elif emoji == '🔎':
                # ズームイン
                current_zoom += 1
                await update_graph(message, latex_expression, current_label_size, current_zoom)
                
            elif emoji == '🔭':
                # ズームアウト
                current_zoom -= 1
                await update_graph(message, latex_expression, current_label_size, current_zoom)
            
            # リアクションを削除
            await reaction.remove(user)
            
        except asyncio.TimeoutError:
            await message.clear_reactions()
            break
        except Exception as e:
            logger.error(f"リアクション処理エラー: {e}")
            break

async def update_graph(message, latex_expression, label_size, zoom_level):
    """グラフを更新"""
    try:
        # 新しいグラフを生成
        image_buffer = await gratex_bot.generate_graph(latex_expression, label_size, zoom_level)
        
        # 新しいファイルを作成
        file = discord.File(image_buffer, filename=f"gratex_graph_updated.png")
        
        # Embedを更新
        embed = discord.Embed(
            title="📊 GraTeX グラフ (更新済み)",
            description=f"**LaTeX式:** `{latex_expression}`\n**ラベルサイズ:** {label_size}\n**ズーム:** {zoom_level}",
            color=0x00ff00
        )
        embed.set_image(url="attachment://gratex_graph_updated.png")
        
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
