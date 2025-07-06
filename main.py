import discord
from discord.ext import commands
from discord import app_commands
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

# Bot設定（スラッシュコマンド専用）
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=None, intents=intents)

class GraTeXBot:
    def __init__(self):
        self.browser = None
        self.page = None
        self.current_zoom_level = 0  # ズームレベルを追跡
        
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
    
    async def generate_graph(self, latex_expression, label_size=4, zoom_level=0):
        """LaTeX式からグラフ画像を生成（GraTeX内部API使用）"""
        try:
            if not self.page:
                await self.initialize_browser()
            
            # 現在のURLがGraTeXでない場合は移動
            current_url = self.page.url
            if 'teth-main.github.io/GraTeX' not in current_url:
                await self.page.goto('https://teth-main.github.io/GraTeX/?wide=true&credit=true')
                await self.page.wait_for_load_state('networkidle')
            
            # 2Dモードを確実にする
            await self.switch_to_2d_mode()
            
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
            
            # ズームレベルを適用
            if zoom_level != 0:
                await self.apply_zoom_level(zoom_level)
            
            # 現在のズームレベルを更新
            self.current_zoom_level = zoom_level
            
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
    
    async def generate_3d_graph(self, latex_expression, label_size=4, zoom_level=0):
        """LaTeX式から3Dグラフ画像を生成（GraTeX内部API使用）"""
        try:
            if not self.page:
                await self.initialize_browser()
            
            # 現在のURLがGraTeXでない場合は移動
            current_url = self.page.url
            if 'teth-main.github.io/GraTeX' not in current_url:
                await self.page.goto('https://teth-main.github.io/GraTeX/?wide=true&credit=true')
                await self.page.wait_for_load_state('networkidle')
            
            # 3Dモードに切り替え
            logger.info("3Dモードに切り替え中...")
            three_d_label = await self.page.query_selector('label[for="version-3d"]')
            if three_d_label:
                await three_d_label.click()
                await asyncio.sleep(2)  # 切り替え完了を待機
            else:
                raise Exception("3D切り替えボタンが見つかりません")
            
            # GraTeX.calculator3Dが利用可能になるまで待機
            await self.page.wait_for_function(
                "() => window.GraTeX && window.GraTeX.calculator3D",
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
            
            # LaTeX式をGraTeX Calculator 3D APIで直接設定
            logger.info(f"3D LaTeX式を設定: {latex_expression}")
            await self.page.evaluate(f"""
                () => {{
                    if (window.GraTeX && window.GraTeX.calculator3D) {{
                        window.GraTeX.calculator3D.setBlank();
                        window.GraTeX.calculator3D.setExpression({{latex: `{latex_expression}`}});
                        console.log("3D数式を設定しました:", `{latex_expression}`);
                    }} else {{
                        throw new Error("GraTeX.calculator3D が利用できません");
                    }}
                }}
            """)
            
            # 3Dズームレベルを適用（必要に応じて将来実装）
            if zoom_level != 0:
                logger.info(f"3Dズームレベル {zoom_level} は現在未実装です")
            
            # 現在のズームレベルを更新
            self.current_zoom_level = zoom_level
            
            # 少し待機してグラフが描画されるのを待つ
            await asyncio.sleep(3)
            
            # Generateボタンをクリック
            logger.info("3Dスクリーンショットボタンをクリック...")
            await self.page.click('#screenshot-button')
            
            # 画像生成完了を待機 - id="preview"のimgタグが更新されるまで待つ
            logger.info("3D画像生成を待機中...")
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
                logger.warning("3D preview imgから画像を取得できませんでした。キャンバスから取得を試行...")
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
                raise Exception("3D画像の生成に失敗しました - preview imgもキャンバスも見つかりません")
            
            logger.info("✅ 3D画像データの取得に成功!")
            
            # base64データを画像に変換
            image_bytes = base64.b64decode(image_data.split(',')[1])
            return io.BytesIO(image_bytes)
            
        except Exception as e:
            logger.error(f"3Dグラフ生成エラー: {e}")
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
            # 現在のズームレベルを取得
            old_zoom_level = self.current_zoom_level
            
            # ズームレベルを更新
            if zoom_direction == 'in':
                new_zoom_level = self.current_zoom_level + 1
            else:
                new_zoom_level = self.current_zoom_level - 1
            
            # ズームレベルを制限範囲内に収める
            new_zoom_level = max(-3, min(3, new_zoom_level))
            
            # 制限に達している場合は何もしない
            if new_zoom_level == old_zoom_level:
                logger.info(f"ズームレベルが制限に達しています: {new_zoom_level}")
                return False
            
            self.current_zoom_level = new_zoom_level
            logger.info(f"新しいズームレベル: {self.current_zoom_level}")
            
            # 新しいズームレベルを適用
            result = await self.apply_zoom_level(self.current_zoom_level)
            
            # ズーム操作後に少し待機
            await asyncio.sleep(1)
            
            return result
            
        except Exception as e:
            logger.error(f"Desmosズーム操作エラー: {e}")
            return False

    async def apply_zoom_level(self, zoom_level):
        """指定されたズームレベルを適用"""
        try:
            # ズームレベルの制限
            zoom_level = max(-3, min(3, zoom_level))
            
            # ベース範囲（zoom_level = 0の場合）
            base_range = 10
            
            # ズームレベルに基づいて範囲を計算
            # zoom_level > 0: 拡大（範囲を小さく）
            # zoom_level < 0: 縮小（範囲を大きく）
            if zoom_level > 0:
                # 拡大：各レベルで範囲を半分にする
                range_size = base_range / (2 ** zoom_level)
            elif zoom_level < 0:
                # 縮小：各レベルで範囲を2倍にする
                range_size = base_range * (2 ** abs(zoom_level))
            else:
                range_size = base_range
            
            logger.info(f"ズームレベル {zoom_level} を適用: 範囲 ±{range_size}")
            
            # ビューポートを設定
            result = await self.page.evaluate(f'''
                () => {{
                    if (window.GraTeX && window.GraTeX.calculator2D) {{
                        try {{
                            window.GraTeX.calculator2D.setMathBounds({{
                                left: -{range_size},
                                right: {range_size},
                                bottom: -{range_size/2},
                                top: {range_size/2}
                            }});
                            console.log("ズームレベル適用完了");
                            return true;
                        }} catch (e) {{
                            console.error("ズームレベル適用エラー:", e);
                            return false;
                        }}
                    }}
                    return false;
                }}
            ''')
            
            return result
            
        except Exception as e:
            logger.error(f"ズームレベル適用エラー: {e}")
            return False

    async def switch_to_2d_mode(self):
        """2Dモードに切り替え"""
        try:
            if not self.page:
                await self.initialize_browser()
            
            logger.info("2Dモードに切り替え中...")
            two_d_label = await self.page.query_selector('label[for="version-2d"]')
            if two_d_label:
                await two_d_label.click()
                await asyncio.sleep(2)  # 切り替え完了を待機
                logger.info("✅ 2Dモードに切り替え完了")
                return True
            else:
                logger.warning("2D切り替えボタンが見つかりません")
                return False
                
        except Exception as e:
            logger.error(f"2Dモード切り替えエラー: {e}")
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
        
        # スラッシュコマンドを同期
        try:
            synced = await bot.tree.sync()
            logger.info(f"スラッシュコマンド同期完了: {len(synced)} コマンド")
        except Exception as e:
            logger.error(f"スラッシュコマンド同期エラー: {e}")
            
    except Exception as e:
        logger.error(f"初期化エラー: {e}")

@bot.tree.command(name="gratex", description="LaTeX式からグラフを生成します")
@app_commands.describe(
    latex="LaTeX式またはDesmos記法の数式（例: y = sin(x), z = x^2 + y^2）",
    mode="グラフの種類（2D または 3D）",
    label_size="軸ラベルのサイズ",
    zoom_level="ズームレベル（2Dのみ、-3～3）"
)
@app_commands.choices(
    mode=[
        app_commands.Choice(name="2D グラフ", value="2d"),
        app_commands.Choice(name="3D グラフ", value="3d")
    ],
    label_size=[
        app_commands.Choice(name="極小 (1)", value=1),
        app_commands.Choice(name="小 (2)", value=2),
        app_commands.Choice(name="中小 (3)", value=3),
        app_commands.Choice(name="標準 (4)", value=4),
        app_commands.Choice(name="大 (6)", value=6),
        app_commands.Choice(name="極大 (8)", value=8)
    ],
    zoom_level=[
        app_commands.Choice(name="縮小 -3", value=-3),
        app_commands.Choice(name="縮小 -2", value=-2),
        app_commands.Choice(name="縮小 -1", value=-1),
        app_commands.Choice(name="標準 0", value=0),
        app_commands.Choice(name="拡大 +1", value=1),
        app_commands.Choice(name="拡大 +2", value=2),
        app_commands.Choice(name="拡大 +3", value=3)
    ]
)
async def gratex_slash(
    interaction: discord.Interaction, 
    latex: str, 
    mode: str = "2d",
    label_size: int = 4, 
    zoom_level: int = 0
):
    """
    スラッシュコマンド: LaTeX式からグラフを生成
    
    Parameters:
    - latex: LaTeX式またはDesmos記法の数式
    - mode: グラフモード（"2d" または "3d"）
    - label_size: ラベルサイズ（1, 2, 3, 4, 6, 8）
    - zoom_level: ズームレベル（2Dのみ、負数で縮小、正数で拡大）
    """
    
    # パラメータ検証
    if mode.lower() not in ["2d", "3d"]:
        await interaction.response.send_message("❌ モードは '2d' または '3d' を指定してください", ephemeral=True)
        return
    
    if label_size not in [1, 2, 3, 4, 6, 8]:
        await interaction.response.send_message("❌ ラベルサイズは 1, 2, 3, 4, 6, 8 のいずれかを指定してください", ephemeral=True)
        return
    
    if not latex.strip():
        await interaction.response.send_message("❌ LaTeX式を入力してください", ephemeral=True)
        return
    
    # 3Dモードの場合はzoom_levelを無視
    if mode.lower() == "3d" and zoom_level != 0:
        await interaction.response.send_message("ℹ️ 3Dモードではズームレベルは無視されます", ephemeral=True)
        zoom_level = 0
    
    if mode.lower() == "2d" and (zoom_level < -3 or zoom_level > 3):
        await interaction.response.send_message("❌ ズームレベルは -3 から 3 の範囲で指定してください", ephemeral=True)
        return
    
    try:
        # 処理中メッセージ
        mode_text = "2D" if mode.lower() == "2d" else "3D"
        await interaction.response.send_message(f"🎨 GraTeXで{mode_text}グラフを生成中...")
        
        # モードに応じてグラフ生成
        if mode.lower() == "2d":
            image_buffer = await gratex_bot.generate_graph(latex, label_size, zoom_level)
            
            # ズームレベル情報
            zoom_info = ""
            if zoom_level > 0:
                zoom_info = f" (拡大 x{2**zoom_level})"
            elif zoom_level < 0:
                zoom_info = f" (縮小 x{2**abs(zoom_level)})"
            
            # 結果を送信
            embed = discord.Embed(
                title="📊 GraTeX 2Dグラフ",
                description=f"**LaTeX式:** `{latex}`\n**ラベルサイズ:** {label_size}\n**ズームレベル:** {zoom_level}{zoom_info}",
                color=0x00ff00
            )
            embed.set_footer(text="Powered by GraTeX 2D")
            
            # リアクションを追加（2D用）
            reactions = ['1⃣', '2⃣', '3⃣', '4⃣', '6⃣', '8⃣', '🔍', '🔭', '✅', '🚮']
            
        else:  # 3Dモード
            image_buffer = await gratex_bot.generate_3d_graph(latex, label_size)
            
            # 結果を送信
            embed = discord.Embed(
                title="📊 GraTeX 3Dグラフ",
                description=f"**LaTeX式:** `{latex}`\n**ラベルサイズ:** {label_size}\n**モード:** 3D",
                color=0x0099ff
            )
            embed.set_footer(text="Powered by GraTeX 3D")
            
            # リアクションを追加（3D用）
            reactions = ['1⃣', '2⃣', '3⃣', '4⃣', '6⃣', '8⃣', '🔄', '✅', '🚮']
        
        # Discord画像ファイルを作成
        file = discord.File(image_buffer, filename=f"gratex_{mode.lower()}_graph.png")
        embed.set_image(url=f"attachment://gratex_{mode.lower()}_graph.png")
        
        # フォローアップメッセージで画像を送信
        message = await interaction.followup.send(file=file, embed=embed)
        
        # リアクションを追加
        for reaction in reactions:
            await message.add_reaction(reaction)
        
        # リアクション処理を設定
        if mode.lower() == "2d":
            await setup_reaction_handler_slash(interaction, message, latex, label_size)
        else:
            await setup_reaction_handler_3d(interaction, message, latex, label_size)
        
    except Exception as e:
        logger.error(f"{mode_text}グラフ生成エラー: {e}")
        await interaction.followup.send(f"❌ {mode_text}グラフの生成に失敗しました: {str(e)}")

async def setup_reaction_handler_slash(interaction, message, latex_expression, current_label_size):
    """スラッシュコマンド用のリアクション処理のセットアップ"""
    
    def check(reaction, user):
        return (
            user == interaction.user and 
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
                    await update_graph_slash(message, latex_expression, new_label_size)
                    current_label_size = new_label_size
                    
            elif emoji == '🔍':
                # 拡大（ズームイン）
                await zoom_graph_slash(message, latex_expression, current_label_size, 'in')
                
            elif emoji == '🔭':
                # 縮小（ズームアウト）
                await zoom_graph_slash(message, latex_expression, current_label_size, 'out')
            
            # リアクションを削除
            await reaction.remove(user)
            
        except asyncio.TimeoutError:
            await message.clear_reactions()
            break
        except Exception as e:
            logger.error(f"リアクション処理エラー: {e}")
            break

async def update_graph_slash(message, latex_expression, label_size):
    """スラッシュコマンド用: グラフを更新"""
    try:
        # 新しいグラフを生成（現在のズームレベルを維持）
        image_buffer = await gratex_bot.generate_graph(latex_expression, label_size, gratex_bot.current_zoom_level)
        
        # 新しいファイルを作成
        file = discord.File(image_buffer, filename=f"gratex_graph_updated.png")
        
        # ズームレベル情報
        zoom_info = ""
        if gratex_bot.current_zoom_level > 0:
            zoom_info = f" (拡大 x{2**gratex_bot.current_zoom_level})"
        elif gratex_bot.current_zoom_level < 0:
            zoom_info = f" (縮小 x{2**abs(gratex_bot.current_zoom_level)})"
        
        # Embedを更新
        embed = discord.Embed(
            title="📊 GraTeX グラフ (更新済み)",
            description=f"**LaTeX式:** `{latex_expression}`\n**ラベルサイズ:** {label_size}\n**ズームレベル:** {gratex_bot.current_zoom_level}{zoom_info}",
            color=0x00ff00
        )
        embed.set_image(url="attachment://gratex_graph_updated.png")
        embed.set_footer(text="Powered by GraTeX")
        
        # メッセージを編集
        await message.edit(attachments=[file], embed=embed)
        
    except Exception as e:
        logger.error(f"グラフ更新エラー: {e}")

async def zoom_graph_slash(message, latex_expression, label_size, zoom_direction):
    """スラッシュコマンド用: グラフをズームイン/アウトして更新"""
    try:
        # ズーム操作を実行
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
            
            # ズームレベル情報
            zoom_info = ""
            if gratex_bot.current_zoom_level > 0:
                zoom_info = f" (拡大 x{2**gratex_bot.current_zoom_level})"
            elif gratex_bot.current_zoom_level < 0:
                zoom_info = f" (縮小 x{2**abs(gratex_bot.current_zoom_level)})"
            
            # Embedを更新
            embed = discord.Embed(
                title=f"📊 GraTeX グラフ ({zoom_text}済み)",
                description=f"**LaTeX式:** `{latex_expression}`\n**ラベルサイズ:** {label_size}\n**ズームレベル:** {gratex_bot.current_zoom_level}{zoom_info}",
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

async def update_graph(message, latex_expression, label_size):
    """レガシー用: グラフを更新（下位互換性のため保持）"""
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
async def on_disconnect():
    """Bot切断時のクリーンアップ"""
    await gratex_bot.close()

async def setup_reaction_handler_3d(interaction, message, latex_expression, current_label_size):
    """3D用のリアクション処理のセットアップ"""
    
    def check(reaction, user):
        return (
            user == interaction.user and 
            reaction.message.id == message.id and
            str(reaction.emoji) in ['1⃣', '2⃣', '3⃣', '4⃣', '6⃣', '8⃣', '🔄', '✅', '🚮']
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
                    await update_3d_graph(message, latex_expression, new_label_size)
                    current_label_size = new_label_size
            
            elif emoji == '🔄':
                # 3Dグラフを再生成（視点をリセット）
                await update_3d_graph(message, latex_expression, current_label_size)
            
            # リアクションを削除
            await reaction.remove(user)
            
        except asyncio.TimeoutError:
            await message.clear_reactions()
            break
        except Exception as e:
            logger.error(f"3Dリアクション処理エラー: {e}")
            break

async def update_3d_graph(message, latex_expression, label_size):
    """3D用: グラフを更新"""
    try:
        # 新しい3Dグラフを生成
        image_buffer = await gratex_bot.generate_3d_graph(latex_expression, label_size)
        
        # 新しいファイルを作成
        file = discord.File(image_buffer, filename=f"gratex_3d_graph_updated.png")
        
        # Embedを更新
        embed = discord.Embed(
            title="📊 GraTeX 3Dグラフ (更新済み)",
            description=f"**LaTeX式:** `{latex_expression}`\n**ラベルサイズ:** {label_size}\n**モード:** 3D",
            color=0x0099ff
        )
        embed.set_image(url="attachment://gratex_3d_graph_updated.png")
        embed.set_footer(text="Powered by GraTeX 3D")
        
        # メッセージを編集
        await message.edit(attachments=[file], embed=embed)
        
    except Exception as e:
        logger.error(f"3Dグラフ更新エラー: {e}")

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
