import discord
from discord.ext import commands
import os, json, time, asyncio, requests, unicodedata

# ================= CONFIG =================
TOKEN = os.getenv("TOKEN")
GROQ_KEY = os.getenv("GROQ_KEY")

if not TOKEN:
    raise ValueError("Missing TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="yen ", intents=intents)

SAFE = discord.AllowedMentions(everyone=False, roles=False, users=True)

CREATOR_ID = 1383111113016872980
LOCK_CHANNEL_ID = 1446191246828634223

# ================= SAFE FILE SYSTEM =================
FILES = {
    "auto": "auto_roles.json",
    "filter": "filters.json",
    "memory": "memory.json",
    "logs": "logs.json"
}

def load(f):
    try:
        with open(f, "r") as x:
            return json.load(x)
    except:
        return {}

def save(f, d):
    try:
        with open(f, "w") as x:
            json.dump(d, x, indent=2)
    except:
        pass

auto_roles = load(FILES["auto"])
filters = load(FILES["filter"])
memory = load(FILES["memory"])
logs = load(FILES["logs"])

# ================= STATE =================
msg_lock = set()
cooldowns = {}

# prevents memory leak (auto cleanup)
MAX_LOCK_SIZE = 2500

# ================= UTIL =================
def norm(t):
    return unicodedata.normalize("NFKD", t).encode("ascii","ignore").decode()

def log(guild, text):
    if not guild:
        return
    gid = str(guild.id)
    logs.setdefault(gid, [])
    logs[gid].append(f"{time.strftime('%H:%M:%S')} | {text}")
    logs[gid] = logs[gid][-20:]
    save(FILES["logs"], logs)

async def safe_send(ch, msg):
    try:
        return await ch.send(msg, allowed_mentions=SAFE)
    except:
        return

# ================= SECURITY CORE =================
def secure(msg):
    if not msg or not msg.guild:
        return False

    if msg.author.bot:
        return False

    # duplicate message protection
    if msg.id in msg_lock:
        return False

    msg_lock.add(msg.id)

    if len(msg_lock) > MAX_LOCK_SIZE:
        msg_lock.clear()

    return True

def is_creator(u):
    return u and u.id == CREATOR_ID

def can_act(a, t):
    if not a or not t:
        return False
    if is_creator(a):
        return True
    return a.top_role > t.top_role

def bot_can(t, g):
    if not g or not t:
        return False
    return g.me.top_role > t.top_role

# ================= GROQ AI =================
def ask_ai(uid, text):
    history = memory.get(str(uid), [])[-6:]

    messages = [{"role": "system", "content": "short chaotic assistant max 40 tokens"}]

    for h in history:
        messages.append({"role": "user", "content": h})

    messages.append({"role": "user", "content": text})

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
            json={
                "model": "llama3-70b-8192",
                "messages": messages,
                "max_tokens": 40,
                "temperature": 0.8
            },
            timeout=10
        )

        return r.json()["choices"][0]["message"]["content"]

    except:
        return "AI offline 💀"

# ================= DASHBOARD =================
class Dashboard(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.page = "home"
        self.target_user = None

    def embed(self, g):

        ai = "🟢 ONLINE" if GROQ_KEY else "🔴 OFFLINE"

        e = discord.Embed(
            title="🟣 YEN CONTROL CORE V9.1",
            description="```NEON SYSTEM STABLE BUILD```",
            color=discord.Color.purple()
        )

        if self.page == "home":
            e.add_field(name="AI", value=ai, inline=True)
            e.add_field(name="Servers", value=len(bot.guilds), inline=True)
            e.add_field(name="Memory", value=len(memory), inline=True)

        elif self.page == "moderation":
            e.add_field(
                name="Target User",
                value=str(self.target_user) if self.target_user else "None selected",
                inline=False
            )

        elif self.page == "logs":
            e.description = "\n".join(logs.get(str(g.id), [])[-8:]) or "No logs"

        return e

    @discord.ui.button(label="HOME")
    async def home(self, i, b):
        self.page = "home"
        await i.response.edit_message(embed=self.embed(i.guild), view=self)

    @discord.ui.button(label="MOD")
    async def mod(self, i, b):
        self.page = "moderation"
        await i.response.edit_message(embed=self.embed(i.guild), view=self)

    @discord.ui.button(label="LOGS")
    async def logs_btn(self, i, b):
        self.page = "logs"
        await i.response.edit_message(embed=self.embed(i.guild), view=self)

    # SAFE MODERATION BUTTONS
    @discord.ui.button(label="BAN")
    async def ban(self, i, b):

        if not i.user.guild_permissions.administrator:
            return await i.response.send_message("no permission", ephemeral=True)

        if not self.target_user:
            return await i.response.send_message("no user selected", ephemeral=True)

        if not can_act(i.user, self.target_user):
            return await i.response.send_message("role too low", ephemeral=True)

        try:
            await self.target_user.ban()
            log(i.guild, f"BAN {self.target_user}")
            await i.response.send_message("banned", ephemeral=True)
        except:
            await i.response.send_message("failed", ephemeral=True)

    @discord.ui.button(label="KICK")
    async def kick(self, i, b):

        if not i.user.guild_permissions.administrator:
            return await i.response.send_message("no permission", ephemeral=True)

        if not self.target_user:
            return await i.response.send_message("no user selected", ephemeral=True)

        if not can_act(i.user, self.target_user):
            return await i.response.send_message("role too low", ephemeral=True)

        try:
            await self.target_user.kick()
            log(i.guild, f"KICK {self.target_user}")
            await i.response.send_message("kicked", ephemeral=True)
        except:
            await i.response.send_message("failed", ephemeral=True)

# ================= READY =================
@bot.event
async def on_ready():

    ch = bot.get_channel(LOCK_CHANNEL_ID)

    if ch:
        await ch.send("🔐 LOCK IN, YEN V9.1 HYBRID ONLINE")
        await ch.send(embed=discord.Embed(
            title="SYSTEM READY",
            description="AI + DASHBOARD + MODERATION ACTIVE",
            color=discord.Color.purple()
        ), view=Dashboard())

# ================= MESSAGE =================
@bot.event
async def on_message(message):

    if not secure(message):
        return

    msg = norm(message.content.lower())

    # FILTER SYSTEM
    bad = filters.get(str(message.guild.id), [])

    for w in bad:
        if w in msg:
            try:
                await message.delete()
            except:
                pass
            log(message.guild, f"FILTER {message.author}")
            return await message.channel.send("blocked ⚠️")

    # AI SYSTEM
    if msg.startswith("hey yen"):

        uid = str(message.author.id)

        memory.setdefault(uid, [])
        memory[uid].append(message.content)
        memory[uid] = memory[uid][-6:]

        save(FILES["memory"], memory)

        if uid in cooldowns and time.time() - cooldowns[uid] < 2:
            return

        cooldowns[uid] = time.time()

        reply = ask_ai(uid, message.content)

        log(message.guild, f"AI {message.author}")

        return await message.reply(reply, allowed_mentions=SAFE)

    await bot.process_commands(message)

# ================= DASHBOARD COMMAND =================
@bot.command()
@commands.has_permissions(administrator=True)
async def dashboard(ctx, user: discord.Member = None):

    view = Dashboard()
    view.target_user = user

    await ctx.send(embed=view.embed(ctx.guild), view=view)

# ================= RUN =================
bot.run(TOKEN)