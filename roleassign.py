import discord
from discord.ext import commands
from discord.ui import Button, View
import random

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='b!', intents=intents)

SPECIAL_ROLE_NAME = "Player"
SPECIAL_CHANNEL_NAME = "game-1"
HOST_ROLE_NAME = "Host"

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command(name='play')
async def create_play_button(ctx):
    play_button = Button(label="Play", style=discord.ButtonStyle.primary)

    async def play_button_callback(interaction):
        guild = interaction.guild
        member = interaction.user

        # Check if the special role exists, if not, create it
        role = discord.utils.get(guild.roles, name=SPECIAL_ROLE_NAME)
        if role is None:
            role = await guild.create_role(name=SPECIAL_ROLE_NAME)

        # Assign the special role to the member
        await member.add_roles(role)
        await interaction.response.send_message(f"{member.mention}, you have been given the {SPECIAL_ROLE_NAME} role!", ephemeral=True)

        # Check if the special channel exists
        channel = discord.utils.get(guild.channels, name=SPECIAL_CHANNEL_NAME)
        if channel is not None:
            # Update the channel permissions to allow the special role to read messages
            overwrites = channel.overwrites_for(role)
            overwrites.read_messages = True
            await channel.set_permissions(role, overwrite=overwrites)

    play_button.callback = play_button_callback
    view = View()
    view.add_item(play_button)
    await ctx.send("Press the button to play!", view=view)

@bot.command(name='leave')
async def create_leave_button(ctx):
    leave_button = Button(label="Leave", style=discord.ButtonStyle.danger)

    async def leave_button_callback(interaction):
        guild = interaction.guild
        member = interaction.user

        # Ask for confirmation
        confirm_view = View()
        confirm_button = Button(label="Confirm", style=discord.ButtonStyle.danger)
        cancel_button = Button(label="Cancel", style=discord.ButtonStyle.secondary)

        async def confirm_button_callback(confirm_interaction):
            # Remove the special role from the member
            role = discord.utils.get(guild.roles, name=SPECIAL_ROLE_NAME)
            if role in member.roles:
                await member.remove_roles(role)
                await confirm_interaction.response.send_message(f"{member.mention}, you have been removed from the {SPECIAL_ROLE_NAME} role.", ephemeral=True)
            else:
                await confirm_interaction.response.send_message(f"{member.mention}, you do not have the {SPECIAL_ROLE_NAME} role.", ephemeral=True)

        async def cancel_button_callback(cancel_interaction):
            await cancel_interaction.response.send_message("Action cancelled.", ephemeral=True)

        confirm_button.callback = confirm_button_callback
        cancel_button.callback = cancel_button_callback
        confirm_view.add_item(confirm_button)
        confirm_view.add_item(cancel_button)

        await interaction.response.send_message("Are you sure you want to leave the game?", view=confirm_view, ephemeral=True)

    leave_button.callback = leave_button_callback
    view = View()
    view.add_item(leave_button)
    await ctx.send("Press the button to leave the game!", view=view)

@bot.command(name='host')
async def assign_host(ctx):
    guild = ctx.guild

    # Check if the special role exists
    player_role = discord.utils.get(guild.roles, name=SPECIAL_ROLE_NAME)
    if player_role is None:
        await ctx.send(f"The role {SPECIAL_ROLE_NAME} does not exist.")
        return

    # Get all members with the special role
    players = [member for member in guild.members if player_role in member.roles]
    if not players:
        await ctx.send("No players found with the special role.")
        return

    # Select a random player
    host_member = random.choice(players)

    # Check if the host role exists, if not, create it
    host_role = discord.utils.get(guild.roles, name=HOST_ROLE_NAME)
    if host_role is None:
        host_role = await guild.create_role(name=HOST_ROLE_NAME)

    # Assign the host role to the selected member
    await host_member.add_roles(host_role)
    await ctx.send(f"{host_member.mention} has been assigned the {HOST_ROLE_NAME} role!")

