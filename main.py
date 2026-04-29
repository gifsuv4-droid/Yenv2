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

def can_act(a, t):
    if not a or not t:
        return False
    return a.guild_permissions.administrator or a.top_role > t.top_role

# ================= GROQ AI =================
def ask_ai(uid, text):
    if not GROQ_KEY:
        return "AI not configured"

    history = memory.get(str(uid), [])[-6:]

    # 🔥 SAVAGE TIKTOK PERSONALITY (SAFE)
    messages = [{
        "role": "system",
        "content": (
            "You are Yen, a sarcastic TikTok-style Discord bot. "
            "Be witty, slightly savage, and playful. "
            "Roast lightly but NEVER use hate speech, slurs, or real harassment. "
            "Keep replies short (1-2 sentences max). "
            "Use casual internet tone like 'bro', 'nah', 'fr', '💀'."
        )
    }]

    if history:
        messages.append({
            "role": "user",
            "content": "Previous context: " + " | ".join(history[-3:])
        })

    messages.append({"role": "user", "content": text})

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": messages,
                "max_tokens": 50,
                "temperature": 0.9
            },
            timeout=10
        )

        print("STATUS:", r.status_code)
        print("RESPONSE:", r.text)

        if r.status_code != 200:
            return f"AI HTTP ERROR {r.status_code}"

        data = r.json()

        if "error" in data:
            return f"AI ERROR: {data['error'].get('message', 'unknown')}"

        choices = data.get("choices")
        if not choices:
            return "AI returned no response"

        return choices[0].get("message", {}).get("content", "AI empty response")

    except Exception as e:
        print("EXCEPTION:", str(e))
        return "AI offline 💀"

# ================= MESSAGE =================
@bot.event
async def on_message(message):

    if not secure(message):
        return

    await bot.process_commands(message)

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

# ================= READY =================
@bot.event
async def on_ready():
    global IS_LEADER
    ch = bot.get_channel(LOCK_CHANNEL_ID)

    if ch:
        await ch.send("BOOTING...")
        await asyncio.sleep(1)
        await ch.send("AI CORE INITIALIZED")
        await asyncio.sleep(1)
        await ch.send("MODULE CHECK COMPLETE")
        await asyncio.sleep(1)

        IS_LEADER = True
        await ch.send("LOCK IN COMPLETE — YEN V9.3 ONLINE")

# ================= DASHBOARD =================
class Dashboard(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.page = "home"
        self.target_user = None

    def embed(self, g):
        ai_status = "🟢 ONLINE" if GROQ_KEY else "🔴 OFFLINE"

        e = discord.Embed(
            title="CONTROL CORE V9.3",
            description="```NEON SYSTEM```",
            color=discord.Color.purple()
        )

        if self.page == "home":
            e.add_field(name="AI", value=ai_status)
            e.add_field(name="Servers", value=len(bot.guilds))
            e.add_field(name="Memory Users", value=len(memory))

        elif self.page == "moderation":
            e.add_field(name="Target User", value=str(self.target_user) if self.target_user else "None")

        elif self.page == "logs":
            logs_data = logs.get(str(g.id), [])[-8:] if g else []
            e.description = "\n".join(logs_data) if logs_data else "No logs"

        return e

    @discord.ui.button(label="HOME")
    async def home(self, i: discord.Interaction, button: discord.ui.Button):
        self.page = "home"
        await i.response.edit_message(embed=self.embed(i.guild), view=self)

    @discord.ui.button(label="MOD")
    async def mod(self, i: discord.Interaction, button: discord.ui.Button):
        self.page = "moderation"
        await i.response.edit_message(embed=self.embed(i.guild), view=self)

    @discord.ui.button(label="LOGS")
    async def logs_btn(self, i: discord.Interaction, button: discord.ui.Button):
        self.page = "logs"
        await i.response.edit_message(embed=self.embed(i.guild), view=self)

    @discord.ui.button(label="BAN")
    async def ban(self, i: discord.Interaction, button: discord.ui.Button):
        if not self.target_user:
            return await i.response.send_message("no user selected", ephemeral=True)
        try:
            await self.target_user.ban()
            log(i.guild, f"BAN {self.target_user}")
            await i.response.send_message("banned", ephemeral=True)
        except:
            await i.response.send_message("failed", ephemeral=True)

    @discord.ui.button(label="KICK")
    async def kick(self, i: discord.Interaction, button: discord.ui.Button):
        if not self.target_user:
            return await i.response.send_message("no user selected", ephemeral=True)
        try:
            await self.target_user.kick()
            log(i.guild, f"KICK {self.target_user}")
            await i.response.send_message("kicked", ephemeral=True)
        except:
            await i.response.send_message("failed", ephemeral=True)

# ================= COMMAND =================
@bot.command()
@commands.has_permissions(administrator=True)
async def dashboard(ctx, user: discord.Member = None):
    view = Dashboard()
    view.target_user = user
    await ctx.send("CONTROL PANEL OPENED", view=view)

# ================= RUN =================
bot.run(TOKEN)