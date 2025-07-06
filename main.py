import os
import io, base64, discord, asyncio
from discord.ext import commands
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, WebDriverException

# webdriver_managerは条件付きでインポート
try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False
    print("webdriver-manager not available, using system ChromeDriver")

def create_driver():
    """Chrome WebDriverを作成する関数"""
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-plugins')
    options.add_argument('--remote-debugging-port=9222')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-web-security')
    options.add_argument('--allow-running-insecure-content')
    options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.headless = True
    
    # Railway/Docker環境でのChrome設定
    chrome_paths = [
        '/usr/bin/chromium',             # Docker/Chromium
        '/usr/bin/google-chrome',        # Google Chrome
        '/nix/store/*/bin/chromium',     # Nixpacks
        '/usr/bin/chromium-browser',     # Alternative
    ]
    
    chromedriver_paths = [
        '/usr/bin/chromedriver',         # Docker/System
        '/usr/local/bin/chromedriver',   # Custom install
        '/nix/store/*/bin/chromedriver', # Nixpacks
    ]
    
    # Chrome バイナリパスを探す
    chrome_binary = None
    for path in chrome_paths:
        if '*' in path:
            # Nixパターンのマッチング
            import glob
            matches = glob.glob(path)
            if matches and os.path.exists(matches[0]):
                chrome_binary = matches[0]
                break
        elif os.path.exists(path):
            chrome_binary = path
            break
    
    if chrome_binary:
        options.binary_location = chrome_binary
        print(f"Using Chrome binary: {chrome_binary}")
    else:
        print("Chrome binary not found, using default")
    
    # ChromeDriver パスを探す
    chromedriver_path = None
    for path in chromedriver_paths:
        if '*' in path:
            import glob
            matches = glob.glob(path)
            if matches and os.path.exists(matches[0]):
                chromedriver_path = matches[0]
                break
        elif os.path.exists(path):
            chromedriver_path = path
            break
    
    try:
        if chromedriver_path:
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=options)
            print(f"WebDriver created with driver: {chromedriver_path}")
        else:
            # webdriver-managerを使用
            if WEBDRIVER_MANAGER_AVAILABLE:
                try:
                    chromedriver_path = ChromeDriverManager().install()
                    service = Service(chromedriver_path)
                    driver = webdriver.Chrome(service=service, options=options)
                    print(f"WebDriver created with webdriver-manager: {chromedriver_path}")
                except Exception as wm_error:
                    print(f"webdriver-manager failed: {wm_error}")
                    # 最後の手段：デフォルト
                    driver = webdriver.Chrome(options=options)
                    print("WebDriver created with default settings")
            else:
                # 最後の手段：デフォルト
                driver = webdriver.Chrome(options=options)
                print("WebDriver created with default settings")
        
        return driver
    except Exception as e:
        print(f"WebDriver creation error: {e}")
        raise e

# グローバル変数として初期化は後で行う
driver = None

def initialize_driver():
    """WebDriverを初期化する関数"""
    global driver
    if driver is None:
        driver = create_driver()
        driver.get('https://teth-main.github.io/GraTeX/?wide=true&credit=true')
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "dcg-tap-container")))
        print("WebDriver initialized successfully")


async def generate_img(latex, labelSize='4', zoomLevel=0):
    global driver
    
    # ドライバーが初期化されていない場合は初期化
    if driver is None:
        initialize_driver()

    if (driver.find_element(By.CLASS_NAME,
                            "dcg-action-zoomrestore").is_displayed()):
        driver.find_element(By.CLASS_NAME, "dcg-action-zoomrestore").click()
    if (zoomLevel > 0):
        for i in range(zoomLevel):
            driver.find_element(By.CLASS_NAME, "dcg-action-zoomin").click()
    if (zoomLevel < 0):
        for i in range(-zoomLevel):
            driver.find_element(By.CLASS_NAME, "dcg-action-zoomout").click()

    Select(
        driver.find_element(By.NAME, "labelSize").find_element(
            By.NAME, "labelSize")).select_by_value(labelSize)
    driver.execute_script("calculator.removeExpression({id:'3'});")
    driver.execute_script(
        "calculator.setExpression({id:'1', latex: String.raw`" + latex +
        "`, color:'black'});")
    await asyncio.sleep(5)
    driver.find_element(By.ID, "screenshot-button").click()

    try:
        WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.ID, "generate-container")))
    except TimeoutException:
        driver.execute_script("calculator.removeExpression({id:'1'});")
        return "error"
    driver.execute_script("calculator.removeExpression({id:'1'});")

    img_data = driver.find_element(By.ID, "preview").get_attribute("src")
    return img_data[21:]


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# スラッシュコマンド用のTree
tree = bot.tree


