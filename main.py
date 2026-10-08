import discord
from discord.ext import commands
import json
import os
import yt_dlp

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

def get_level_thresholds():
    thresholds = [30, 70, 150, 300]
    current = 300
    for i in range(4, 20):
        current += 300
        thresholds.append(current)
    return thresholds

LEVEL_THRESHOLDS = get_level_thresholds()
DATA_FILE = "levels.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_user_level(total_msgs):
    level = 0
    for i, thresh in enumerate(LEVEL_THRESHOLDS):
        if total_msgs >= thresh:
            level = i + 1
        else:
            break
    return level

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    data = load_data()
    guild_id = str(message.guild.id) if message.guild else "dm"
    user_id = str(message.author.id)
    if guild_id not in data:
        data[guild_id] = {}
    if user_id not in data[guild_id]:
        data[guild_id][user_id] = {"messages": 0, "level": 0}
    data[guild_id][user_id]["messages"] += 1
    total = data[guild_id][user_id]["messages"]
    old_level = data[guild_id][user_id]["level"]
    new_level = get_user_level(total)
    if new_level > old_level:
        data[guild_id][user_id]["level"] = new_level
        await message.channel.send(f"🎉 ¡Felicidades {message.author.mention}! ¡Subiste al **NIVEL {new_level}**! ({total} mensajes)")
    save_data(data)
    await bot.process_commands(message)

@bot.command(name="nivel")
async def nivel(ctx, member: discord.Member = None):
    member = member or ctx.author
    data = load_data()
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)
    if guild_id in data and user_id in data[guild_id]:
        msgs = data[guild_id][user_id]["messages"]
        lvl = data[guild_id][user_id]["level"]
        next_thresh = LEVEL_THRESHOLDS[lvl] if lvl < len(LEVEL_THRESHOLDS) else LEVEL_THRESHOLDS[-1] + 300
        faltan = next_thresh - msgs
        await ctx.send(f"📊 {member.mention} - Nivel **{lvl}** con **{msgs}** msgs. Te faltan **{faltan}** para nivel {lvl+1}")
    else:
        await ctx.send(f"{member.mention} aún no tiene mensajes.")

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, razon="No razón"):
    try:
        await member.kick(reason=razon)
        await ctx.send(f"👢 {member.mention} fue kickeado por {ctx.author.mention} | Razón: {razon}")
    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.command(name="play", aliases=["p", "musica"])
async def play(ctx, *, busqueda):
    if not ctx.author.voice:
        await ctx.send("¡Debes estar en voz!")
        return
    await ctx.send(f"🔍 Buscando **{busqueda}**...")
    os.makedirs("music", exist_ok=True)
    try:
        YTDL_OPTIONS = {'format': 'bestaudio/best','outtmpl': 'music/%(title)s.%(ext)s','postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}],'noplaylist': True,'quiet': True}
        with yt_dlp.YoutubeDL({'format': 'bestaudio','noplaylist': True,'quiet': True,'default_search': 'ytsearch1'}) as ydl:
            info = ydl.extract_info(f"ytsearch1:{busqueda}", download=False)
            video = info['entries'][0] if 'entries' in info else info
            title = video.get('title', busqueda)
            url = video.get('webpage_url')
        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=True)
            mp3_file = ydl.prepare_filename(info).rsplit('.',1)[0]+".mp3"
        if os.path.exists(mp3_file) and os.path.getsize(mp3_file)/(1024*1024) < 25:
            await ctx.send(f"🎵 **{title}** - pedido por {ctx.author.mention}", file=discord.File(mp3_file))
        channel = ctx.author.voice.channel
        vc = ctx.voice_client or await channel.connect()
        if vc.is_playing(): vc.stop()
        import glob
        latest = max(glob.glob("music/*.mp3"), key=os.path.getctime)
        vc.play(discord.FFmpegPCMAudio(latest))
        await ctx.send(f"▶️ Reproduciendo: **{title}**")
    except Exception as e:
        await ctx.send(f"Error: {e}")

bot.run(os.getenv("DISCORD_TOKEN"))
