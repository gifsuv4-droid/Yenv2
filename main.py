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

IS_LEADER = False

FILES = {
    "memory": "memory.json",
    "logs": "logs.json",
    "ignore": "ignore_roles.json"
}

def load(f):
    try: return json.load(open(f))
    except: return {}

def save(f, d):
    try: json.dump(d, open(f, "w"), indent=2)
    except: pass

memory = load(FILES["memory"])
logs = load(FILES["logs"])
ignore_roles = load(FILES["ignore"])

msg_lock = set()
cooldowns = {}

# ================= UTIL =================
def norm(t):
    return unicodedata.normalize("NFKD", t).encode("ascii","ignore").decode()

def log(g, text):
    if not g: return
    gid = str(g.id)
    logs.setdefault(gid, [])
    logs[gid].append(f"{time.strftime('%H:%M:%S')} | {text}")
    logs[gid] = logs[gid][-20:]
    save(FILES["logs"], logs)

def secure(m):
    if not m or not m.guild: return False
    if m.author.bot: return False
    if m.id in msg_lock: return False
    msg_lock.add(m.id)
    if len(msg_lock) > 2000:
        msg_lock.clear()
    return True

# ================= ROLE LOGIC =================
def top_role_filtered(member):
    ignored = ignore_roles.get(str(member.guild.id))
    roles = sorted(member.roles, key=lambda r: r.position, reverse=True)

    for r in roles:
        if str(r.id) != ignored:
            return r
    return roles[0] if roles else None

def can_act(actor, target):
    if actor.id == CREATOR_ID:
        return True
    ar = top_role_filtered(actor)
    tr = top_role_filtered(target)
    if not ar or not tr:
        return False
    return ar.position > tr.position

def bot_can(target, guild):
    return guild.me.top_role > target.top_role

# ================= AI =================
def ask_ai(uid, text):
    if not GROQ_KEY:
        return "AI off"

    history = memory.get(str(uid), [])[-3:]

    messages = [{
        "role": "system",
        "content": "You are Yen. Sarcastic, blunt, TikTok tone. Short replies. No hate."
    }]

    if history:
        messages.append({"role": "user","content": " | ".join(history)})

    messages.append({"role": "user", "content": text})

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": messages,
                "max_tokens": 50
            },
            timeout=10
        )

        if r.status_code != 200:
            return f"AI {r.status_code}"

        return r.json()["choices"][0]["message"]["content"]

    except:
        return "AI died 💀"

# ================= MESSAGE =================
@bot.event
async def on_message(m):
    if not secure(m): return
    await bot.process_commands(m)

    if not IS_LEADER: return

    msg = norm(m.content.lower())

    if msg.startswith("hey yen"):
        uid = str(m.author.id)

        memory.setdefault(uid, []).append(m.content)
        memory[uid] = memory[uid][-6:]
        save(FILES["memory"], memory)

        if uid in cooldowns and time.time() - cooldowns[uid] < 2:
            return
        cooldowns[uid] = time.time()

        reply = ask_ai(uid, m.content)
        log(m.guild, f"AI {m.author}")
        return await m.reply(reply, allowed_mentions=SAFE)

# ================= READY =================
@bot.event
async def on_ready():
    global IS_LEADER
    ch = bot.get_channel(LOCK_CHANNEL_ID)

    if ch:
        await ch.send("BOOTING...")
        await asyncio.sleep(1)
        IS_LEADER = True
        await ch.send("YEN ONLINE")

# ================= USER SELECT =================
class UserSelect(discord.ui.UserSelect):
    def __init__(self, view):
        super().__init__(placeholder="Select user", min_values=1, max_values=1)
        self.view = view

    async def callback(self, interaction: discord.Interaction):
        self.view.target = self.values[0]
        await interaction.response.edit_message(embed=self.view.embed(interaction.guild), view=self.view)

