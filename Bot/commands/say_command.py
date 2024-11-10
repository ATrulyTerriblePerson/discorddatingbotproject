import discord
from discord.ext import commands

class SayCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def say(self, ctx, *, message: str):
        await ctx.send(message)

async def setup(bot):
    await bot.add_cog(SayCommand(bot))
