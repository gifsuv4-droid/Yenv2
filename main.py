import discord
from discord.ext import commands
import os, json, time, random, asyncio, unicodedata, math

# ---------- ENV ----------
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("Missing TOKEN")

# ---------- BOT ----------
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="", intents=intents)

SAFE_MENTIONS = discord.AllowedMentions(everyone=False, roles=False, users=True)

CREATOR_ID = 1383111113016872980
IMMUNE_USERS = {CREATOR_ID, 1464487262082302095}

LOCK_CHANNEL_ID = 1446191246828634223
IS_LEADER = False

# ---------- CONFIG ----------
MEMORY_LIMIT = 6
COOLDOWN_TIME = 3

slime_file = "slimed.json"
ignore_file = "ignore_roles.json"

conversation_memory = {}
user_cooldowns = {}
message_locks = {}

# ---------- NORMALIZE ----------
def normalize_text(text):
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")

# ---------- FILE ----------
def load_json(f):
    if os.path.exists(f):
        with open(f) as file:
            return json.load(file)
    return {}

def save_json(d, f):
    with open(f, "w") as file:
        json.dump(d, file, indent=2)

slimed_users = load_json(slime_file)
ignored_roles = load_json(ignore_file)

# ---------- SAFE SEND ----------
async def safe_send(channel, content=None, embed=None, ref=None):
    if ref:
        return await ref.reply(content, embed=embed, allowed_mentions=SAFE_MENTIONS)
    return await channel.send(content, embed=embed, allowed_mentions=SAFE_MENTIONS)

# ---------- FANCY ----------
def fancy(text):
    normal = "abcdefghijklmnopqrstuvwxyz0123456789"
    fancy_ = "𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝚖𝚗𝚘𝚙𝚚𝚛𝚜𝚝𝚞𝚟𝚠𝚡𝚢𝚣0123456789"
    return text.lower().translate(str.maketrans(normal, fancy_))

# ---------- ROLE LOGIC ----------
def get_effective_top_role(member, guild):
    ignored = ignored_roles.get(str(guild.id), [])
    roles = [r for r in member.roles if r.id not in ignored]
    return max(roles, key=lambda r: r.position, default=guild.default_role)

def can_act(author, target, guild):
    if author == guild.owner:
        return True
    return get_effective_top_role(author, guild) > get_effective_top_role(target, guild)

def bot_can_act(target, guild):
    return guild.me.top_role > get_effective_top_role(target, guild)

# ---------- SIMPLE AI ----------
def simple_ai(text):
    text = text.lower()

    if any(q in text for q in ["what","how","why","help"]):
        return "google exists bro"

    replies = [
        "nah 💀",
        "you thought that was smart?",
        "bro said that with confidence 😭",
        "ain't no way",
        "skill issue",
        "cry about it",
        "mid take",
        "you good?"
    ]
    return random.choice(replies)

# ---------- HELP UI ----------
class HelpView(discord.ui.View):
    def __init__(self, user, cmds):
        super().__init__(timeout=60)
        self.user = user
        self.cmds = cmds
        self.page = 0
        self.per = 5
        self.pages = math.ceil(len(cmds)/self.per)

    def get_embed(self):
        chunk = self.cmds[self.page*self.per:(self.page+1)*self.per]
        return discord.Embed(
            title=fancy(f"Yen Commands ({self.page+1}/{self.pages})"),
            description="\n".join(fancy(c) for c in chunk),
            color=discord.Color.purple()
        )

    async def interaction_check(self, interaction):
        return interaction.user == self.user

    @discord.ui.button(label="⬅️")
    async def prev(self, i, b):
        self.page = (self.page - 1) % self.pages
        await i.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="➡️")
    async def next(self, i, b):
        self.page = (self.page + 1) % self.pages
        await i.response.edit_message(embed=self.get_embed(), view=self)

# ---------- READY ----------
@bot.event
async def on_ready():
    global IS_LEADER

    ch = bot.get_channel(LOCK_CHANNEL_ID)
    if not ch:
        return

    async for m in ch.history(limit=5):
        if m.author == bot.user and m.content in ["LOCK","LOCK IN"]:
            IS_LEADER = False
            return

    await ch.send("LOCK IN")
    IS_LEADER = True

