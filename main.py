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
LOCK_CHANNEL_ID = 1446191246828634223
IS_LEADER = False

# ---------- FILES ----------
FILES = {
    "slime": "slimed.json",
    "ignore": "ignore_roles.json",
    "auto": "auto_roles.json",
    "filter": "filter.json"
}

def load_json(f):
    if os.path.exists(f):
        with open(f) as file:
            return json.load(file)
    return {}

def save_json(d, f):
    with open(f, "w") as file:
        json.dump(d, file, indent=2)

slimed_users = load_json(FILES["slime"])
ignored_roles = load_json(FILES["ignore"])
auto_roles = load_json(FILES["auto"])
filtered_words = load_json(FILES["filter"])

DEFAULT_FILTER = ["badword1", "badword2"]

# ---------- STATE ----------
conversation_memory = {}
user_cooldowns = {}
message_locks = {}

# ---------- UTIL ----------
def normalize_text(t):
    return unicodedata.normalize("NFKD", t).encode("ascii","ignore").decode("ascii")

async def safe_send(ch, content=None, embed=None, ref=None):
    if ref:
        return await ref.reply(content, embed=embed, allowed_mentions=SAFE_MENTIONS)
    return await ch.send(content, embed=embed, allowed_mentions=SAFE_MENTIONS)

def fancy(t):
    normal = "abcdefghijklmnopqrstuvwxyz0123456789"
    fancy_ = "𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝚖𝚗𝚘𝚙𝚚𝚛𝚜𝚝𝚞𝚟𝚠𝚡𝚢𝚣0123456789"
    return t.lower().translate(str.maketrans(normal, fancy_))

# ---------- ROLE LOGIC ----------
def get_effective_top_role(member, guild):
    ignored = ignored_roles.get(str(guild.id), [])
    roles = [r for r in member.roles if r.id not in ignored]
    return max(roles, key=lambda r: r.position, default=guild.default_role)

def can_act(a, t, g):
    return a == g.owner or get_effective_top_role(a,g) > get_effective_top_role(t,g)

def bot_can_act(t, g):
    return g.me.top_role > get_effective_top_role(t,g)

# ---------- AI ----------
def simple_ai(text):
    text = text.lower()
    if any(x in text for x in ["what","how","why","help"]):
        return "google exists bro"
    return random.choice([
        "nah 💀","skill issue","cry about it",
        "mid take","you good?","ain't no way"
    ])

# ---------- HELP UI ----------
class HelpView(discord.ui.View):
    def __init__(self, user, cmds):
        super().__init__(timeout=60)
        self.user = user
        self.cmds = cmds
        self.page = 0
        self.per = 6
        self.pages = math.ceil(len(cmds)/self.per)

    def get_embed(self):
        chunk = self.cmds[self.page*self.per:(self.page+1)*self.per]
        return discord.Embed(
            title=fancy(f"Yen Commands ({self.page+1}/{self.pages})"),
            description="\n".join(fancy(c) for c in chunk),
            color=discord.Color.purple()
        )

    async def interaction_check(self, i):
        return i.user == self.user

    @discord.ui.button(label="⬅️")
    async def prev(self, i, b):
        self.page = (self.page-1)%self.pages
        await i.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="➡️")
    async def next(self, i, b):
        self.page = (self.page+1)%self.pages
        await i.response.edit_message(embed=self.get_embed(), view=self)

# ---------- READY ----------
@bot.event
async def on_ready():
    global IS_LEADER
    ch = bot.get_channel(LOCK_CHANNEL_ID)
    if not ch: return

    async for m in ch.history(limit=5):
        if m.author == bot.user:
            IS_LEADER = False
            return

    await ch.send("LOCK IN, SYSTEM UPDATED, NEW VERSION EXECUTING")
    IS_LEADER = True

# ---------- AUTO ROLE ----------
@bot.event
async def on_member_update(before, after):
    if before.roles == after.roles:
        return

    gid = str(after.guild.id)
    mapping = auto_roles.get(gid, {})

    gained = {r.id for r in after.roles} - {r.id for r in before.roles}

    for rid in gained:
        if str(rid) in mapping:
            role = after.guild.get_role(mapping[str(rid)])
            if role and role < after.guild.me.top_role:
                try:
                    await after.add_roles(role)
                except:
                    pass

