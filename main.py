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
    
    # 基本設定
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-plugins')
    options.add_argument('--remote-debugging-port=9222')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-web-security')
    options.add_argument('--allow-running-insecure-content')
    
    # ユーザーデータディレクトリの競合を回避
    import tempfile
    import uuid
    temp_dir = tempfile.gettempdir()
    unique_user_data_dir = f"{temp_dir}/chrome_user_data_{uuid.uuid4()}"
    options.add_argument(f'--user-data-dir={unique_user_data_dir}')
    print(f"Using unique user data directory: {unique_user_data_dir}")
    
    # 追加の安定性設定
    options.add_argument('--disable-background-timer-throttling')
    options.add_argument('--disable-backgrounding-occluded-windows')
    options.add_argument('--disable-renderer-backgrounding')
    options.add_argument('--disable-features=TranslateUI')
    options.add_argument('--disable-ipc-flooding-protection')
    options.add_argument('--single-process')
    
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
        print("Creating new WebDriver instance...")
        driver = create_driver()
        print("Loading GraTeX website...")
        driver.get('https://teth-main.github.io/GraTeX/?wide=true&credit=true')
        print("Waiting for page to load...")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CLASS_NAME, "dcg-tap-container")))
        print("WebDriver initialized successfully")
    else:
        print("WebDriver already initialized")


def cleanup_driver():
    """WebDriverをクリーンアップする関数"""
    global driver
    if driver:
        try:
            driver.quit()
            print("WebDriver closed successfully")
        except Exception as e:
            print(f"Error closing WebDriver: {e}")
        finally:
            driver = None


async def generate_img(latex, labelSize='4', zoomLevel=0):
    print(f"=== generate_img called ===")
    print(f"LaTeX: {latex}")
    print(f"Label size: {labelSize}")
    print(f"Zoom level: {zoomLevel}")
    
    global driver
    
    # ドライバーが初期化されていない場合は初期化
    if driver is None:
        print("Driver not initialized, initializing...")
        try:
            initialize_driver()
        except Exception as e:
            print(f"Failed to initialize driver: {e}")
            return "error"

    try:
        print("Checking current page...")
        current_url = driver.current_url
        print(f"Current URL: {current_url}")
        
        # ページが正しく読み込まれているかチェック
        if "GraTeX" not in current_url:
            print("Reloading GraTeX page...")
            driver.get('https://teth-main.github.io/GraTeX/?wide=true&credit=true')
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CLASS_NAME, "dcg-tap-container")))
        
        print("Checking zoom restore button...")
        zoom_restore = driver.find_elements(By.CLASS_NAME, "dcg-action-zoomrestore")
        if zoom_restore and zoom_restore[0].is_displayed():
            zoom_restore[0].click()
            print("Zoom restore clicked")
            
        print(f"Setting zoom level to {zoomLevel}...")
        if (zoomLevel > 0):
            for i in range(zoomLevel):
                zoom_in_buttons = driver.find_elements(By.CLASS_NAME, "dcg-action-zoomin")
                if zoom_in_buttons:
                    zoom_in_buttons[0].click()
                    print(f"Zoom in {i+1}/{zoomLevel}")
                    await asyncio.sleep(0.5)  # 少し待機
        if (zoomLevel < 0):
            for i in range(-zoomLevel):
                zoom_out_buttons = driver.find_elements(By.CLASS_NAME, "dcg-action-zoomout")
                if zoom_out_buttons:
                    zoom_out_buttons[0].click()
                    print(f"Zoom out {i+1}/{-zoomLevel}")
                    await asyncio.sleep(0.5)  # 少し待機

        print(f"Setting label size to {labelSize}...")
        try:
            label_selects = driver.find_elements(By.NAME, "labelSize")
            if label_selects:
                Select(label_selects[0]).select_by_value(labelSize)
                print("Label size set")
            else:
                print("Label size selector not found")
        except Exception as e:
            print(f"Error setting label size: {e}")
        
        print("Removing old expression...")
        driver.execute_script("calculator.removeExpression({id:'3'});")
        
        print(f"Setting new expression: {latex}")
        # JavaScriptエスケープを改善
        escaped_latex = latex.replace('\\', '\\\\').replace('`', '\\`')
        driver.execute_script(
            f"calculator.setExpression({{id:'1', latex: String.raw`{escaped_latex}`, color:'black'}});")
        
        print("Waiting 5 seconds...")
        await asyncio.sleep(5)
        
        print("Clicking screenshot button...")
        screenshot_buttons = driver.find_elements(By.ID, "screenshot-button")
        if screenshot_buttons:
            screenshot_buttons[0].click()
        else:
            print("Screenshot button not found")
            return "error"

        try:
            print("Waiting for generation container...")
            WebDriverWait(driver, 30).until(
                EC.visibility_of_element_located((By.ID, "generate-container")))
            print("Generation container found")
        except TimeoutException:
            print("Timeout waiting for generation container")
            driver.execute_script("calculator.removeExpression({id:'1'});")
            return "error"
            
        print("Removing expression...")
        driver.execute_script("calculator.removeExpression({id:'1'});")

        print("Getting image data...")
        preview_elements = driver.find_elements(By.ID, "preview")
        if preview_elements:
            img_data = preview_elements[0].get_attribute("src")
            print(f"Image data length: {len(img_data) if img_data else 'None'}")
            
            if img_data and len(img_data) > 21:
                result = img_data[22:]  # "data:image/png;base64," を除去
                print(f"Returning image data, length: {len(result)}")
                return result
            else:
                print("Invalid image data")
                return "error"
        else:
            print("Preview element not found")
            return "error"
            
    except Exception as e:
        print(f"Error in generate_img: {e}")
        import traceback
        traceback.print_exc()
        
        # エラー時にドライバーを再初期化
        print("Attempting to reinitialize driver due to error...")
        cleanup_driver()
        try:
            initialize_driver()
            print("Driver reinitialized successfully")
        except Exception as reinit_error:
            print(f"Failed to reinitialize driver: {reinit_error}")
        
        return "error"


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# スラッシュコマンド用のTree
tree = bot.tree

