import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import os
import requests
from mojang import API
from datetime import datetime
import asyncio

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='%dev%/', intents=intents)
mojang_api = API()

load_dotenv()
TOKEN = os.getenv('TOKEN')
APIKEY = os.getenv('APIKEY')
INVITEURL = os.getenv('INVITEURL')

default_headers = {
    'API-Key': APIKEY,
    'Content-Type': 'application/json'
}

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    
async def send_ratelimit_embed(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Rate Limit Exceeded",
        description="We are being rate limited. Please try again later.",
        color=discord.Color.red()
    )
    embed.set_footer(text="Hypixel API Bot is not affiliated or endorsed by Hypixel")
    await send_interaction_response(interaction, content='', embed=embed)

async def get_uuid(plr_name):
    uuid = await bot.loop.run_in_executor(None, mojang_api.get_uuid, plr_name)
    return uuid

USER_ID = 827176666320207872

# Load settings from settings.txt
def load_settings():
    settings = {}
    try:
        with open("settings.txt", "r") as file:
            for line in file:
                guild_id, setting = line.strip().split(":")
                settings[int(guild_id)] = setting.lower() == "false"  # Inverting the logic here
    except FileNotFoundError:
        pass
    return settings

# Save settings to settings.txt
def save_settings(settings):
    with open("settings.txt", "w") as file:
        for guild_id, setting in settings.items():
            file.write(f"{guild_id}:{str(setting).lower()}\n")

settings = load_settings()

# Modify the send_interaction_response function
async def send_interaction_response(interaction, content, **kwargs):
    if interaction:
        guild_id = interaction.guild_id
        hide_results = settings.get(guild_id, False)
        if hide_results:
            await interaction.response.send_message(content, ephemeral=True, **kwargs)
        else:
            await interaction.response.send_message(content, **kwargs)
    else:
        print("Interaction is None. Cannot send message.")


# Function to check if the user is you
def is_bot_owner(user_id):
    return user_id == USER_ID

@bot.tree.command(name='restart', description='OWNER ONLY - Restart the bot - OWNER ONLY')
@app_commands.check(lambda i: is_bot_owner(i.user.id))
async def restart(interaction: discord.Interaction):
    await interaction.response.send_message("Restarting bot...", ephemeral=True)
    await bot.close()
    
async def update_help_commands():
    global bot
    for guild in bot.guilds:
        commands = await guild.fetch_commands()
        help_content = "\n".join([f"`/{cmd.name}` - {cmd.description}" for cmd in commands])
        # Assuming you have a slash command named 'help' already registered
        help_command = await guild.fetch_command('help')
        await help_command.edit(description=f"Help: {help_content}")


# Modify each prefix command to use discord.Interaction and be owner-only
@bot.tree.command(name='blacklistuser', description='OWNER ONLY - Blacklist a user - OWNER ONLY')
@app_commands.check(lambda i: is_bot_owner(i.user.id))
@app_commands.describe(user_id="The ID of the user to blacklist")
async def blacklist_user(interaction: discord.Interaction, user_id: int):
    response = await interaction.response.send_message(f"Blacklisting user with ID {user_id}.", ephemeral=True)
    with open("blacklist.txt", "a") as file:
        file.write(str(user_id) + "\n")
    await response.edit(content=f"User with ID {user_id} has been added to the blacklist.")

@bot.tree.command(name='removeblacklistuser', description='OWNER ONLY - Remove a user from blacklist - OWNER ONLY')
@app_commands.check(lambda i: is_bot_owner(i.user.id))
@app_commands.describe(user_id="The ID of the user to remove from blacklist")
async def remove_blacklist_user(interaction: discord.Interaction, user_id: int):
    response = await interaction.response.send_message(f"Removing user with ID {user_id} from blacklist.", ephemeral=True)
    with open("blacklist.txt", "r") as file:
        lines = file.readlines()
    with open("blacklist.txt", "w") as file:
        for line in lines:
            if line.strip() != str(user_id):
                file.write(line)
    await response.edit(content=f"User with ID {user_id} has been removed from the blacklist.")

@bot.tree.command(name='sync', description='OWNER ONLY - Sync command tree - OWNER ONLY')
@app_commands.check(lambda i: is_bot_owner(i.user.id))
async def sync(interaction: discord.Interaction):
    await bot.tree.sync()
    await interaction.response.send_message('Command tree synced. This may take up to an hour to show up.', ephemeral=True)

@bot.tree.command(name='ping', description='OWNER ONLY - Check bot latency - OWNER ONLY')
@app_commands.check(lambda i: is_bot_owner(i.user.id))
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"{bot.latency}", ephemeral=True)
    
