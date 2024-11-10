import discord
from discord.ext import commands
import os
import asyncio
import setup  # Import setup.py to run the directory checks

# Print current working directory
print("Current Working Directory:", os.getcwd())

# Initialize the bot with the desired prefix and intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Function to display available commands by group
async def list_command_groups():
    for cog_name in bot.cogs:
        cog = bot.get_cog(cog_name)
        print(f'Command Group: {cog_name}')
        for command in cog.get_commands():
            print(f'  - {command.name}: {command.help}')

# Function to load commands from the 'commands' directory
async def load_extensions():
    for filename in os.listdir('./commands'):
        if filename.endswith('.py') and filename != '__init__.py':
            await bot.load_extension(f'commands.{filename[:-3]}')

# Bot event to notify that it's ready and display command groups
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    await list_command_groups()

# Replace 'YOUR_DISCORD_TOKEN' with your actual token
async def main():
    setup.check_dependencies()  # Run setup.py to create necessary directories
    await load_extensions()
    await bot.start(YOUR_DISCORD_TOKEN)

# Start the bot
if __name__ == "__main__":
    asyncio.run(main())
