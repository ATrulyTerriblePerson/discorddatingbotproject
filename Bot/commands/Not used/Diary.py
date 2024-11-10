import discord
from discord.ext import commands, tasks
from textblob import TextBlob
import json
import os
from datetime import datetime, timedelta
import random


class DiaryEntryModal(discord.ui.Modal):
    def __init__(self, bot, user_id):
        super().__init__(title="Write Diary Entry")
        self.bot = bot
        self.user_id = user_id

        # Input fields for diary entry and tags
        self.add_item(discord.ui.InputText(label="Your Entry", style=discord.InputTextStyle.long,
                                           placeholder="Write your thoughts here..."))
        self.add_item(discord.ui.InputText(label="Tags (comma separated)", placeholder="#happy, #goal"))

    async def callback(self, interaction: discord.Interaction):
        # Extract the entry and tags
        entry_text = self.children[0].value
        tags = [tag.strip() for tag in self.children[1].value.split(",")]

        # Perform sentiment analysis
        mood = self.analyze_mood(entry_text)

        # Save the entry
        await self.save_entry(entry_text, tags, mood)

        await interaction.response.send_message(f"Your diary entry has been saved with a mood of '{mood}'.",
                                                ephemeral=True)

    async def save_entry(self, entry_text, tags, mood):
        date_str = datetime.now().strftime("%Y-%m-%d")
        entry_data = {
            "date": date_str,
            "text": entry_text,
            "tags": tags,
            "mood": mood
        }

        user_dir = f"diaries/{self.user_id}"
        os.makedirs(user_dir, exist_ok=True)
        entry_path = os.path.join(user_dir, f"{date_str}.json")

        with open(entry_path, "w") as file:
            json.dump(entry_data, file)

    def analyze_mood(self, entry_text):
        analysis = TextBlob(entry_text)
        polarity = analysis.sentiment.polarity
        if polarity > 0:
            return "positive"
        elif polarity < 0:
            return "negative"
        else:
            return "neutral"


class DiaryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_prompt.start()

    def cog_unload(self):
        self.daily_prompt.cancel()

    @commands.slash_command(name="write_diary")
    async def write_diary(self, ctx: discord.ApplicationContext):
        """Opens a modal to write a private diary entry."""
        modal = DiaryEntryModal(self.bot, ctx.author.id)
        await ctx.send_modal(modal)

    @commands.slash_command(name="mood_summary")
    async def mood_summary(self, ctx: discord.ApplicationContext, period: str = "month"):
        """Generate a mood summary based on past entries (weekly or monthly)."""
        user_dir = f"diaries/{ctx.author.id}"
        if not os.path.exists(user_dir):
            await ctx.respond("You have no diary entries yet.", ephemeral=True)
            return

        mood_counts = {"positive": 0, "neutral": 0, "negative": 0}
        for filename in os.listdir(user_dir):
            with open(os.path.join(user_dir, filename)) as file:
                entry = json.load(file)
                mood_counts[entry.get("mood", "neutral")] += 1

        # Generate the summary
        total_entries = sum(mood_counts.values())
        if total_entries == 0:
            await ctx.respond("No entries available for mood summary.", ephemeral=True)
            return

        mood_summary = "\n".join(
            [f"{mood.capitalize()}: {count} ({(count / total_entries) * 100:.1f}%)" for mood, count in
             mood_counts.items()]
        )
        await ctx.respond(f"**Mood Summary ({period}):**\n{mood_summary}", ephemeral=True)

    @commands.slash_command(name="search_diary")
    async def search_diary(self, ctx: discord.ApplicationContext, keyword: str):
        """Search your diary entries for a specific keyword."""
        user_dir = f"diaries/{ctx.author.id}"
        if not os.path.exists(user_dir):
            await ctx.respond("You have no diary entries yet.", ephemeral=True)
            return

        results = []
        for filename in os.listdir(user_dir):
            with open(os.path.join(user_dir, filename)) as file:
                entry = json.load(file)
                if keyword.lower() in entry["text"].lower():
                    results.append(entry["date"])

        if results:
            await ctx.respond(f"Found keyword '{keyword}' in entries on: {', '.join(results)}", ephemeral=True)
        else:
            await ctx.respond(f"No entries found with keyword '{keyword}'.", ephemeral=True)

    @commands.slash_command(name="export_diary")
    async def export_diary(self, ctx: discord.ApplicationContext):
        """Export all your diary entries to a text file."""
        user_dir = f"diaries/{ctx.author.id}"
        if not os.path.exists(user_dir):
            await ctx.respond("You have no diary entries yet.", ephemeral=True)
            return

        export_text = ""
        for filename in sorted(os.listdir(user_dir)):
            with open(os.path.join(user_dir, filename)) as file:
                entry = json.load(file)
                export_text += f"{entry['date']}\n{entry['text']}\nTags: {', '.join(entry['tags'])}\nMood: {entry['mood']}\n\n"

        export_path = f"diaries/{ctx.author.id}_export.txt"
        with open(export_path, "w") as export_file:
            export_file.write(export_text)

        await ctx.respond("Here is your exported diary file:", file=discord.File(export_path), ephemeral=True)

    @commands.slash_command(name="monthly_highlights")
    async def monthly_highlights(self, ctx: discord.ApplicationContext):
        """Get a summary of positive highlights for the month."""
        user_dir = f"diaries/{ctx.author.id}"
        if not os.path.exists(user_dir):
            await ctx.respond("You have no diary entries yet.", ephemeral=True)
            return

        highlights = []
        for filename in os.listdir(user_dir):
            with open(os.path.join(user_dir, filename)) as file:
                entry = json.load(file)
                if entry["mood"] == "positive":
                    highlights.append((entry["date"], entry["text"]))

        if highlights:
            summary = "\n\n".join([f"{date}: {text[:100]}..." for date, text in highlights])
            await ctx.respond(f"**Monthly Highlights:**\n{summary}", ephemeral=True)
        else:
            await ctx.respond("No positive highlights found for the month.", ephemeral=True)

    @tasks.loop(hours=24)
    async def daily_prompt(self):
        """Send a daily writing prompt to users."""
        prompts = [
            "What made you smile today?",
            "What's a recent goal you've achieved?",
            "Write about something that challenged you today.",
            "What are you grateful for right now?",
        ]
        prompt = random.choice(prompts)

        # Example for sending prompt to a specific channel
        channel = self.bot.get_channel(1267546007982313579)  # Replace with your channel ID
        if channel:
            await channel.send(f"Daily Writing Prompt: {prompt}")


async def setup(bot):
    await bot.add_cog(DiaryCog(bot))
