import discord
from discord.ext import commands
from discord.ui import Button, View
import random
import asyncio


class Card:
    def __init__(self, name, effect):
        self.name = name
        self.effect = effect  # The type of effect this card has (e.g., 'defuse', 'explode', 'cat', etc.)

    def __repr__(self):
        return f"Card(name={self.name}, effect={self.effect})"


class ExplodingKittensGame:
    def __init__(self, players, starting_hand_size=5, defuse_count=6, bomb_count=1, attack_x2_count=2,
                 attack_x3_count=2, skip_count=2, nope_count=2, future_count=2, reveal_future_count=1):
        self.players = players  # List of player IDs
        self.deck = self.create_deck(len(players), defuse_count, bomb_count, attack_x2_count, attack_x3_count,
                                     skip_count, nope_count, future_count, reveal_future_count)
        self.hands = {player: [] for player in players}
        self.turn_index = 0
        self.starting_hand_size = starting_hand_size
        self.init_hands()

    def create_deck(self, num_players, defuse_count, bomb_count, attack_x2_count, attack_x3_count, skip_count,
                    nope_count, future_count, reveal_future_count):
        # Create a deck with Exploding Kittens, Defuse, and other special cards
        deck = [Card("Exploding Kitten", "explode")] * bomb_count
        deck += [Card("Defuse", "defuse")] * defuse_count
        deck += [Card("Attack x2", "attack2")] * attack_x2_count
        deck += [Card("Attack x3", "attack3")] * attack_x3_count
        deck += [Card("Skip", "skip")] * skip_count
        deck += [Card("Nope", "nope")] * nope_count
        deck += [Card("See the Future", "future")] * future_count
        deck += [Card("Reveal the Future", "reveal_future")] * reveal_future_count
        # Adding the 5 unique Cat cards
        cat_names = ["Palindrome Cat", "Beard Cat", "Smol Cat", "Big Cat", "Panzer Cat"]
        for name in cat_names:
            deck += [Card(name, "cat")] * 2  # Two of each Cat card
        random.shuffle(deck)
        return deck

    def init_hands(self):
        # Deal initial hands to each player
        for player in self.players:
            self.hands[player] = [self.deck.pop() for _ in range(self.starting_hand_size)]
            # Add a defuse card to each player's hand
            self.hands[player].append(Card("Defuse", "defuse"))

    def draw_card(self, player_id):
        # Player draws a card from the deck
        card = self.deck.pop()
        if card.name == "Exploding Kitten":
            # Handle explosion or defuse
            return self.handle_explosion(player_id)
        else:
            self.hands[player_id].append(card)
            return f"{player_id} drew a {card.name} card."

    def handle_explosion(self, player_id):
        # Check if player has a defuse card
        hand = self.hands[player_id]
        defuse_card = next((c for c in hand if c.name == "Defuse"), None)
        if defuse_card:
            # Use Defuse card
            hand.remove(defuse_card)
            # Place Exploding Kitten back in the deck at random position
            self.deck.insert(random.randint(0, len(self.deck)), Card("Exploding Kitten", "explode"))
            return f"{player_id} used a Defuse card to avoid the explosion!"
        else:
            # Player is eliminated
            self.players.remove(player_id)
            return f"{player_id} has exploded and is out of the game!"

    def steal_card(self, player_id, target_id):
        # Check if player has two of the same Cat card
        hand = self.hands[player_id]
        cat_cards = [card for card in hand if card.effect == "cat"]
        card_count = {card.name: cat_cards.count(card) for card in cat_cards}
        stealable_cat = [card for card, count in card_count.items() if count >= 2]

        if stealable_cat:
            selected_cat = random.choice(stealable_cat)
            # Steal a random card from the target player
            target_hand = self.hands[target_id]
            stolen_card = random.choice(target_hand)
            self.hands[target_id].remove(stolen_card)
            self.hands[player_id].append(stolen_card)
            return f"{player_id} stole a {stolen_card.name} card from {target_id} using {selected_cat}!"
        else:
            return f"{player_id} does not have two of the same Cat card to steal."

    def next_turn(self):
        # Advance to the next player
        self.turn_index = (self.turn_index + 1) % len(self.players)
        return f"It is now {self.players[self.turn_index]}'s turn."


class ExplodingKittens(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}  # Stores active games with channel ID as key

    @commands.command(name="start_game")
    async def start_game(self, ctx, starting_hand_size: int = 5, defuse_count: int = 6, bomb_count: int = 1,
                         attack_x2_count: int = 2, attack_x3_count: int = 2, skip_count: int = 2, nope_count: int = 2,
                         future_count: int = 2, reveal_future_count: int = 1, *players: discord.Member):
        if ctx.channel.id in self.active_games:
            await ctx.send("A game is already in progress in this channel.")
            return

        player_ids = [player.id for player in players]
        game = ExplodingKittensGame(player_ids, starting_hand_size, defuse_count, bomb_count, attack_x2_count,
                                    attack_x3_count, skip_count, nope_count, future_count, reveal_future_count)
        self.active_games[ctx.channel.id] = game
        await ctx.send("Exploding Kittens game started! Players have been dealt their hands.")

        # Display starting hands to each player with buttons
        for player_id in player_ids:
            player = self.bot.get_user(player_id)
            await self.display_player_deck(player, game)

        await ctx.send(f"{self.bot.get_user(game.players[0]).mention} goes first!")

    async def display_player_deck(self, player, game):
        hand = game.hands[player.id]
        hand_buttons = []

        # Create buttons for each card the player has, if it's their turn
        for card in hand:
            if card.name != "Nope":  # NOPE should be handled separately
                button = Button(label=card.name, custom_id=f"card_{card.name}", style=discord.ButtonStyle.primary)
                hand_buttons.append(button)
            else:
                # NOPE button is available for everyone to prevent steal
                button = Button(label="NOPE", custom_id="card_nope", style=discord.ButtonStyle.danger)
                hand_buttons.append(button)

        view = View(timeout=10)  # 10 seconds for response
        for button in hand_buttons:
            if player.id != game.players[game.turn_index]:  # If it's not the player's turn, disable the button
                button.disabled = True
            view.add_item(button)

        # Send the embed with their deck and buttons
        embed = discord.Embed(title="Your Hand", description="\n".join([card.name for card in hand]),
                              color=discord.Color.green())
        await player.send(embed=embed, view=view)

    @commands.command(name="ek_draw")
    async def draw_card(self, ctx):
        channel_id = ctx.channel.id
        if channel_id not in self.active_games:
            await ctx.send("No active game in this channel. Start one with !ek start_game.")
            return

        game = self.active_games[channel_id]
        player_id = ctx.author.id
        if game.players[game.turn_index] != player_id:
            await ctx.send("It's not your turn!")
            return

        result = game.draw_card(player_id)
        await ctx.send(result)

        if player_id not in game.players:
            # If player exploded, check if game is over
            if len(game.players) == 1:
                winner = self.bot.get_user(game.players[0])
                await ctx.send(f"The game is over! {winner.mention} wins!")
                del self.active_games[channel_id]  # End the game

        # Advance to the next turn
        await game.next_turn()

        # Display updated deck after drawing card
        await self.display_player_deck(self.bot.get_user(player_id), game)


async def setup(bot):
    await bot.add_cog(ExplodingKittens(bot))