async def waitReaction(ctx_or_interaction, message, arg, labelSize, zoomLevel):
  # ctx_or_interactionがInteractionかContextかを判定
  if hasattr(ctx_or_interaction, 'user'):
    # Interaction
    user = ctx_or_interaction.user
  else:
    # Context
    user = ctx_or_interaction.author

  def check(reaction, reaction_user):
    return reaction_user == user and str(reaction.emoji) in [
      '1⃣', '2⃣', '3⃣', '4⃣', '6⃣', '8⃣', '🔎', '🔭', '✅', '🚮'
    ]

  try:
    reaction, reaction_user = await bot.wait_for('reaction_add',
                                        timeout=20.0,
                                        check=check)
  except asyncio.TimeoutError:
    await message.clear_reactions()
    return
  else:
    if (str(reaction.emoji) == '✅'):
      await message.clear_reactions()
      return

    if (str(reaction.emoji) == '🚮'):
      await message.delete()
      return

    if (str(reaction.emoji) == '🔎'):
      zoomLevel += 1
    if (str(reaction.emoji) == '🔭'):
      zoomLevel -= 1

    if (str(reaction.emoji) in ['1⃣', '2⃣', '3⃣', '4⃣', '6⃣', '8⃣']):
      labelSize = str(reaction.emoji)[0]

    await reaction.remove(reaction_user)
    
    # メッセージ更新処理
    try:
      img_data = await generate_img(arg, labelSize, zoomLevel)
      await message.edit(attachments=[
        discord.File(io.BytesIO(base64.b64decode(img_data)),
                     f'GraTeX zoom {zoomLevel}.png')
      ])
    except Exception as e:
      print(f"Error updating image: {e}")
    
    await waitReaction(ctx_or_interaction, message, arg, labelSize, zoomLevel)


@bot.event
async def on_ready():
    print('GraTeX bot is ready!')
    # Bot起動時にWebDriverを初期化
    try:
        initialize_driver()
        print('WebDriver initialized on bot startup')
    except Exception as e:
        print(f'Error initializing WebDriver: {e}')
    
    # スラッシュコマンドを同期
    try:
        synced = await tree.sync()
        print(f'Synced {len(synced)} slash commands')
    except Exception as e:
        print(f'Failed to sync slash commands: {e}')


# ヘルプ用のEmbed作成関数
def create_help_embed():
    embed = discord.Embed(
        title="🧮 GraTeX Bot - Help",
        description="Generate mathematical graphs from LaTeX formulas with interactive controls",
        color=0x00ff00
    )
    
    embed.add_field(
        name="📖 Basic Usage",
        value='`/gratex formula:"latex_formula"`\nor\n`!gratex "latex_formula"`\n\n**Example:**\n`/gratex formula:"\\cos x\\le\\cos y"`',
        inline=False
    )
    
    embed.add_field(
        name="🎛️ Interactive Controls",
        value="2⃣3⃣4⃣6⃣ : Change label size\n🔎 : Zoom in\n🔭 : Zoom out\n✅ : Complete editing\n🚮 : Delete message",
        inline=False
    )
    
    embed.add_field(
        name="⚙️ Advanced Usage",
        value='`/gratex formula:"latex" label_size:4 zoom_level:0`\n\n**Parameters:**\n• label_size: 1, 2, 3, 4, 6, 8\n• zoom_level: integer value',
        inline=False
    )
    
    embed.add_field(
        name="⏱️ Note",
        value="If no response for 20 seconds, editing automatically completes",
        inline=False
    )
    
    embed.set_footer(text="Powered by GraTeX | Made with ❤️")
    
    return embed


