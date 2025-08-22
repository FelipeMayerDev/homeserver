import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import yt_dlp
import asyncio
from collections import defaultdict
import aiohttp
import json

# Load environment variables
load_dotenv()

# Get the bot token from environment variables
TOKEN = os.getenv('DISCORD_TOKEN')

# Set up bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.voice_states = True

# Create bot instance
bot = commands.Bot(command_prefix='>', intents=intents)

# Music queue and player state
current_players = {}  # {guild_id: player}
queues = defaultdict(list)
leave_tasks = {}  # {guild_id: task}


async def send_webhook_data(data):
    """Send data to the webhook service"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://webhook-service:8000/discord/voice_state",
                json=data,
                headers={"Content-Type": "application/json"}
            ) as response:
                print(f"Webhook response: {response.status}")
    except Exception as e:
        print(f"Error sending to webhook: {e}")


@bot.event
async def on_ready():
    print(f'{bot.user} has logged in!')
    await bot.change_presence(activity=discord.Game(name="Ready to play music!"))


# Store last update time for each user
last_update = {}

@bot.event
async def on_voice_state_update(member, before, after):
    """Notifica apenas quando alguém entra, sai ou troca de canal de voz."""

    # Ignorar bots
    if member.bot:
        return

    # Verificar se houve mudança de canal
    if before.channel == after.channel:
        return  # mutar/desmutar, câmera, etc → ignorar

    # Cooldown de 60 segundos por usuário
    now = asyncio.get_event_loop().time()
    if (last := last_update.get(member.id)) and now - last < 60:
        return

    # Preparar dados para webhook
    users_in_channel = []
    channel_name = None
    event_type = None

    if after.channel:  # entrou ou trocou
        users_in_channel = [
            (m.display_name, m.name.capitalize())
            for m in after.channel.members
            if not m.bot
        ]
        channel_name = after.channel.name

    elif before.channel:
        # Quando alguém sai, ainda queremos mostrar os membros restantes no canal
        users_in_channel = [
            (m.display_name, m.name.capitalize())
            for m in before.channel.members
            if not m.bot
        ]
        channel_name = before.channel.name

    # Determinar evento
    if before.channel is None and after.channel is not None:
        event_type = "joined"
    elif before.channel is not None and after.channel is None:
        event_type = "left"
    elif before.channel and after.channel and before.channel != after.channel:
        event_type = "switched"

    # Se não for um evento válido, não faz nada
    if not event_type:
        return

    webhook_data = {
        "user": (member.display_name, member.name.capitalize()),
        "channel": channel_name,
        "users_in_channel": users_in_channel,
        "event": event_type,
    }

    # Enviar
    await send_webhook_data(webhook_data)

    # Atualizar cooldown
    last_update[member.id] = now

def get_stream_info(url_or_query: str):
    """Extrai informações de áudio (stream_url, título, etc)"""
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url_or_query, download=False)
        return info


async def play_next(ctx):
    """Toca a próxima música da fila"""
    if queues[ctx.guild.id]:
        song = queues[ctx.guild.id].pop(0)
        voice_client = ctx.guild.voice_client

        if voice_client and voice_client.is_connected():
            # Cancel any existing leave task for this guild
            if ctx.guild.id in leave_tasks:
                leave_tasks[ctx.guild.id].cancel()
                del leave_tasks[ctx.guild.id]
                
            source = discord.FFmpegPCMAudio(
                song['stream_url'],
                before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin -extension_picky 0",
                options="-vn -loglevel error"  # Keep 'error' for debugging; switch to 'panic' later if needed
            )

            def after_playing(error):
                if error:
                    print(f"Erro ao tocar: {error}")
                asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

            voice_client.play(source, after=after_playing)

            await bot.change_presence(activity=discord.Game(name=f'{song["title"]} - {song["uploader"]}'[:32])) # Discord username limit is 32 characters
            embed = discord.Embed(
                title="🎶 Now Playing",
                description=f"[{song['title']}]({song['webpage_url']})",
                color=0x00ff00,
            )
            embed.set_author(
                name=f"Requested by {ctx.author.display_name}",
                icon_url=ctx.author.avatar.url
            )
            await ctx.send(embed=embed)

        else:
            queues[ctx.guild.id].clear()
    else:
        voice_client = ctx.guild.voice_client
        if voice_client and voice_client.is_connected() and not voice_client.is_playing():        
            embed = discord.Embed(
                title="✅ Queue Finished",
                description="No more songs in the queue. I'll leave the channel in 5 minutes if nothing is added.",
                color=0xff0000,
            )
            await ctx.send(embed=embed)
            
            # Schedule the bot to leave after 5 minutes
            async def wait_and_leave():
                await asyncio.sleep(300)  # 5 minutes
                if ctx.guild.voice_client and not ctx.guild.voice_client.is_playing():
                    await ctx.guild.voice_client.disconnect()
                    if ctx.guild.id in queues:
                        del queues[ctx.guild.id]
                    if ctx.guild.id in leave_tasks:
                        del leave_tasks[ctx.guild.id]
                        
            leave_tasks[ctx.guild.id] = asyncio.create_task(wait_and_leave())


@bot.command()
async def play(ctx, *, query: str):
    """Reproduz música do YouTube ou adiciona à fila"""
    # Conectar ao canal de voz
    voice_client = ctx.guild.voice_client
    if not voice_client:
        if not ctx.author.voice:
            await ctx.send("❌ Você precisa estar em um canal de voz!")
            return
        voice_client = await ctx.author.voice.channel.connect()
    elif voice_client.channel != ctx.author.voice.channel:
        await voice_client.move_to(ctx.author.voice.channel)

    try:
        print(f"🔎 Procurando: {query}")
        # Se não for link, busca no YouTube
        if not query.startswith("http"):
            info = get_stream_info(f"ytsearch1:{query}")
            if "entries" in info:
                info = info["entries"][0]
        else:
            info = get_stream_info(query)

        # Se for playlist
        if "_type" in info and info["_type"] == "playlist":
            playlist_title = info.get("title", "Unknown Playlist")
            songs_added = 0
            for entry in info["entries"]:
                try:
                    full = get_stream_info(entry["url"])
                    queues[ctx.guild.id].append({
                        "title": full.get("title", "Unknown Title"),
                        "stream_url": full["url"],
                        "webpage_url": full.get("webpage_url", entry["url"]),
                        "uploader": full.get("uploader", "Unknown Uploader"),
                    })
                    # Cancel any existing leave task for this guild when adding a new song
                    if ctx.guild.id in leave_tasks:
                        leave_tasks[ctx.guild.id].cancel()
                        del leave_tasks[ctx.guild.id]
                        songs_added += 1
                except Exception as e:
                    print(f"Erro ao adicionar música: {e}")
                    continue


            embed = discord.Embed(
                title="📂 Playlist Added",
                description=f"Adicionadas {songs_added} músicas de [{playlist_title}]({info.get('webpage_url', '')})",
                color=0x0000ff,
            )
            await ctx.send(embed=embed)

            if not voice_client.is_playing():
                await play_next(ctx)

        # Música única
        else:
            song = {
                "title": info.get("title", "Unknown Title"),
                "stream_url": info["url"],
                "webpage_url": info.get("webpage_url", query),
                "uploader": info.get("uploader", "Unknown Uploader"),
            }

            queues[ctx.guild.id].append(song)

            # Cancel any existing leave task for this guild when adding a new song
            if ctx.guild.id in leave_tasks:
                leave_tasks[ctx.guild.id].cancel()
                del leave_tasks[ctx.guild.id]

            if not voice_client.is_playing():
                await play_next(ctx)
            else:
                embed = discord.Embed(
                    title="➕ Added to Queue",
                    description=f"[{song['title']}]({song['webpage_url']})",
                    color=0x0000ff,
                )
                await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Erro ao processar: `{str(e)}`")
        raise

@bot.command()
async def stop(ctx):
    """Stop playing music and clear the queue"""
    voice_client = ctx.guild.voice_client
    if voice_client and voice_client.is_connected():
        # Clear the queue
        if ctx.guild.id in queues:
            queues[ctx.guild.id].clear()
        
        # Cancel any leave task
        if ctx.guild.id in leave_tasks:
            leave_tasks[ctx.guild.id].cancel()
            del leave_tasks[ctx.guild.id]
        
        # Stop playing
        voice_client.stop()
        await voice_client.disconnect()
        await ctx.send("Stopped playing music and cleared the queue.")
    else:
        await ctx.send("I'm not connected to a voice channel.")

@bot.command()
async def skip(ctx):
    """Skip the current song"""
    voice_client = ctx.guild.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.stop()  # This will trigger the after callback which plays the next song
        await ctx.send("Skipped the current song.")
    else:
        await ctx.send("There's no song currently playing.")

@bot.command()
async def skipall(ctx):
    """Skip all songs in the queue"""
    if ctx.guild.id in queues:
        skipped_count = len(queues[ctx.guild.id])
        queues[ctx.guild.id].clear()
        await ctx.send(f"Skipped {skipped_count} songs from the queue.")
    else:
        await ctx.send("The queue is currently empty.")

@bot.command()
async def queue(ctx):
    """Show the current music queue"""
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        queue_list = ""
        for i, song in enumerate(queues[ctx.guild.id][:10], 1):  # Show only first 10 songs
            queue_list += f"{i}. [{song['title']}]({song['webpage_url']})"

        embed = discord.Embed(title="Music Queue", description=queue_list, color=0x00ff00)
        if len(queues[ctx.guild.id]) > 10:
            embed.set_footer(text=f"And {len(queues[ctx.guild.id]) - 10} more songs...")
        await ctx.send(embed=embed)
    else:
        await ctx.send("The queue is currently empty.")

@bot.command()
async def ping(ctx):
    """Simple ping command to check if bot is responsive"""
    await ctx.send('Pong!')

@bot.command()
async def hello(ctx):
    """Simple hello command"""
    await ctx.send(f'Hello {ctx.author.mention}!')

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Command not found!")

# Run the bot
if __name__ == "__main__":
    if TOKEN is None:
        print("Error: DISCORD_TOKEN not found in environment variables")
    else:
        bot.run(TOKEN)