# ---------- MESSAGE ----------
@bot.event
async def on_message(message):

    if message.author.bot or not IS_LEADER:
        return

    raw = message.content
    msg = normalize_text(raw.lower())

    # ---------- COMMAND BLOCK ----------
    if msg.startswith("yen"):

        def creator_only():
            return message.author.id == CREATOR_ID

        # IGNORE
        if msg.startswith("yen ignore"):
            if not creator_only():
                return await safe_send(message.channel,"only the creator yen can use this")
            if not message.role_mentions:
                return
            r = message.role_mentions[0]
            gid = str(message.guild.id)
            ignored_roles.setdefault(gid,[])
            if r.id not in ignored_roles[gid]:
                ignored_roles[gid].append(r.id)
                save_json(ignored_roles,ignore_file)
                await safe_send(message.channel,f"ignoring {r.name}")
            return

        # UNIGNORE
        if msg.startswith("yen unignore"):
            if not creator_only():
                return await safe_send(message.channel,"only the creator yen can use this")
            if not message.role_mentions:
                return
            r = message.role_mentions[0]
            gid = str(message.guild.id)
            if r.id in ignored_roles.get(gid,[]):
                ignored_roles[gid].remove(r.id)
                save_json(ignored_roles,ignore_file)
                await safe_send(message.channel,f"stopped ignoring {r.name}")
            return

        # BAN
        if msg.startswith("yen ban"):
            if not message.mentions: return
            t = message.mentions[0]

            if not can_act(message.author,t,message.guild):
                return await safe_send(message.channel,"you aren't high enough in the role hierarchy")
            if not bot_can_act(t,message.guild):
                return await safe_send(message.channel,"i can't do that")

            await t.ban()
            return await safe_send(message.channel,f"{t} banned")

        # KICK
        if msg.startswith("yen kick"):
            if not message.mentions: return
            t = message.mentions[0]

            if not can_act(message.author,t,message.guild):
                return await safe_send(message.channel,"you aren't high enough in the role hierarchy")
            if not bot_can_act(t,message.guild):
                return await safe_send(message.channel,"i can't do that")

            await t.kick()
            return await safe_send(message.channel,f"{t} kicked")

        # MUTE
        if msg.startswith("yen mute"):
            if not message.mentions: return
            t = message.mentions[0]

            role = discord.utils.get(message.guild.roles,name="Muted")
            if not role:
                role = await message.guild.create_role(name="Muted")

            await t.add_roles(role)
            return await safe_send(message.channel,f"{t} muted")

        # UNMUTE
        if msg.startswith("yen unmute"):
            if not message.mentions: return
            t = message.mentions[0]
            role = discord.utils.get(message.guild.roles,name="Muted")
            if role:
                await t.remove_roles(role)
            return await safe_send(message.channel,f"{t} unmuted")

        # STRIP ROLES
        if msg == "yen strip roles":
            if not creator_only():
                return await safe_send(message.channel,"only the creator yen can use this")

            members = [m for m in message.guild.members if not m.bot]
            total = len(members)

            for i,m in enumerate(members,1):
                removable=[r for r in m.roles if r!=message.guild.default_role and r<message.guild.me.top_role]
                if removable:
                    try: await m.remove_roles(*removable)
                    except: pass
                if i%5==0:
                    await safe_send(message.channel,f"{int((i/total)*100)}%")

            return await safe_send(message.channel,"done stripping roles 💀")

        # VERIFIED
        if msg == "yen give verified":
            if not creator_only():
                return await safe_send(message.channel,"only the creator yen can use this")

            role = discord.utils.get(message.guild.roles,name="Verified")
            if not role:
                role = await message.guild.create_role(name="Verified")

            members=[m for m in message.guild.members if not m.bot]
            total=len(members)

            for i,m in enumerate(members,1):
                if role not in m.roles:
                    try: await m.add_roles(role)
                    except: pass
                if i%5==0:
                    await safe_send(message.channel,f"{int((i/total)*100)}%")

            return await safe_send(message.channel,"everyone verified ✅")

        # RESET
        if msg == "yen reset all":
            if not creator_only():
                return await safe_send(message.channel,"only the creator yen can use this")
            conversation_memory.clear()
            return await safe_send(message.channel,"memory wiped 🧠💀")

        # HELP
        if msg == "yen commands":
            cmds = [
                "yen ban @user",
                "yen kick @user",
                "yen mute @user",
                "yen unmute @user",
                "yen ignore @role",
                "yen unignore @role",
                "yen strip roles",
                "yen give verified",
                "yen reset all"
            ]
            view = HelpView(message.author,cmds)
            return await message.channel.send(embed=view.get_embed(),view=view)

        return  # 🔥 STOPS AI

    # ---------- AI ----------
    if not msg.startswith("hey yen"):
        return

    uid = str(message.author.id)

    if uid in user_cooldowns and time.time()-user_cooldowns[uid]<COOLDOWN_TIME:
        return

    user_cooldowns[uid]=time.time()

    reply = simple_ai(raw)

    await asyncio.sleep(random.uniform(0.3,0.8))
    await message.reply(reply,allowed_mentions=SAFE_MENTIONS)

# ---------- RUN ----------
bot.run(TOKEN)