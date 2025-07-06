import os
import io, base64, discord, asyncio
from discord.ext import commands
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException

# Chrome WebDriverの設定
options = Options()
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument('--remote-debugging-port=9222')
options.headless = True

# Railway環境での設定
driver = webdriver.Chrome(options=options)

driver.get('https://teth-main.github.io/GraTeX/?wide=true&credit=true')
WebDriverWait(driver, 20).until(
  EC.presence_of_element_located((By.CLASS_NAME, "dcg-tap-container")))


async def generate_img(latex, labelSize='4', zoomLevel=0):

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


async def waitReaction(ctx, message, arg, labelSize, zoomLevel):

  def check(reaction, user):
    return user == ctx.author and str(reaction.emoji) in [
      '1⃣', '2⃣', '3⃣', '4⃣', '6⃣', '8⃣', '🔎', '🔭', '✅', '🚮'
    ]

  try:
    reaction, user = await bot.wait_for('reaction_add',
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

    await reaction.remove(user)
    async with ctx.typing():
      img_data = await generate_img(arg, labelSize, zoomLevel)
      await message.edit(attachments=[
        discord.File(io.BytesIO(base64.b64decode(img_data)),
                     f'GraTeX zoom {zoomLevel}.png')
      ])
    await waitReaction(ctx, message, arg, labelSize, zoomLevel)


@bot.event
async def on_ready():
  print('GraTeX bot is ready!')


@bot.command()
async def gratex(ctx, arg, labelSize='4', zoomLevel=0):
  if (arg == "help"):
    await ctx.send('''
    You get a formula in latex format and a function graph in one image with this bot. The command is `!gratex \"{latex}\"` and the formula must be enclosed in \" \".
    ex) `!gratex \"\\cos x\\le\\cos y\"`
    
    __The output image will be given a reaction.__
    2⃣3⃣4⃣6⃣ : change the size of the label(=labelSize)
    🔎 : zoomin
    🔭 : zoomout
    ✅ : complete(Note: if there is no response for 20 seconds, the process is automatically completed.)
    🚮 : delete

    __extended command__
    `!gratex \"{latex}\" labelSize zoomLevel`
    labelSize supports four as shown in the stamp above.
    Enter zoomLevel as an integer value.
    ''')
    return

  if (not labelSize in ['1', '2', '3', '4', '6', '8']):
    await ctx.send(
      'Wrong command!\n\nPlease type `!gratex help` to confirm the command.')
    return

  if (not isinstance(zoomLevel, int)):
    await ctx.send(
      'Wrong command!\n\nPlease type `!gratex help` to confirm the command.')
    return

  async with ctx.typing():
    img_data = await generate_img(arg.translate(str.maketrans('', '',
                                                              '`')), labelSize,
                                  zoomLevel)  #removes extra msg bits
    if (img_data == "error"):
      await ctx.send(
        '**The graph could not be generated. \nPlease enter a simpler formula and try again.**'
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
    
    bot.run(token)
