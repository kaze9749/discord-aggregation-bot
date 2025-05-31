from discord.ext import commands
import discord
from commands import setup_commands
from scheduler import setup_scheduler
from config import TOKEN

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True  # これがないとメッセージ内容の取得不可

bot = commands.Bot(command_prefix="!", intents=intents)

setup_commands(bot)
setup_scheduler(bot)

bot.run(TOKEN)