print("Bot instance created with intents and tree initialized")


async def waitReaction(ctx_or_interaction, message, arg, labelSize, zoomLevel):
  print(f"waitReaction called with arg: {arg}, labelSize: {labelSize}, zoomLevel: {zoomLevel}")
  
  # ctx_or_interactionがInteractionかContextかを判定
  if hasattr(ctx_or_interaction, 'user'):
    # Interaction
    user = ctx_or_interaction.user
    print(f"Using Interaction user: {user}")
  else:
    # Context
    user = ctx_or_interaction.author
    print(f"Using Context author: {user}")

  def check(reaction, reaction_user):
    result = reaction_user == user and str(reaction.emoji) in [
      '1⃣', '2⃣', '3⃣', '4⃣', '6⃣', '8⃣', '🔎', '🔭', '✅', '🚮'
    ]
    print(f"Reaction check: user={reaction_user}, emoji={reaction.emoji}, result={result}")
    return result

  try:
    print("Waiting for reaction...")
    reaction, reaction_user = await bot.wait_for('reaction_add',
                                        timeout=20.0,
                                        check=check)
    print(f"Reaction received: {reaction.emoji} from {reaction_user}")
  except asyncio.TimeoutError:
    print("Reaction timeout, clearing reactions")
    await message.clear_reactions()
    return
  else:
    if (str(reaction.emoji) == '✅'):
      print("Complete reaction received")
      await message.clear_reactions()
      return

    if (str(reaction.emoji) == '🚮'):
      print("Delete reaction received")
      await message.delete()
      return

    if (str(reaction.emoji) == '🔎'):
      zoomLevel += 1
      print(f"Zoom in: new zoom level = {zoomLevel}")
    if (str(reaction.emoji) == '🔭'):
      zoomLevel -= 1
      print(f"Zoom out: new zoom level = {zoomLevel}")

    if (str(reaction.emoji) in ['1⃣', '2⃣', '3⃣', '4⃣', '6⃣', '8⃣']):
      labelSize = str(reaction.emoji)[0]
      print(f"Label size changed to: {labelSize}")

    await reaction.remove(reaction_user)
    
    # メッセージ更新処理
    try:
      print(f"Generating new image with labelSize={labelSize}, zoomLevel={zoomLevel}")
      img_data = await generate_img(arg, labelSize, zoomLevel)
      if img_data == "error":
        print("Image generation returned error")
        return
      
      print("Updating message with new image")
      await message.edit(attachments=[
        discord.File(io.BytesIO(base64.b64decode(img_data)),
                     f'GraTeX zoom {zoomLevel}.png')
      ])
      print("Message updated successfully")
    except Exception as e:
      print(f"Error updating image: {e}")
      return
    
    await waitReaction(ctx_or_interaction, message, arg, labelSize, zoomLevel)