# ================= DASHBOARD =================
class Dashboard(discord.ui.View):
    def __init__(self, target):
        super().__init__(timeout=None)
        self.target = target
        self.page = "home"

        self.build_home()

    def build_home(self):
        self.clear_items()
        self.add_item(UserSelect(self))
        self.add_item(self.home)
        self.add_item(self.logs_btn)
        self.add_item(self.punish)

    def build_punish(self):
        self.clear_items()
        self.add_item(UserSelect(self))
        self.add_item(self.home)
        self.add_item(self.logs_btn)
        self.add_item(self.punish)

        # ONLY here actions appear
        self.add_item(self.ban)
        self.add_item(self.kick)
        self.add_item(self.mute)
        self.add_item(self.unmute)

    def embed(self, g):
        e = discord.Embed(title="YEN PANEL", color=discord.Color.purple())

        if self.page == "home":
            e.add_field(name="Target", value=str(self.target))

        elif self.page == "logs":
            data = logs.get(str(g.id), [])[-6:]
            e.description = "\n".join(data) if data else "No logs"

        elif self.page == "punish":
            e.description = f"Target: {self.target}"

        return e

    @discord.ui.button(label="HOME")
    async def home(self, i, b):
        self.page = "home"
        self.build_home()
        await i.response.edit_message(embed=self.embed(i.guild), view=self)

    @discord.ui.button(label="LOGS")
    async def logs_btn(self, i, b):
        self.page = "logs"
        self.build_home()
        await i.response.edit_message(embed=self.embed(i.guild), view=self)

    @discord.ui.button(label="PUNISHMENT")
    async def punish(self, i, b):
        self.page = "punish"
        self.build_punish()
        await i.response.edit_message(embed=self.embed(i.guild), view=self)

    # ===== ACTIONS =====
    @discord.ui.button(label="BAN")
    async def ban(self, i, b):
        if not self.target:
            return await i.response.send_message("no target", ephemeral=True)

        if not can_act(i.user, self.target) or not bot_can(self.target, i.guild):
            return await i.response.send_message("no perms", ephemeral=True)

        try:
            await self.target.ban()
            log(i.guild, f"BAN {self.target}")
            await i.response.send_message("banned", ephemeral=True)
        except:
            await i.response.send_message("fail", ephemeral=True)

    @discord.ui.button(label="KICK")
    async def kick(self, i, b):
        if not self.target:
            return await i.response.send_message("no target", ephemeral=True)

        if not can_act(i.user, self.target) or not bot_can(self.target, i.guild):
            return await i.response.send_message("no perms", ephemeral=True)

        try:
            await self.target.kick()
            log(i.guild, f"KICK {self.target}")
            await i.response.send_message("kicked", ephemeral=True)
        except:
            await i.response.send_message("fail", ephemeral=True)

    @discord.ui.button(label="MUTE")
    async def mute(self, i, b):
        role = discord.utils.get(i.guild.roles, name="Muted")
        if not role:
            return await i.response.send_message("no muted role", ephemeral=True)

        try:
            await self.target.add_roles(role)
            log(i.guild, f"MUTE {self.target}")
            await i.response.send_message("muted", ephemeral=True)
        except:
            await i.response.send_message("fail", ephemeral=True)

    @discord.ui.button(label="UNMUTE")
    async def unmute(self, i, b):
        role = discord.utils.get(i.guild.roles, name="Muted")
        if not role:
            return await i.response.send_message("no muted role", ephemeral=True)

        try:
            await self.target.remove_roles(role)
            log(i.guild, f"UNMUTE {self.target}")
            await i.response.send_message("unmuted", ephemeral=True)
        except:
            await i.response.send_message("fail", ephemeral=True)

# ================= COMMANDS =================
@bot.command()
async def dashboard(ctx, user: discord.Member = None):
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send("no perms")

    user = user or ctx.author
    await ctx.send("panel", view=Dashboard(user))

@bot.command()
async def ignorerole(ctx, role: discord.Role):
    if ctx.author.id != CREATOR_ID:
        return await ctx.send("no")

    ignore_roles[str(ctx.guild.id)] = str(role.id)
    save(FILES["ignore"], ignore_roles)
    await ctx.send(f"ignored {role.name}")

# ================= RUN =================
bot.run(TOKEN)