import json
import discord
from discord.ext import commands
from discord.ui import Button, View
import random
from pathlib import Path


# Get the absolute path to the JSON file
json_path = Path(__file__).resolve().parent.parent / 'data' / 'trivia' / 'Sc2 Units.json'

# Load the trivia data from the JSON file
with open(json_path, "r") as file:
    unit_data = json.load(file)

# List all units in the trivia data
units = list(unit_data.keys())

class Minigames(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}  # Dictionary to store ongoing games

    @commands.command(name="connect4", help="Starts a Connect 4 game")
    async def connect4(self, ctx, opponent: discord.Member = None):
        """Starts a Connect 4 game; if no opponent is specified, it will be against the AI."""
        if opponent is None:
            opponent = "AI"  # Set opponent to AI if none is provided

        # Create a new game instance and store it
        game = Connect4(ctx.author, opponent)
        self.games[game.game_id] = game

        # Start the game
        await game.start_game(ctx)

    @commands.command(name="c4", help="Shortcut command to play Connect 4")
    async def c4(self, ctx, opponent: discord.Member = None):
        await self.connect4(ctx, opponent)

    @commands.command(name="trivia", help="Ask a trivia question about StarCraft 2 units")
    async def trivia(self, ctx):
        """Asks a random trivia question about StarCraft 2 units."""
        # Randomly select a unit and an attribute
        unit = random.choice(units)
        attribute = random.choice(["health", "mineral_cost", "building_time", "shield", "armour"])

        # Get the correct answer for the selected attribute
        correct_answer = unit_data[unit][attribute]

        # Formulate the trivia question
        question = f"What is the {attribute} of {unit}?"

        # Ask the question to the user
        await ctx.send(question)

        def check(m):
            """Check if the response is from the same user and in the correct channel."""
            return m.author == ctx.author and m.channel == ctx.channel

        # Wait for the user's response
        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30)  # Wait for 30 seconds

            # Check if the answer is correct
            if str(correct_answer) in msg.content:
                await ctx.send(f"Correct! The {attribute} of {unit} is {correct_answer}.")
            else:
                await ctx.send(f"Incorrect! The correct answer was {correct_answer}.")

        except TimeoutError:
            await ctx.send("You took too long to answer!")

class Connect4:
    def __init__(self, player1, player2):
        """Initialize the Connect 4 game."""
        self.player1 = player1
        self.player2 = player2
        self.board = [["⬛" for _ in range(7)] for _ in range(6)]  # 7 columns, 6 rows
        self.current_turn = player1  # Player 1 starts
        self.game_over = False
        self.game_id = f"{player1.id}_{player2.id}" if player2 != "AI" else f"{player1.id}_AI"
        self.buttons = [Button(label=f"{i + 1}", custom_id=f"column_{i}", style=discord.ButtonStyle.primary) for i in range(7)]

    async def start_game(self, ctx):
        """Starts the game and sends the initial embed with buttons."""
        embed = self.create_board_embed()
        view = View()
        for button in self.buttons:
            button.callback = self.drop_piece  # Set the button callback
            view.add_item(button)

        await ctx.send(embed=embed, view=view)

    def create_board_embed(self):
        """Creates an embed with the current state of the board."""
        board_display = "\n".join(["".join(row) for row in self.board])
        column_numbers = "1️⃣2️⃣3️⃣4️⃣5️⃣6️⃣7️⃣"  # Column numbers at the top
        return discord.Embed(
            title="Connect 4",
            description=f"{column_numbers}\n{board_display}\n\nIt's **{self.current_turn.display_name if self.current_turn != 'AI' else 'AI'}'s** turn!",
            color=discord.Color.blue()
        )

    async def drop_piece(self, interaction: discord.Interaction):
        """Handles a button press to drop a piece into a column."""
        if self.game_over:
            await interaction.response.send_message("The game is over. Please start a new game!", ephemeral=True)
            return

        # Determine which column the button refers to
        column = int(interaction.data["custom_id"].split("_")[1])

        # Find the lowest available row in the column
        for row in reversed(range(6)):
            if self.board[row][column] == "⬛":  # Empty spot
                self.board[row][column] = "🟥" if self.current_turn == self.player1 else "🟦"
                break
        else:
            await interaction.response.send_message("This column is full! Choose another one.", ephemeral=True)
            return

        # Log the move made by the player or AI
        print(f"Move made by {self.current_turn.display_name if self.current_turn != 'AI' else 'AI'} in column {column + 1}")

        # Check for a win or tie
        if self.check_win():
            embed = self.create_board_embed()
            embed.title = f"{self.current_turn.display_name if self.current_turn != 'AI' else 'AI'} wins!"
            await interaction.response.edit_message(embed=embed, view=None)
            self.game_over = True
            return

        # Switch to the next player
        if self.current_turn != "AI":
            self.current_turn = self.player2 if self.current_turn == self.player1 else self.player1
            # Let AI play after the player's turn
            if self.current_turn == "AI":
                await self.ai_move(interaction)

        # Update the board in the message
        embed = self.create_board_embed()
        await interaction.response.edit_message(embed=embed)

    async def ai_move(self, interaction):
        """AI makes its move based on a heuristic strategy."""
        # AI tries to win, then blocks the player, or takes a random move
        move = self.get_best_move("🟦") or self.get_best_move("🟥")
        if move is None:
            available_columns = [col for col in range(7) if self.board[0][col] == "⬛"]
            move = random.choice(available_columns)

        # Drop the AI piece in the selected column
        for row in reversed(range(6)):
            if self.board[row][move] == "⬛":
                self.board[row][move] = "🟦"
                break

        # Log the AI move
        print(f"AI moves in column {move + 1}")

        # Check if AI wins after its move
        if self.check_win():
            embed = self.create_board_embed()
            embed.title = f"AI wins!"
            await interaction.response.edit_message(embed=embed, view=None)
            self.game_over = True
            return

        # Switch to the player's turn after AI's move
        self.current_turn = self.player1

    def get_best_move(self, piece):
        """Returns the best move for the AI or player."""
        for col in range(7):
            if self.board[0][col] == "⬛":  # Check if the column is not full
                for row in reversed(range(6)):
                    if self.board[row][col] == "⬛":
                        self.board[row][col] = piece
                        if self.check_win():
                            self.board[row][col] = "⬛"  # Undo the move
                            return col  # This is the winning move
                        self.board[row][col] = "⬛"  # Undo the move
                        break
        return None

    def check_win(self):
        """Check for a Connect 4 win condition."""
        for row in range(6):
            for col in range(7):
                if self.board[row][col] == "⬛":
                    continue
                if self.check_direction(row, col, 1, 0) or self.check_direction(row, col, 0, 1) or self.check_direction(row, col, 1, 1) or self.check_direction(row, col, 1, -1):
                    return True
        return False

    def check_direction(self, row, col, row_dir, col_dir):
        """Checks if there are 4 pieces in a line from the (row, col) point."""
        piece = self.board[row][col]
        for i in range(1, 4):
            r, c = row + row_dir * i, col + col_dir * i
            if not (0 <= r < 6 and 0 <= c < 7) or self.board[r][c] != piece:
                return False
        return True

# Add this cog to the bot
async def setup(bot):
    await bot.add_cog(Minigames(bot))