def is_blacklisted(user_id):
    with open("blacklist.txt", "r") as file:
        blacklist = file.read().splitlines()
    return str(user_id) in blacklist
@bot.tree.command(name='invite', description='Get the invite link for the bot')
async def invite(interaction: discord.Interaction):
    # Invite link for the bot
    invite_link = INVITEURL
    # Create an embed for the invite link
    embed = discord.Embed(title="Bot Invite Link", description="Click [here](" + invite_link + ") to invite the bot to your server!", color=discord.Color.blue())
    embed.set_footer(text="Hypixel API Bot is not affiliated or endorsed by Hypixel")
    
    try:
        # Send the embed via DM
        await interaction.user.send(embed=embed)
        await send_interaction_response(interaction, "Sent you a DM with the invite link!")
    except discord.Forbidden:
        # If unable to DM, send in the channel
        await send_interaction_response(interaction,":warning: **I have tried sending you an DM with the invite, however you have [your dms disabled](https://support.discord.com/hc/en-us/articles/217916488-Blocking-Privacy-Settings#h_01HD4ANCTGAS1RCVZVY1F4CHGS). You may also right click the server icon, press Privacy Settings, then activate `Direct Messages`.** :warning:", ephemeral=True)
        await send_interaction_response(interaction,embed=embed, ephemeral=True)


@bot.tree.command(name='banstats', description='See stats about the recent bans')
async def banstats(interaction: discord.Interaction):
    if is_blacklisted(interaction.user.id):
        await interaction.response.send_message("You're banned from using this bot. To appeal join this discord server `https://discord.gg/nUe7PkKqxm` and go to the `support` channel.", ephemeral=True)
        return
    request = requests.get("https://api.hypixel.net/v2/punishmentstats", headers=default_headers)
    data = request.json()
    if request.status_code == 429:  # Rate limit exceeded
        await send_ratelimit_embed(interaction)
        return
    elif request.status_code == 200:
        embed = discord.Embed(title="Ban Stats", color=discord.Color.green())
        embed.add_field(name="Watchdog", value=f"Last Day: {data['watchdog_rollingDaily']}\nTotal: {data['watchdog_total']}", inline=False)
        embed.add_field(name="Staff", value=f"Last Day: {data['staff_rollingDaily']}\nTotal: {data['staff_total']}", inline=False)
        embed.add_field(name="GLOBAL", value=f"Last Day: {data['watchdog_rollingDaily'] + data['staff_rollingDaily']}\nTotal: {data['watchdog_total'] + data['staff_total']}", inline=False)
        embed.set_footer(text="Hypixel API Bot is not affiliated or endorsed by Hypixel")
        await send_interaction_response(interaction, content='', embed=embed)
    else:
        await send_interaction_response(interaction, content=f"An error has occurred: \nStatus code: {request.status_code} \nSuccess: {data['success']} \nCause: {data['cause']}")

@bot.tree.command(name='playerinfo', description='See information about a specific player')
@app_commands.describe(plrname="The player name to get information from")
async def playerinfo(interaction: discord.Interaction, plrname: str):
    if is_blacklisted(interaction.user.id):
        await interaction.response.send_message("You're banned from using this bot. To appeal join this discord server `https://discord.gg/nUe7PkKqxm` and go to the `support` channel.", ephemeral=True)
        return
    uuid = await get_uuid(plrname)
    request = requests.get(f"https://api.hypixel.net/v2/player?uuid={uuid}", headers=default_headers)
    data = request.json()
    if request.status_code == 429:  # Rate limit exceeded
        await send_ratelimit_embed(interaction)
        return
    elif request.status_code == 200:
        embed = discord.Embed(title="Player Info", color=discord.Color.green())
        embed.add_field(name="Player Name", value=f"{data['player']['displayname']}", inline=False)
        if 'rank' in data['player']:
            rank = data['player']['rank']
        elif 'newPackageRank' in data['player']:
            rank = data['player']['newPackageRank']
        else:
            rank = "Error, highly likely to be regular rank"
        embed.add_field(name="Rank", value=rank, inline=False)
        timestamp_in_seconds_first_login = data['player']['firstLogin'] / 1000
        date_first_login = datetime.utcfromtimestamp(timestamp_in_seconds_first_login)
        embed.add_field(name="First Login", value=f"{date_first_login}", inline=False)
        embed.set_footer(text="Hypixel API Bot is not affiliated or endorsed by Hypixel")
        await send_interaction_response(interaction, content='', embed=embed)
    else:
        await send_interaction_response(interaction, content=f"An error has occurred: \nStatus code: {request.status_code} \nSuccess: {data['success']} \nCause: {data['cause']}")