# スラッシュコマンド定義
@tree.command(name="gratex", description="Generate mathematical graphs from LaTeX formulas")
async def gratex_slash(
    interaction: discord.Interaction,
    formula: str,
    label_size: int = 4,
    zoom_level: int = 0
):
    # パラメータ検証
    if label_size not in [1, 2, 3, 4, 6, 8]:
        await interaction.response.send_message(
            '❌ **Invalid label size!**\nLabel size must be one of: 1, 2, 3, 4, 6, 8\n\nUse `/gratex help` for more information.',
            ephemeral=True
        )
        return
    
    if not isinstance(zoom_level, int):
        await interaction.response.send_message(
            '❌ **Invalid zoom level!**\nZoom level must be an integer\n\nUse `/gratex help` for more information.',
            ephemeral=True
        )
        return

    # "help"チェック
    if formula.lower() == "help":
        embed = create_help_embed()
        await interaction.response.send_message(embed=embed)
        return
    
    # 処理中メッセージ
    await interaction.response.defer()
    
    try:
        # 画像生成
        img_data = await generate_img(
            formula.translate(str.maketrans('', '', '`')), 
            str(label_size), 
            zoom_level
        )
        
        if img_data == "error":
            await interaction.followup.send(
                '❌ **The graph could not be generated.**\nPlease enter a simpler formula and try again.'
            )
            return

        # 画像送信
        reply = await interaction.followup.send(
            file=discord.File(
                io.BytesIO(base64.b64decode(img_data)), 
                'GraTeX.png'
            )
        )
        
        # リアクション追加
        await reply.add_reaction('2⃣')
        await reply.add_reaction('3⃣')
        await reply.add_reaction('4⃣')
        await reply.add_reaction('6⃣')
        await reply.add_reaction('🔎')
        await reply.add_reaction('🔭')
        await reply.add_reaction('✅')
        await reply.add_reaction('🚮')
        
        # リアクション待機
        await waitReaction(interaction, reply, formula, str(label_size), zoom_level)
        
    except Exception as e:
        print(f"Error in slash command: {e}")
        await interaction.followup.send(
            '❌ **An error occurred while generating the graph.**\nPlease try again later.'
        )


# 従来のプレフィックスコマンド（後方互換性のため）
@bot.command()
async def gratex(ctx, arg, labelSize='4', zoomLevel=0):
  if (arg == "help"):
    embed = create_help_embed()
    await ctx.send(embed=embed)
    return

  if (not labelSize in ['1', '2', '3', '4', '6', '8']):
    await ctx.send(
      '❌ **Wrong command!**\n\nPlease type `!gratex help` or `/gratex help` to confirm the command.')
    return

  if (not isinstance(zoomLevel, int)):
    await ctx.send(
      '❌ **Wrong command!**\n\nPlease type `!gratex help` or `/gratex help` to confirm the command.')
    return

  async with ctx.typing():
    img_data = await generate_img(arg.translate(str.maketrans('', '',
                                                              '`')), labelSize,
                                  zoomLevel)  #removes extra msg bits
    if (img_data == "error"):
      await ctx.send(
        '❌ **The graph could not be generated.**\nPlease enter a simpler formula and try again.'
      )
      return

    reply = await ctx.send(file=discord.File(
      io.BytesIO(base64.b64decode(img_data)), 'GraTeX.png'))  #sends image
  #await reply.add_reaction('1⃣')
  await reply.add_reaction('2⃣')
  await reply.add_reaction('3⃣')
  await reply.add_reaction('4⃣')
  await reply.add_reaction('6⃣')
  #await reply.add_reaction('8⃣')
  await reply.add_reaction('🔎')
  await reply.add_reaction('🔭')
  await reply.add_reaction('✅')
  await reply.add_reaction('🚮')
  await waitReaction(ctx, reply, arg, labelSize, zoomLevel)


if __name__ == "__main__":
    # Railwayの環境変数からトークンを取得
    token = os.getenv("TOKEN")
    if not token:
        raise ValueError("TOKEN environment variable is not set")
    
    try:
        bot.run(token)
    except Exception as e:
        print(f"Bot error: {e}")
    finally:
        # クリーンアップ
        if driver:
            try:
                driver.quit()
                print("WebDriver closed")
            except:
                pass
