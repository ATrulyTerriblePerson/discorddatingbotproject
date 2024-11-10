import discord
from discord.ext import commands
import random

class CardGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}

    def create_deck(self):
        suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'Jack', 'Queen', 'King', 'Ace']
        return [(rank, suit) for suit in suits for rank in ranks]

    def card_value(self, card):
        rank = card[0]
        if rank in ['Jack', 'Queen', 'King']:
            return 10
        elif rank == 'Ace':
            return 11  # Handle Aces later in scoring
        else:
            return int(rank)

    async def start_game(self, ctx, game_type):
        if ctx.channel.id in self.games:
            await ctx.send("A game is already in progress in this channel.")
            return

        deck = self.create_deck()
        random.shuffle(deck)

        self.games[ctx.channel.id] = {
            'deck': deck,
            'players': {},
            'game_type': game_type
        }

        await ctx.send(f"{game_type} game started! Type !join to participate.")

    @commands.command()
    async def poker(self, ctx):
        await self.start_game(ctx, "Poker")

    @commands.command()
    async def war(self, ctx):
        await self.start_game(ctx, "War")

    @commands.command()
    async def blackjack(self, ctx):
        await self.start_game(ctx, "Blackjack")

    @commands.command()
    async def pokerjoin(self, ctx):
        if ctx.channel.id not in self.games:
            await ctx.send("No game is currently running. Start a game using !poker, !war, or !blackjack.")
            return

        game = self.games[ctx.channel.id]
        player_id = ctx.author.id

        if player_id in game['players']:
            await ctx.send("You have already joined this game.")
            return

        game['players'][player_id] = {
            'hand': [],
            'score': 0
        }

        await ctx.send(f"{ctx.author.name} has joined the game!")

        # If enough players join, start the game
        if len(game['players']) == 2:
            await ctx.send("Two players have joined! The game will start now.")
            await self.deal_initial_cards(ctx)

    async def deal_initial_cards(self, ctx):
        game = self.games[ctx.channel.id]

        for player_id in game['players']:
            hand = [game['deck'].pop(), game['deck'].pop()]
            game['players'][player_id]['hand'] = hand

        await self.show_hands(ctx)

    async def show_hands(self, ctx):
        game = self.games[ctx.channel.id]
        embed = discord.Embed(title="Current Hands")

        for player_id, player in game['players'].items():
            hand = ", ".join(f"{card[0]} of {card[1]}" for card in player['hand'])
            embed.add_field(name=f"{self.bot.get_user(player_id).name}'s Hand", value=hand, inline=True)

        await ctx.send(embed=embed)

        # Interactive buttons for drawing cards or ending the game
        buttons = [
            discord.ui.Button(label="Draw Card", style=discord.ButtonStyle.primary, custom_id="draw_card"),
            discord.ui.Button(label="End Game", style=discord.ButtonStyle.danger, custom_id="end_game"),
        ]

        view = discord.ui.View()
        for button in buttons:
            view.add_item(button)

        await ctx.send("Choose your action:", view=view)

    @discord.ui.button(label="Draw Card", style=discord.ButtonStyle.primary, custom_id="draw_card")
    async def draw_card(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer()  # Acknowledge the button press

        ctx = interaction.channel
        if ctx.id not in self.games:
            await interaction.followup.send("No game is currently running.")
            return

        game = self.games[ctx.id]
        player_id = interaction.user.id

        if player_id not in game['players']:
            await interaction.followup.send("You need to join the game first using !join.")
            return

        if not game['deck']:
            await interaction.followup.send("No cards left in the deck!")
            return

        card = game['deck'].pop(random.randint(0, len(game['deck']) - 1))
        game['players'][player_id]['hand'].append(card)

        embed = discord.Embed(title="Your Draw", description=f"You drew: {card[0]} of {card[1]}")
        await interaction.followup.send(embed=embed)

        await self.show_hands(interaction)

        # Check win conditions (only for Blackjack as an example)
        if game['game_type'] == "Blackjack":
            score = sum(self.card_value(card) for card in game['players'][player_id]['hand'])
            if score > 21:
                await interaction.followup.send(f"{interaction.user.name}, you bust! Game over.")
                await self.end_game(interaction)
            elif score == 21:
                await interaction.followup.send(f"{interaction.user.name}, you hit Blackjack! You win!")
                await self.end_game(interaction)

    @discord.ui.button(label="End Game", style=discord.ButtonStyle.danger, custom_id="end_game")
    async def end_game(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer()  # Acknowledge the button press

        ctx = interaction.channel
        if ctx.id not in self.games:
            await interaction.followup.send("No game is currently running.")
            return

        del self.games[ctx.id]
        await interaction.followup.send("Game ended.")

async def setup(bot):
    await bot.add_cog(CardGame(bot))