@bot.tree.command(name='recentgames', description='Retrieve recent games of a player')
@app_commands.describe(plrname="The player name", count="The number of recent games to retrieve (1-50)")
async def recentgames(interaction: discord.Interaction, plrname: str, count: int):
    if is_blacklisted(interaction.user.id):
        await interaction.response.send_message("You're banned from using this bot. To appeal join this discord server `https://discord.gg/nUe7PkKqxm` and go to the `support` channel.", ephemeral=True)
        return
    if count < 1:
        count = 1
    elif count > 50:
        count = 50
    uuid = await get_uuid(plrname)
    request = requests.get(f"https://api.hypixel.net/v2/recentgames?uuid={uuid}", headers=default_headers)
    data = request.json()
    if request.status_code == 429:  # Rate limit exceeded
        await send_ratelimit_embed(interaction)
        return
    elif request.status_code == 200:
        games = data.get("games", [])
        if not games:
            embed = discord.Embed(title="Recent Games", color=discord.Color.red())
            embed.description = "No recent games were found from that player."
            embed.set_footer(text="Hypixel API Bot is not affiliated or endorsed by Hypixel")
            await send_interaction_response(interaction, content='', embed=embed)
            return
        games = games[:count]
        embed = discord.Embed(title="Recent Games", color=discord.Color.green())
        for game in games:
            start_time = datetime.utcfromtimestamp(game["date"] / 1000)
            end_time = datetime.utcfromtimestamp(game["ended"] / 1000)
            game_type = game["gameType"]
            embed.add_field(name="Game Type", value=game_type, inline=False)
            embed.add_field(name="Start Time", value=start_time, inline=False)
            embed.add_field(name="End Time", value=end_time, inline=False)
            embed.add_field(name="\u200b", value="", inline=False)  # Add empty field for spacing
        embed.set_footer(text="Hypixel API Bot is not affiliated or endorsed by Hypixel")
        await send_interaction_response(interaction, content='', embed=embed)
        if len(games) < count:
            embed = discord.Embed(title="Recent Games", color=discord.Color.green())
            embed.description = "No more recent games were found from that player."
            embed.set_footer(text="Hypixel API Bot is not affiliated or endorsed by Hypixel")
            await send_interaction_response(interaction, content='', embed=embed)
    else:
        await send_interaction_response(interaction, content=f"An error has occurred: \nStatus code: {request.status_code} \nSuccess: {data['success']} \nCause: {data['cause']}")

@bot.tree.command(name='status', description='Retrieve status of a player')
@app_commands.describe(plrname="The player name")
async def status(interaction: discord.Interaction, plrname: str):
    if is_blacklisted(interaction.user.id):
        await interaction.response.send_message("You're banned from using this bot. To appeal join this discord server `https://discord.gg/nUe7PkKqxm` and go to the `support` channel.", ephemeral=True)
        return
    uuid = await get_uuid(plrname)
    request = requests.get(f"https://api.hypixel.net/v2/status?uuid={uuid}", headers=default_headers)
    data = request.json()
    if request.status_code == 429:  # Rate limit exceeded
        await send_ratelimit_embed(interaction)
        return
    elif request.status_code == 200:
        embed = discord.Embed(title="Player Status", color=discord.Color.green())
        if data['session']['online']:
            embed.add_field(name="Online", value=f"{data['session']['online']}", inline=False)
            embed.add_field(name="Game Type", value=f"{data['session']['gameType']}", inline=False)
            embed.add_field(name="Mode", value=f"{data['session']['mode']}", inline=False)
            if 'map' in data['session']:
                map_value = data['session']['map']
            else:
                map_value = "NONE"
            embed.add_field(name="Map", value=map_value, inline=False)
            embed.set_footer(text="Hypixel API Bot is not affiliated or endorsed by Hypixel")
        else:
            embed.add_field(name="Online", value=f"{data['session']['online']}", inline=False)
            embed.set_footer(text="Hypixel API Bot is not affiliated or endorsed by Hypixel")
        await send_interaction_response(interaction, content='', embed=embed)
    else:
        await send_interaction_response(interaction, content=f"An error has occurred: \nStatus code: {request.status_code} \nSuccess: {data['success']} \nCause: {data['cause']}")


