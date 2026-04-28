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

# ================= LOCK SYSTEM =================
IS_LEADER = False

# ================= FILE SYSTEM =================
FILES = {
    "auto": "auto_roles.json",
    "filter": "filters.json",
    "memory": "memory.json",
    "logs": "logs.json"
}

def load(f):
    try:
        return json.load(open(f, "r"))
    except:
        return {}

def save(f, d):
    try:
        json.dump(d, open(f, "w"), indent=2)
    except:
        pass

auto_roles = load(FILES["auto"])
filters = load(FILES["filter"])
memory = load(FILES["memory"])
logs = load(FILES["logs"])

# ================= STATE =================
msg_lock = set()
cooldowns = {}
MAX_LOCK = 2500

# ================= UTIL =================
def norm(t):
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()

def log(guild, text):
    if not guild:
        return
    gid = str(guild.id)
    logs.setdefault(gid, [])
    logs[gid].append(f"{time.strftime('%H:%M:%S')} | {text}")
    logs[gid] = logs[gid][-20:]
    save(FILES["logs"], logs)

# ================= SECURITY =================
def secure(msg):
    if not msg or not msg.guild:
        return False
    if msg.author.bot:
        return False

    if msg.id in msg_lock:
        return False

    msg_lock.add(msg.id)

    if len(msg_lock) > MAX_LOCK:
        msg_lock.clear()

    return True

def is_creator(u):
    return u and u.id == CREATOR_ID

def can_act(a, t):
    if not a or not t:
        return False
    return is_creator(a) or a.top_role > t.top_role

# ================= GROQ AI =================
def ask_ai(uid, text):
    if not GROQ_KEY:
        return "AI not configured"

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

        data = r.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "AI error")

    except:
        return "AI offline 💀"

# ================= DASHBOARD =================
class Dashboard(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.page = "home"
        self.target_user = None

    def embed(self, interaction: discord.Interaction):

        g = interaction.guild
        ai_status = "🟢 ONLINE" if GROQ_KEY else "🔴 OFFLINE"

        e = discord.Embed(
            title="🟣 YEN CONTROL CORE V9.3",
            description="```NEON SYSTEM STABLE BUILD```",
            color=discord.Color.purple()
        )

        if self.page == "home":
            e.add_field(name="AI", value=ai_status, inline=True)
            e.add_field(name="Servers", value=len(bot.guilds), inline=True)
            e.add_field(name="Memory Users", value=len(memory), inline=True)

        elif self.page == "moderation":
            e.add_field(
                name="Target User",
                value=str(self.target_user) if self.target_user else "None selected",
                inline=False
            )

        elif self.page == "logs":
            if g:
                logs_data = logs.get(str(g.id), [])[-8:]
                e.description = "\n".join(logs_data) if logs_data else "No logs"
            else:
                e.description = "No guild context"

        return e

    # NAV BUTTONS
    @discord.ui.button(label="HOME")
    async def home(self, i: discord.Interaction, button: discord.ui.Button):
        self.page = "home"
        await i.response.edit_message(embed=self.embed(i), view=self)

    @discord.ui.button(label="MOD")
    async def mod(self, i: discord.Interaction, button: discord.ui.Button):
        self.page = "moderation"
        await i.response.edit_message(embed=self.embed(i), view=self)

    @discord.ui.button(label="LOGS")
    async def logs_btn(self, i: discord.Interaction, button: discord.ui.Button):
        self.page = "logs"
        await i.response.edit_message(embed=self.embed(i), view=self)

    # MOD ACTIONS
    @discord.ui.button(label="BAN")
    async def ban(self, i: discord.Interaction, button: discord.ui.Button):

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
    async def kick(self, i: discord.Interaction, button: discord.ui.Button):

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

    global IS_LEADER
    ch = bot.get_channel(LOCK_CHANNEL_ID)

    if ch:
        await ch.send("🔐 SYSTEM BOOTING...")
        await asyncio.sleep(1)
        await ch.send("🧠 AI CORE INITIALIZED")
        await asyncio.sleep(1)
        await ch.send("⚙️ MODULE CHECK COMPLETE")
        await asyncio.sleep(1)

        IS_LEADER = True

        await ch.send("🔐 LOCK IN COMPLETE — YEN V9.3 ONLINE")

# ================= MESSAGE =================
@bot.event
async def on_message(message):

    if not secure(message):
        return

    if not IS_LEADER:
        return

    msg = norm(message.content.lower())

    bad = filters.get(str(message.guild.id), [])

    for w in bad:
        if w in msg:
            try:
                await message.delete()
            except:
                pass
            log(message.guild, f"FILTER {message.author}")
            return await message.channel.send("blocked ⚠️")

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

    await ctx.send("🟣 CONTROL PANEL OPENED", view=view)

# ================= RUN =================
bot.run(TOKEN)