@bot.command(name='settings')
async def settings(ctx):
    guild = ctx.guild

    # Check if the host role exists
    host_role = discord.utils.get(guild.roles, name=HOST_ROLE_NAME)
    if host_role is None:
        await ctx.send(f"The role {HOST_ROLE_NAME} does not exist.")
        return

    # Find the current host
    host_member = None
    for member in guild.members:
        if host_role in member.roles:
            host_member = member
            break

    if host_member is None:
        await ctx.send("No host found.")
        return

    # Check if the player role exists
    player_role = discord.utils.get(guild.roles, name=SPECIAL_ROLE_NAME)
    if player_role is None:
        await ctx.send(f"The role {SPECIAL_ROLE_NAME} does not exist.")
        return

    # Get all members with the player role, excluding the host and bots
    players = [member for member in guild.members if player_role in member.roles and host_role not in member.roles and not member.bot]
    if not players:
        await ctx.send("No players found with the special role.")
        return

    # Ask the host to choose the number of impostors
    def check(m):
        return m.author == host_member and m.channel == ctx.channel

    await ctx.send(f"{host_member.mention}, please enter the number of impostors (1 or 2):")
    try:
        msg = await bot.wait_for('message', check=check, timeout=60.0)
        num_impostors = int(msg.content)
        if num_impostors not in [1, 2]:
            await ctx.send("Invalid number of impostors. Please enter 1 or 2.")
            return
    except (ValueError, TimeoutError):
        await ctx.send("Invalid input or timeout. Please try again.")
        return

    # Select impostors and crewmates
    impostors = random.sample(players, num_impostors)
    crewmates = [player for player in players if player not in impostors]

    # Send direct messages to the host
    impostor_names = ', '.join([impostor.name for impostor in impostors])
    crewmate_names = ', '.join([crewmate.name for crewmate in crewmates])
    player_order = '\n'.join([f"{i+1}. {player.name}" for i, player in enumerate(players)])
    await host_member.send(f"Impostors: {impostor_names}\nCrewmates: {crewmate_names}\n\nPlayer Order:\n{player_order}")

@bot.command(name='changehost')
async def change_host(ctx):
    guild = ctx.guild

    # Check if the host role exists
    host_role = discord.utils.get(guild.roles, name=HOST_ROLE_NAME)
    if host_role is None:
        await ctx.send(f"The role {HOST_ROLE_NAME} does not exist.")
        return

    # Find the current host
    current_host = None
    for member in guild.members:
        if host_role in member.roles:
            current_host = member
            break

    if current_host is None:
        await ctx.send("No current host found.")
        return

    # Remove the host role from the current host
    await current_host.remove_roles(host_role)

  
    player_role = discord.utils.get(guild.roles, name=SPECIAL_ROLE_NAME)
    if player_role is None:
        await ctx.send(f"The role {SPECIAL_ROLE_NAME} does not exist.")
        return

    
    players = [member for member in guild.members if player_role in member.roles and host_role not in member.roles and not member.bot]
    if not players:
        await ctx.send("No players found with the special role.")
        return

    # Select a new host
    new_host = random.choice(players)

    # Assign the host role to the new host
    await new_host.add_roles(host_role)
    await ctx.send(f"{new_host.mention} has been assigned the {HOST_ROLE_NAME} role!")

    # Send a direct message to the new host
    await new_host.send("You are the new host")

@bot.command(name='end')
async def end_game(ctx):
    guild = ctx.guild

    # Check if the player role exists
    player_role = discord.utils.get(guild.roles, name=SPECIAL_ROLE_NAME)
    if player_role is None:
        await ctx.send(f"The role {SPECIAL_ROLE_NAME} does not exist.")
        return

    # Get all members with the player role, excluding bots
    players = [member for member in guild.members if player_role in member.roles and not member.bot]
    if not players:
        await ctx.send("No players found with the special role.")
        return

    # Remove the player role from all members
    for player in players:
        await player.remove_roles(player_role)

    await ctx.send("The game has ended and the Player role has been removed from all players.")

@bot.command(name='commands')
async def help_command(ctx):
    help_text = (
        "Here are the available commands:\n"
        "1. `b!play` - Shows the play button to join the game.\n"
        "2. `b!leave` - Shows the leave button to leave the game.\n"
        "3. `b!host` - Assigns a random player as the host.\n"
        "4. `b!settings` - Allows the host to set the number of impostors and shows the player order.\n"
        "5. `b!changehost` - Changes the host to a new random player.\n"
        "6. `b!end` - Ends the game and removes the Player role from all players.\n"
        "7. `b!commands` - Shows this help message."
    )
    await ctx.send(help_text)

# Replace 'YOUR_BOT_TOKEN' with your bot's token
bot.run('')