# ---------- MAIN ----------
@bot.event
async def on_message(message):

    if message.author.bot or not IS_LEADER:
        return

    now = time.time()

    if message.id in message_locks and now - message_locks[message.id] < 5:
        return
    message_locks[message.id] = now

    raw = message.content
    msg = normalize_text(raw.lower())

    # ---------- FILTER ----------
    words = filtered_words.get(str(message.guild.id), DEFAULT_FILTER)
    for w in words:
        if w in msg:
            try: await message.delete()
            except: pass
            return await safe_send(message.channel, f"{message.author.mention} watch your language")

    # ---------- COMMANDS ----------
    if msg.startswith("yen"):

        def creator():
            return message.author.id == CREATOR_ID

        # AUTO ROLE
        if msg.startswith("yen add"):
            if not creator():
                return await safe_send(message.channel,"only the creator yen can use this")

            if len(message.role_mentions) < 2:
                return

            give = message.role_mentions[0]
            trigger = message.role_mentions[1]

            gid = str(message.guild.id)
            auto_roles.setdefault(gid, {})
            auto_roles[gid][str(trigger.id)] = give.id
            save_json(auto_roles, FILES["auto"])

            members = [m for m in message.guild.members if trigger in m.roles]
            total = len(members)

            for i,m in enumerate(members,1):
                if give not in m.roles and give < message.guild.me.top_role:
                    try: await m.add_roles(give)
                    except: pass
                if total > 5 and i % 5 == 0:
                    await safe_send(message.channel, f"{int((i/total)*100)}%")

            return await safe_send(message.channel,f"{give.name} auto added to {trigger.name}")

        # STRIP
        if msg == "yen strip roles":
            if not creator():
                return await safe_send(message.channel,"only the creator yen can use this")

            members = [m for m in message.guild.members if not m.bot]
            total = len(members)

            for i,m in enumerate(members,1):
                removable = [r for r in m.roles if r != message.guild.default_role and r < message.guild.me.top_role]
                if removable:
                    try: await m.remove_roles(*removable)
                    except: pass
                if i % 5 == 0:
                    await safe_send(message.channel,f"{int((i/total)*100)}%")

            return await safe_send(message.channel,"done stripping roles 💀")

        # VERIFIED
        if msg == "yen give verified":
            if not creator():
                return await safe_send(message.channel,"only the creator yen can use this")

            role = discord.utils.get(message.guild.roles, name="Verified")
            if not role:
                role = await message.guild.create_role(name="Verified")

            for m in message.guild.members:
                if not m.bot and role not in m.roles:
                    try: await m.add_roles(role)
                    except: pass

            return await safe_send(message.channel,"everyone verified ✅")

        # BAN
        if msg.startswith("yen ban") and message.mentions:
            t = message.mentions[0]

            if not can_act(message.author,t,message.guild):
                return await safe_send(message.channel,"you aren't high enough in the role hierarchy")
            if not bot_can_act(t,message.guild):
                return await safe_send(message.channel,"i can't do that")

            await t.ban()
            return await safe_send(message.channel,f"{t} banned")

        # KICK
        if msg.startswith("yen kick") and message.mentions:
            t = message.mentions[0]

            if not can_act(message.author,t,message.guild):
                return await safe_send(message.channel,"you aren't high enough in the role hierarchy")
            if not bot_can_act(t,message.guild):
                return await safe_send(message.channel,"i can't do that")

            await t.kick()
            return await safe_send(message.channel,f"{t} kicked")

        # MUTE
        if msg.startswith("yen mute") and message.mentions:
            t = message.mentions[0]

            role = discord.utils.get(message.guild.roles,name="Muted")
            if not role:
                role = await message.guild.create_role(name="Muted")

            await t.add_roles(role)
            return await safe_send(message.channel,f"{t} muted")

        # UNMUTE
        if msg.startswith("yen unmute") and message.mentions:
            t = message.mentions[0]
            role = discord.utils.get(message.guild.roles,name="Muted")
            if role:
                await t.remove_roles(role)
            return await safe_send(message.channel,f"{t} unmuted")

        # HELP
        if msg == "yen commands":
            cmds = [
                "yen add @role to @role",
                "yen strip roles",
                "yen give verified",
                "yen ban @user",
                "yen kick @user",
                "yen mute @user",
                "yen unmute @user"
            ]
            view = HelpView(message.author, cmds)
            return await message.channel.send(embed=view.get_embed(), view=view)

        return

    # ---------- AI ----------
    if not msg.startswith("hey yen"):
        return

    uid = str(message.author.id)

    if uid in user_cooldowns and now - user_cooldowns[uid] < 3:
        return

    user_cooldowns[uid] = now

    await asyncio.sleep(random.uniform(0.3,0.7))
    await message.reply(simple_ai(raw), allowed_mentions=SAFE_MENTIONS)

# ---------- RUN ----------
bot.run(TOKEN)