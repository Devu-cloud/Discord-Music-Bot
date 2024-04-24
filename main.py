import os
import discord
import asyncio
from discord.ext import commands,tasks
from itertools import cycle
import importlib
import logging

from dotenv import load_dotenv
load_dotenv()



# Set up logging
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")

intents = discord.Intents.default()
intents.voice_states = True
intents.members = True
intents.messages = True
intents.message_content = True
intents.presences = True

# Creating bot instance
bot = commands.Bot(command_prefix="!!", intents=intents, help_command=None)
bot_status = cycle(["type !!h to help","activity 2", "acticvity 3","activity 4"])

@tasks.loop(seconds =15)
async def change_status():
    await bot.change_presence(activity =discord.Game(next(bot_status)))
    
#event handler for when bot is ready
@bot.event
async def on_ready():
    try:
        print("_______________________\n")
        print(f"{bot.user.name} at your Service!!")
        print(f"Bot_ID ={bot.user.id}")
        print("_______________________")
        change_status.start()
        
    except Exception as e:
        print(f"An error occurred: {e}")
        
#loading required cogs
# Automatically load all cogs
async def load():
    for cog in os.listdir('cogs'):
        if cog.endswith('.py'):
            try:
                await bot.load_extension(f'cogs.{cog[:-3]}')
                print(f'Loaded {cog} cog')
            except Exception as e:
                print(f'Failed to load {cog} cog: {e}')


# Automatically reload all cogs
@bot.command()
@commands.has_permissions(administrator=True)
async def reload_all_cogs(ctx):
    for cog in os.listdir('cogs'):
        if cog.endswith('.py'):
            try:
                await bot.reload_extension(f'cogs.{cog[:-3]}')
                await ctx.send(f'Reloaded {cog} cog')
            except Exception as e:
                await ctx.send(f'Failed to reload {cog} cog: {e}')

# Automatically unload all cogs
@bot.command()
@commands.has_permissions(administrator=True)
async def unload_all_cogs(ctx):
    for cog in os.listdir('cogs'):
        if cog.endswith('.py'):
            try:
                await bot.unload_extension(f'cogs.{cog[:-3]}')
                await ctx.send(f'Unloaded {cog} cog')
            except Exception as e:
              await ctx.send(f'Failed to unload {cog} cog: {e}')
              
#running the bot              
async def main():
    async with bot:
        await load()
        await bot.start(DISCORD_BOT_TOKEN)

asyncio.run(main())