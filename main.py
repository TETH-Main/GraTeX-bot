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
            
            # Step 1: Desmosでグラフを作成してURLを取得
            desmos_url = await self.create_desmos_graph(latex_expression)
            logger.info(f"Desmos URL取得: {desmos_url}")
            
            # Step 2: GraTeXページに移動
            await self.page.goto('https://teth-main.github.io/GraTeX/?wide=true&credit=true')
            await self.page.wait_for_load_state('networkidle')
            
            # Step 3: DesmosのURLを入力
            await self.page.fill('#desmos-hash', desmos_url)
            
            # Step 4: ラベルサイズを設定
            if label_size in [1, 2, 2.5, 3, 4, 6, 8]:
                label_selects = await self.page.query_selector_all('select.form-control')
                if len(label_selects) >= 2:  # 2番目のselectがラベルサイズ
                    await label_selects[1].select_option(str(label_size))
            
            # Step 5: 画像サイズを設定（必要に応じて）
            # デフォルトは1920x1080で良い
            
            # Step 6: Generateボタンをクリック
            await self.page.click('#screenshot-button')
            
            # Step 7: 画像生成完了を待機
            await asyncio.sleep(5)  # 画像生成に時間がかかる場合があります
            
            # Step 8: 生成された画像を取得
            # GraTeXは生成後に画像をダウンロードリンクとして提供する可能性があります
            # まず、キャンバスから直接取得を試行
            image_data = await self.page.evaluate('''
                () => {
                    // GraTeXの結果キャンバスを探す
                    const canvas = document.querySelector('canvas.dcg-graph-inner');
                    if (canvas && canvas.width > 0 && canvas.height > 0) {
                        return canvas.toDataURL('image/png');
                    }
                    
                    // 他のキャンバス要素も確認
                    const allCanvas = document.querySelectorAll('canvas');
                    for (let c of allCanvas) {
                        if (c.width > 0 && c.height > 0) {
                            return c.toDataURL('image/png');
                        }
                    }
                    return null;
                }
            ''')
            
            if not image_data:
                raise Exception("画像の生成に失敗しました - キャンバスが見つからないか空です")
            
            # base64データを画像に変換
            image_bytes = base64.b64decode(image_data.split(',')[1])
            return io.BytesIO(image_bytes)
            
        except Exception as e:
            logger.error(f"グラフ生成エラー: {e}")
            raise
    
    async def create_desmos_graph(self, latex_expression):
        """Desmosでグラフを作成してURLまたはハッシュを取得"""
        try:
            # 新しいページを開いてDesmos電卓にアクセス
            desmos_page = await self.browser.new_page()
            await desmos_page.goto('https://www.desmos.com/calculator')
            await desmos_page.wait_for_load_state('networkidle')
            
            # LaTeX式を入力
            # Desmosの式入力エリアを探す
            expression_input = await desmos_page.wait_for_selector('.dcg-mq-editable-field', timeout=10000)
            
            # 式を入力
            await expression_input.click()
            await expression_input.type(latex_expression)
            
            # Enterキーを押して式を確定
            await expression_input.press('Enter')
            
            # 少し待機してグラフが描画されるのを待つ
            await asyncio.sleep(3)
            
            # Shareボタンを探してクリック（ハッシュ生成のため）
            try:
                share_button = await desmos_page.wait_for_selector('[aria-label="Share Graph"]', timeout=5000)
                await share_button.click()
                await asyncio.sleep(2)
                
                # Share URLを取得
                share_url_input = await desmos_page.wait_for_selector('input[readonly]', timeout=5000)
                share_url = await share_url_input.get_attribute('value')
                
                if share_url and '#' in share_url:
                    hash_value = share_url.split('#')[1]
                    await desmos_page.close()
                    return hash_value
                    
            except Exception as e:
                logger.warning(f"Shareボタンが見つからないかクリックできませんでした: {e}")
            
            # Shareボタンが使えない場合の代替方法: URLから直接ハッシュを取得
            current_url = desmos_page.url
            await desmos_page.close()
            
            if '#' in current_url:
                return current_url.split('#')[1]
            else:
                # ハッシュがない場合はDesmosのAPIを使用して簡易的なハッシュを作成
                # LaTeX式をDesmos形式に変換
                desmos_expression = self.latex_to_desmos(latex_expression)
                return f"expression={desmos_expression}"
                
        except Exception as e:
            logger.error(f"Desmosグラフ作成エラー: {e}")
            # フォールバック: LaTeX式をDesmos形式に変換
            desmos_expression = self.latex_to_desmos(latex_expression)
            return f"expression={desmos_expression}"
    
    def latex_to_desmos(self, latex_expression):
        """LaTeX式をDesmos形式に変換"""
        # 基本的な変換ルール
        desmos_expr = latex_expression.replace('\\', '')  # バックスラッシュを削除
        desmos_expr = desmos_expr.replace(' ', '')  # スペースを削除
        
        # 一般的な変換
        conversions = {
            'sin': 'sin',
            'cos': 'cos', 
            'tan': 'tan',
            'log': 'log',
            'ln': 'ln',
            'sqrt': 'sqrt',
            'pi': 'pi',
            'theta': 'theta',
            'le': '<=',
            'ge': '>=',
            'ne': '!=',
            'pm': '±'
        }
        
        for latex, desmos in conversions.items():
            desmos_expr = desmos_expr.replace(latex, desmos)
        
        return desmos_expr
    
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
        processing_msg = await ctx.send("🎨 Desmosでグラフを作成中...")
        
        # グラフ生成
        image_buffer = await gratex_bot.generate_graph(
            latex_expression, label_size, zoom_level
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
        embed.set_footer(text="Powered by Desmos + GraTeX")
        
        message = await ctx.send(file=file, embed=embed)
        
        # リアクションを追加（ズーム機能は削除、ラベルサイズのみ）
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
        embed.set_footer(text="Powered by Desmos + GraTeX")
        
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