# @bot.tree.command(name='guildinfo', description='Get information about a guild')
# @app_commands.describe(player="The player name", id="The guild ID", name="The guild name")
async def guildinfo(interaction: discord.Interaction, player: str = None, id: str = None, name: str = None):
    # Validate parameters
    if not any([player, id, name]):
        await send_interaction_response(interaction,"Please provide at least one parameter: player, id, or name.")
        return
    if is_blacklisted(interaction.user.id):
        await interaction.response.send_message("You're banned from using this bot. To appeal join this discord server `https://discord.gg/nUe7PkKqxm` and go to the `support` channel.", ephemeral=True)
        return
    # Construct URL based on provided parameters
    url = "https://api.hypixel.net/v2/guild?"
    if player:
        uuid = await get_uuid(player)
        url += f"player={uuid}"
    elif id:
        url += f"id={id}"
    elif name:
        url += f"name={name}"

    # Execute HTTP request
    request = requests.get(url)

    if request.status_code == 429:  # Rate limit exceeded
        await send_ratelimit_embed(interaction)
        return
    elif request.status_code == 200:
        data = request.json()
        guild_info = data.get("guild")

        if guild_info:
            embed = discord.Embed(title="Guild Information", color=discord.Color.blue())
            embed.add_field(name="Guild Name", value=guild_info.get("name", "Not Found"), inline=False)
            
            # Fetch members and their ranks
            members_info = ""
            for member in guild_info.get("members", []):
                member_name = member.get("uuid")
                member_rank = member.get("rank")
                members_info += f"{member_name} - {member_rank}\n"
            embed.add_field(name="Members and Ranks", value=members_info or "No Members", inline=False)

            # Online players count
            online_players = guild_info.get("achievements", {}).get("ONLINE_PLAYERS", 0)
            embed.add_field(name="Online Players", value=online_players, inline=False)

            # Guild experience by game type
            exp_by_game_type = guild_info.get("guildExpByGameType", {})
            exp_info = "\n".join([f"{key}: {value}" for key, value in exp_by_game_type.items()])
            embed.add_field(name="Guild Experience by Game Type", value=exp_info or "No Data", inline=False)

            await send_interaction_response(interaction,embed=embed)
        else:
            await send_interaction_response(interaction,"Guild not found.")
    else:
        await send_interaction_response(interaction,f"An error has occurred: \nStatus code: {request.status_code} \nSuccess: {data['success']} \nCause: {data['cause']}")

# @bot.tree.command(name="cmds", description="Display all available commands")
async def cmds(interaction: discord.Interaction):
    if is_blacklisted(interaction.user.id):
        await interaction.response.send_message("You're banned from using this bot. To appeal join this discord server `https://discord.gg/nUe7PkKqxm` and go to the `support` channel.", ephemeral=True)
        return
    commands = await bot.fetch_guild_commands(interaction.guild.id)
    help_content = "\n".join([f"`/{cmd.name}` - {cmd.description}" for cmd in commands])
    embed = discord.Embed(title="Available Commands", description=help_content, color=discord.Color.green())
    await send_interaction_response(interaction,embed=embed)
    
# @bot.tree.command(name="help", description="Display all available commands")
async def help(interaction: discord.Interaction):
    await cmds(interaction)

@bot.tree.command(name="servers", description="Gets the amount of servers the bot is in.")
async def servers(interaction: discord.Interaction):
    if is_blacklisted(interaction.user.id):
        await interaction.response.send_message("You're banned from using this bot. To appeal join this discord server `https://discord.gg/nUe7PkKqxm` and go to the `support` channel.", ephemeral=True)
        return
    num_servers = len(bot.guilds)
    await send_interaction_response(interaction, content=f"This bot is in {num_servers} servers!", ephemeral=True)

# Add the settings command
@bot.tree.command(name='settings', description='Modify bot settings')
@app_commands.describe(visibility="Toggle visibilty results")
async def settings_command(interaction: discord.Interaction, visibility: bool = None):
    global settings
    if interaction.user:
        # Debug output: Print user's permissions
        print("User is guild owner:", interaction.user.id == interaction.guild.owner_id)
        print("User has administrator permission:", interaction.user.guild_permissions.administrator)

        if visibility is None:
            # Display the current setting
            current_setting = settings.get(interaction.guild_id, True)
            await interaction.response.send_message(f"Results are currently {'invisible' if current_setting else 'visible'}.", ephemeral=True)
        else:
            if interaction.user.id == interaction.guild.owner_id or interaction.user.guild_permissions.administrator:
                settings[interaction.guild_id] = not visibility  # Inverted logic here
                save_settings(settings)
                await interaction.response.send_message(f"Results are now {'invisible' if not visibility else 'visible'}.", ephemeral=True)  # Inverted logic here
            else:
                await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
    else:
        await interaction.response.send_message("Invalid user detected.", ephemeral=True)

bot.run(TOKEN)