@bot.event
async def on_ready():
    print('=== GraTeX bot is starting up ===')
    print(f'Bot user: {bot.user}')
    print(f'Bot ID: {bot.user.id}')
    print(f'Bot guilds: {len(bot.guilds)}')
    
    # Bot起動時にWebDriverを初期化
    try:
        print('Initializing WebDriver...')
        initialize_driver()
        print('WebDriver initialized successfully on bot startup')
    except Exception as e:
        print(f'Error initializing WebDriver: {e}')
    
    # スラッシュコマンドを同期
    try:
        print('Syncing slash commands...')
        synced = await tree.sync()
        print(f'Successfully synced {len(synced)} slash commands:')
        for cmd in synced:
            print(f'  - {cmd.name}: {cmd.description}')
    except Exception as e:
        print(f'Failed to sync slash commands: {e}')
    
    print('=== GraTeX bot is ready! ===')


@bot.event
async def on_application_command_error(interaction: discord.Interaction, error: Exception):
    print(f"Application command error: {error}")
    print(f"Interaction: {interaction}")
    if not interaction.response.is_done():
        await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)


@bot.event
async def on_error(event, *args, **kwargs):
    print(f"Bot error in event {event}: {args}, {kwargs}")
    import traceback
    traceback.print_exc()


# ヘルプ用のEmbed作成関数
def create_help_embed():
    embed = discord.Embed(
        title="🧮 GraTeX Bot - Help",
        description="Generate mathematical graphs from LaTeX formulas with interactive controls",
        color=0x00ff00
    )
    
    embed.add_field(
        name="📖 Basic Usage",
        value='`/gratex formula:"latex_formula"`\n\n**Example:**\n`/gratex formula:"\\cos x\\le\\cos y"`',
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
    print(f"=== Slash command received ===")
    print(f"User: {interaction.user}")
    print(f"Guild: {interaction.guild}")
    print(f"Formula: {formula}")
    print(f"Label size: {label_size}")
    print(f"Zoom level: {zoom_level}")
    
    # パラメータ検証
    if label_size not in [1, 2, 3, 4, 6, 8]:
        print(f"Invalid label size: {label_size}")
        await interaction.response.send_message(
            '❌ **Invalid label size!**\nLabel size must be one of: 1, 2, 3, 4, 6, 8\n\nUse `/gratex formula:"help"` for more information.',
            ephemeral=True
        )
        return
    
    if not isinstance(zoom_level, int):
        print(f"Invalid zoom level type: {type(zoom_level)}")
        await interaction.response.send_message(
            '❌ **Invalid zoom level!**\nZoom level must be an integer\n\nUse `/gratex formula:"help"` for more information.',
            ephemeral=True
        )
        return

    # "help"チェック
    if formula.lower() == "help":
        print("Help requested")
        embed = create_help_embed()
        await interaction.response.send_message(embed=embed)
        return
    
    # 処理中メッセージ
    print("Deferring interaction response...")
    await interaction.response.defer()
    
    try:
        # 画像生成
        print(f"Generating image for formula: {formula}")
        cleaned_formula = formula.translate(str.maketrans('', '', '`'))
        print(f"Cleaned formula: {cleaned_formula}")
        
        img_data = await generate_img(cleaned_formula, str(label_size), zoom_level)
        print(f"Image generation result: {'success' if img_data != 'error' else 'error'}")
        
        if img_data == "error":
            print("Image generation failed")
            await interaction.followup.send(
                '❌ **The graph could not be generated.**\nPlease enter a simpler formula and try again.'
            )
            return

        # 画像送信
        print("Sending image file...")
        reply = await interaction.followup.send(
            file=discord.File(
                io.BytesIO(base64.b64decode(img_data)), 
                'GraTeX.png'
            )
        )
        print(f"Image sent successfully, message ID: {reply.id}")
        
        # リアクション追加
        print("Adding reactions...")
        reactions = ['2⃣', '3⃣', '4⃣', '6⃣', '🔎', '🔭', '✅', '🚮']
        for emoji in reactions:
            try:
                await reply.add_reaction(emoji)
                print(f"Added reaction: {emoji}")
            except Exception as e:
                print(f"Failed to add reaction {emoji}: {e}")
        
        print("Starting reaction listener...")
        # リアクション待機
        await waitReaction(interaction, reply, formula, str(label_size), zoom_level)
        
    except Exception as e:
        print(f"Error in slash command: {e}")
        import traceback
        traceback.print_exc()
        try:
            await interaction.followup.send(
                '❌ **An error occurred while generating the graph.**\nPlease try again later.'
            )
        except:
            print("Failed to send error message")


if __name__ == "__main__":
    print("=== Starting GraTeX Bot ===")
    # Railwayの環境変数からトークンを取得
    token = os.getenv("TOKEN")
    if not token:
        print("ERROR: TOKEN environment variable is not set")
        raise ValueError("TOKEN environment variable is not set")
    
    print(f"Token found: {token[:10]}...")
    
    try:
        print("Starting bot...")
        bot.run(token)
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Bot error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # クリーンアップ
        print("Cleaning up...")
        cleanup_driver()
