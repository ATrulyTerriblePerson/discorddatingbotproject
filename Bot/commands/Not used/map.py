import discord
from discord.ext import commands
from perlin_noise import PerlinNoise
import random

class MapNavigation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.map_width = 50
        self.map_height = 40
        self.view_range = 5
        self.player_position = {"x": self.map_width // 2, "y": self.map_height // 2}
        self.seed = random.randint(1, 10000)
        self.noise = PerlinNoise(octaves=6, seed=self.seed)

        # Adjusted biome probabilities
        self.biome_probs = {
            "ocean": 15,
            "field": 15,
            "plains": 20,
            "forest": 20,
            "town": 5,
            "castle": 5,
            "river": 5,
            "desert": 5,
            "mountain": 10
        }

        # Emoji mapping
        self.biome_emojis = {
            "plains": "🟩",
            "forest": "🌲",
            "town": "🏘️",
            "castle": "🏰",
            "ocean": "🟦",
            "field": "🟨",
            "desert": "🟧",
            "mountain": "⛰️",
            "river": "🟦",  # Using blue for river as well
            "character": "⚔️"
        }

        self.base_map = self.generate_map()

    def generate_map(self):
        map_grid = [["ocean" for _ in range(self.map_width)] for _ in range(self.map_height)]

        # Ensure oceans are on the edges of the map
        self.place_oceans_on_edges(map_grid)

        # Place mountains
        self.place_mountains(map_grid)

        # Place rivers connected from mountains to oceans
        self.place_rivers(map_grid)

        # Place major biomes first for clustering
        self.place_clustered_biomes(map_grid, "castle", 3)
        self.place_clustered_biomes(map_grid, "town", 5)

        # Ensure fields around towns/castles
        self.ensure_fields_around_villages(map_grid)

        # Generate biomes with noise for natural variation
        for y in range(self.map_height):
            for x in range(self.map_width):
                if map_grid[y][x] == "ocean":  # Only overwrite if uninitialized
                    noise_val = self.noise([x / self.map_width, y / self.map_height])
                    map_grid[y][x] = self.get_biome_from_noise(noise_val)

        return map_grid

    def place_oceans_on_edges(self, map_grid):
        for x in range(self.map_width):
            map_grid[0][x] = "ocean"  # Top edge
            map_grid[self.map_height - 1][x] = "ocean"  # Bottom edge
        for y in range(self.map_height):
            map_grid[y][0] = "ocean"  # Left edge
            map_grid[y][self.map_width - 1] = "ocean"  # Right edge

    def place_mountains(self, map_grid):
        for _ in range(5):  # Number of mountains
            x = random.randint(4, self.map_width - 5)
            y = random.randint(4, self.map_height - 5)
            if map_grid[y][x] == "ocean":  # Ensure no mountains on oceans
                map_grid[y][x] = "mountain"
                # Surround the mountain with forests
                for i in range(-1, 2):
                    for j in range(-1, 2):
                        if 0 <= x + i < self.map_width and 0 <= y + j < self.map_height:
                            if map_grid[y + j][x + i] == "ocean":
                                continue  # Don't place forest on ocean
                            map_grid[y + j][x + i] = "forest"

    def place_rivers(self, map_grid):
        for _ in range(3):  # Number of rivers
            start_x = random.randint(0, self.map_width - 1)
            start_y = random.randint(0, self.map_height - 1)
            # Ensure starting point is near a mountain or field
            if map_grid[start_y][start_x] in ["mountain", "field"]:
                length = random.randint(20, 50)
                for _ in range(length):
                    if 0 <= start_x < self.map_width and 0 <= start_y < self.map_height:
                        map_grid[start_y][start_x] = "river"
                        # Rivers curve slightly, favoring certain directions
                        start_x += random.choice([-1, 0, 1])
                        start_y += random.choice([-1, 0, 1])
                    if map_grid[start_y][start_x] == "ocean":
                        break  # Stop if it reaches the ocean

    def ensure_fields_around_villages(self, map_grid):
        for y in range(self.map_height):
            for x in range(self.map_width):
                if map_grid[y][x] in ["town", "castle"]:
                    # Ensure at least 5-9 field tiles around towns/castles
                    field_count = 0
                    for i in range(-3, 4):
                        for j in range(-3, 4):
                            if 0 <= x + i < self.map_width and 0 <= y + j < self.map_height:
                                if map_grid[y + j][x + i] == "field":
                                    field_count += 1

                    # If not enough fields, add them
                    while field_count < random.randint(5, 9):
                        fx = random.randint(x - 3, x + 3)
                        fy = random.randint(y - 3, y + 3)
                        if 0 <= fx < self.map_width and 0 <= fy < self.map_height:
                            if map_grid[fy][fx] == "ocean":
                                continue  # Don't place fields on oceans
                            map_grid[fy][fx] = "field"
                            field_count += 1

    def get_biome_from_noise(self, noise_val):
        thresholds = [
            ("ocean", 0.1),
            ("desert", 0.2),
            ("plains", 0.35),
            ("field", 0.45),
            ("forest", 0.65),
            ("mountain", 0.75),
            ("plains", 0.9),
            ("river", 1.0)
        ]
        for biome, threshold in thresholds:
            if noise_val <= threshold:
                return biome
        return "plains"

    def place_clustered_biomes(self, map_grid, biome, count):
        for _ in range(count):
            placed = False
            while not placed:
                x = random.randint(0, self.map_width - 1)
                y = random.randint(0, self.map_height - 1)
                # Check if the position is valid for placement
                if map_grid[y][x] == "ocean" and self.is_near_water(map_grid, x, y):
                    map_grid[y][x] = biome
                    placed = True

    def is_near_water(self, map_grid, x, y):
        for i in range(-3, 4):
            for j in range(-3, 4):
                if 0 <= x + i < self.map_width and 0 <= y + j < self.map_height:
                    if map_grid[y + j][x + i] == "river" or map_grid[y + j][x + i] == "ocean":
                        return True
        return False

    def get_visible_map(self):
        visible_map = []
        for y_offset in range(-self.view_range, self.view_range + 1):
            row = []
            for x_offset in range(-self.view_range, self.view_range + 1):
                x = self.player_position["x"] + x_offset
                y = self.player_position["y"] + y_offset
                if 0 <= x < self.map_width and 0 <= y < self.map_height:
                    if x == self.player_position["x"] and y == self.player_position["y"]:
                        row.append(self.biome_emojis["character"])
                    else:
                        biome = self.base_map[y][x]
                        row.append(self.biome_emojis.get(biome, "⬛"))
                else:
                    row.append("⬛")  # Out of bounds
            visible_map.append("".join(row))
        return "\n".join(visible_map)
    def get_tile_counts(self):
        tile_counts = {biome: 0 for biome in self.biome_probs.keys()}
        for row in self.base_map:
            for tile in row:
                if tile in tile_counts:
                    tile_counts[tile] += 1
        return tile_counts

    @commands.command(name="map")
    async def show_map(self, ctx):
        embed = discord.Embed(title="Map", description=self.get_visible_map(), color=discord.Color.blue())
        embed.set_footer(text="Navigate with buttons.")
        view = MapNavigationView(self)
        await ctx.send(embed=embed, view=view)

    @commands.command(name="mapdetails", aliases=["mp"])
    async def show_map_details(self, ctx):
        tile_counts = self.get_tile_counts()
        description = "\n".join([f"**{biome.capitalize()}**: {count}" for biome, count in tile_counts.items()])
        embed = discord.Embed(
            title="Map Details",
            description=description,
            color=discord.Color.green()
        )
        embed.add_field(name="Map Seed", value=str(self.seed), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="towns")
    async def list_towns_castles(self, ctx):
        town_coords = self.town_castle_coords["town"]
        castle_coords = self.town_castle_coords["castle"]
        description = f"**Towns:** {town_coords}\n**Castles:** {castle_coords}"
        embed = discord.Embed(title="Town and Castle Locations", description=description, color=discord.Color.gold())
        await ctx.send(embed=embed)

    async def move_player(self, direction, sprint=False):
        move_steps = 3 if sprint else 1
        if direction == "left" and self.player_position["x"] - move_steps >= 0:
            self.player_position["x"] -= move_steps
        elif direction == "right" and self.player_position["x"] + move_steps < self.map_width:
            self.player_position["x"] += move_steps
        elif direction == "up" and self.player_position["y"] - move_steps >= 0:
            self.player_position["y"] -= move_steps
        elif direction == "down" and self.player_position["y"] + move_steps < self.map_height:
            self.player_position["y"] += move_steps


class MapNavigationView(discord.ui.View):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog
        self.sprint_enabled = False  # Toggle for sprint mode

    @discord.ui.button(label="Interact", style=discord.ButtonStyle.grey, row=0)
    async def interact(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"You interact with tile ID: {self.tile_id}.", ephemeral=True)

    @discord.ui.button(label="Up", style=discord.ButtonStyle.blurple, row=0)
    async def move_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_move(interaction, "up")

    @discord.ui.button(label="Sprint", style=discord.ButtonStyle.green, row=0)
    async def sprint(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Toggle sprint mode
        self.sprint_enabled = not self.sprint_enabled
        button.label = "Sprint: ON" if self.sprint_enabled else "Sprint: OFF"
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Left", style=discord.ButtonStyle.blurple, row=1)
    async def move_left(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_move(interaction, "left")

    @discord.ui.button(label="Down", style=discord.ButtonStyle.blurple, row=1)
    async def move_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_move(interaction, "down")

    @discord.ui.button(label="Right", style=discord.ButtonStyle.blurple, row=1)
    async def move_right(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_move(interaction, "right")

    @discord.ui.button(label="Inventory", style=discord.ButtonStyle.grey, row=2)
    async def inventory(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Your inventory is empty.", ephemeral=True)

    async def handle_move(self, interaction: discord.Interaction, direction: str):
        await self.cog.move_player(direction, sprint=self.sprint_enabled)
        embed = discord.Embed(title="Map", description=self.cog.get_visible_map(), color=discord.Color.blue())
        embed.set_footer(text="Navigate with buttons.")
        await interaction.response.edit_message(embed=embed, view=self)

async def setup(bot):
    await bot.add_cog(MapNavigation(bot))