import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# تحميل المتغيرات البيئية
load_dotenv()

# إعداد البوت
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot logged in as {bot.user}')
    print('By s7.7 - جميع الحقوق محفوظة')
    await bot.change_presence(activity=discord.Game(name="By s7.7 🔥"))

@bot.command()
async def ping(ctx):
    await ctx.send('pong!')

print("جاري تشغيل البوت...")
bot.run(TOKEN) 