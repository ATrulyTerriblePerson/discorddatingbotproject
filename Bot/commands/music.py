# Import Statements
import os
import random
import time
import asyncio
import json
import math
import wave
from pathlib import Path
import asyncio
import re


import discord
from discord.ext import commands, tasks
from discord import FFmpegPCMAudio, PCMVolumeTransformer
from discord.ext import commands
from discord.ui import Button, View

from gpt4all import GPT4All
import fitz  # PyMuPDF
from dotenv import load_dotenv
import yt_dlp as youtube_dl
import yt_dlp

import pafy
import pyaudio
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from fuzzywuzzy import process




class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []
        self.loop = False
        self.loop_single = False

    @commands.command(name='join', help='Joins the voice channel that the user is in')
    async def join(self, ctx):
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await channel.connect()
            await ctx.send(f'Joined {channel}')
        else:
            await ctx.send('You are not connected to a voice channel.')

    @commands.command(name='leave', help='Disconnects the bot from the voice channel')
    async def leave(self, ctx):
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if voice_client:
            await voice_client.disconnect()
            await ctx.send('Disconnected from the voice channel.')
        else:
            await ctx.send('I am not connected to a voice channel.')

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""

        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"Changed volume to {volume}%")

    @commands.command(name='play', aliases=['Play'], help='Plays a song from YouTube')
    async def play(self, ctx, *, search: str = None):
        if search is None:
            await ctx.send('Usage: !play [song title]')
            return

        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'default_search': 'ytsearch',
            'quiet': True,
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search, download=False)
            url = info['entries'][0]['url']
            title = info['entries'][0]['title']

        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)

        if voice_client is None:
            await ctx.send('I am not connected to a voice channel.')
            return

        self.queue.append((url, title))

        if not voice_client.is_playing():
            await self.play_next(ctx)

        await ctx.send(f'Added to queue: {title}')

    async def play_next(self, ctx):
        if self.queue:
            url, title = self.queue.pop(0)
            voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)

            with youtube_dl.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                thumbnail = info.get('thumbnail', 'https://example.com/default_thumbnail.jpg')

            if not re.match(r'^https?://', thumbnail):
                thumbnail = 'https://example.com/default_thumbnail.jpg'

            embed = discord.Embed(title="Now Playing", description=title, color=0x00ff00)
            embed.set_image(url=thumbnail)

            async def pause_callback(interaction):
                if voice_client.is_playing():
                    voice_client.pause()
                    await interaction.response.send_message("Paused the current song.", ephemeral=True)

            async def resume_callback(interaction):
                if voice_client.is_paused():
                    voice_client.resume()
                    await interaction.response.send_message("Resumed the current song.", ephemeral=True)

            async def skip_callback(interaction):
                if voice_client.is_playing():
                    voice_client.stop()
                    await interaction.response.send_message("Skipped the current song.", ephemeral=True)
                    await self.play_next(ctx)

            async def loop_callback(interaction):
                self.loop = not self.loop
                self.loop_single = False
                await interaction.response.send_message(f"Looping is now {'enabled' if self.loop else 'disabled'}.", ephemeral=True)

            pause_button = Button(label="Pause", style=discord.ButtonStyle.primary)
            pause_button.callback = pause_callback

            resume_button = Button(label="Resume", style=discord.ButtonStyle.primary)
            resume_button.callback = resume_callback

            skip_button = Button(label="Skip", style=discord.ButtonStyle.primary)
            skip_button.callback = skip_callback

            loop_button = Button(label="Loop", style=discord.ButtonStyle.primary)
            loop_button.callback = loop_callback

            view = View()
            view.add_item(pause_button)
            view.add_item(resume_button)
            view.add_item(skip_button)
            view.add_item(loop_button)

            voice_client.play(discord.FFmpegPCMAudio(url), after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop))
            await ctx.send(embed=embed, view=view)

    @commands.command(name='queue', help='Displays the current song queue')
    async def queue(self, ctx):
        if self.queue:
            embed = discord.Embed(title="Queue", description="\n".join([f"{i + 1}. {title}" for i, (_, title) in enumerate(self.queue)]), color=0x00ff00)
        else:
            embed = discord.Embed(title="Queue", description="The queue is empty.", color=0x00ff00)

        await ctx.send(embed=embed)

    @commands.command(name='skip', help='Skips the current song')
    async def skip(self, ctx):
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)

        if voice_client.is_playing():
            voice_client.stop()
            await ctx.send("Skipped the current song.")
        else:
            await ctx.send("No song is currently playing.")

    @commands.command(name='pause', help='Pauses the current song')
    async def pause(self, ctx):
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)

        if voice_client.is_playing():
            voice_client.pause()
            await ctx.send("Paused the current song.")
        else:
            await ctx.send("No song is currently playing.")

    @commands.command(name='resume', help='Resumes the paused song')
    async def resume(self, ctx):
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)

        if voice_client.is_paused():
            voice_client.resume()
            await ctx.send("Resumed the current song.")
        else:
            await ctx.send("No song is currently paused.")

    @commands.command(name='loop', help='Loops the queue or the current song')
    async def loop(self, ctx, mode: str = None):
        if mode is None:
            await ctx.send('Usage: !loop [queue/single/off]')
            return

        mode = mode.lower()

        if mode == 'queue':
            self.loop = True
            self.loop_single = False
            await ctx.send("Looping the queue.")
        elif mode == 'single':
            self.loop = False
            self.loop_single = True
            await ctx.send("Looping the current song.")
        elif mode == 'off':
            self.loop = False
            self.loop_single = False
            await ctx.send("Looping is turned off.")
        else:
            await ctx.send("Invalid mode. Use 'queue', 'single', or 'off'.")

    
async def setup(bot):
    await bot.add_cog(Music(bot))  # Ensure this is awaited
