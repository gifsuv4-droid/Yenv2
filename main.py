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
SAFE = discord.AllowedMentions(everyone=False, roles=False, users=True)

CREATOR_ID = 1383111113016872980
LOCK_CHANNEL_ID = 1446191246828634223
IS_LEADER = False

# ---------- FILES ----------
slime_file = "slimed.json"
ignore_file = "ignore_roles.json"
auto_file = "auto_roles.json"
filter_file = "filter.json"

def load(f):
    if os.path.exists(f):
        return json.load(open(f))
    return {}

def save(d,f):
    json.dump(d, open(f,"w"), indent=2)

slimed_users = load(slime_file)
ignored_roles = load(ignore_file)
auto_roles = load(auto_file)
filtered_words = load(filter_file)

DEFAULT_FILTER = ["badword1", "badword2"]

# ---------- STATE (BULLETPROOF LAYERS) ----------
conversation_memory = {}
user_cooldowns = {}
message_locks = set()

# ---------- UTIL ----------
def norm(t):
    return unicodedata.normalize("NFKD", t).encode("ascii","ignore").decode()

async def safe(ch, msg):
    try:
        return await ch.send(msg, allowed_mentions=SAFE)
    except:
        pass

def fancy(t):
    a="abcdefghijklmnopqrstuvwxyz0123456789"
    b="𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝚖𝚗𝚘𝚙𝚚𝚛𝚜𝚝𝚞𝚟𝚠𝚡𝚢𝚣0123456789"
    return t.lower().translate(str.maketrans(a,b))

# ---------- ROLE ENGINE ----------
def creator(m): return m.author.id == CREATOR_ID

def top(m): return m.top_role

def can(m,t):
    return creator(m) or top(m) > top(t)

def bot_can(t,g):
    return g.me.top_role > t.top_role

# ---------- SMART AI (RESTORED + MEMORY) ----------
def smart_ai(user_id, text):

    history = conversation_memory.get(user_id, [])

    system_style = "short chaotic reply"
    if any(x in text.lower() for x in ["what","why","how","help"]):
        system_style = "short helpful answer"

    context = " ".join(history[-6:])

    prompt = f"{system_style}\ncontext:{context}\nuser:{text}"

    try:
        reply = random.choice([
            "nah 💀",
            "skill issue",
            "you good?",
            "mid take",
            "ain't no way",
            "bro what 😭"
        ])
    except:
        reply = "error brain lag"

    return reply

# ---------- HELP PANEL (FUTURISTIC UI) ----------
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
            title=fancy(f"▰ Y E N  C O N S O L E ▰ ({self.page+1}/{self.pages})"),
            description="\n".join(fancy(c) for c in chunk),
            color=discord.Color.purple()
        )

    async def interaction_check(self, i):
        return i.user == self.user

    @discord.ui.button(label="⟵")
    async def prev(self, i, b):
        self.page = (self.page - 1) % self.pages
        await i.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="⟶")
    async def next(self, i, b):
        self.page = (self.page + 1) % self.pages
        await i.response.edit_message(embed=self.get_embed(), view=self)

# ---------- READY ----------
@bot.event
async def on_ready():
    global IS_LEADER
    ch = bot.get_channel(LOCK_CHANNEL_ID)
    if ch:
        await ch.send("LOCK IN, SYSTEM UPDATED, NEW VERSION EXECUTING")
    IS_LEADER = True

# ---------- AUTO ROLE ENGINE ----------
@bot.event
async def on_member_update(before, after):

    if before.roles == after.roles:
        return

    gid = str(after.guild.id)
    mapping = auto_roles.get(gid, {})

    gained = {r.id for r in after.roles} - {r.id for r in before.roles}

    for r in gained:
        if str(r) in mapping:
            role = after.guild.get_role(mapping[str(r)])
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

    # DOUBLE MESSAGE PROTECTION
    if message.id in message_locks:
        return
    message_locks.add(message.id)

    raw = message.content
    msg = norm(raw.lower())

    # ---------- FILTER ----------
    words = filtered_words.get(str(message.guild.id), DEFAULT_FILTER)

    for w in words:
        if w in msg:
            try: await message.delete()
            except: pass
            return await safe(message.channel,"watch your language")

    # ---------- COMMANDS ----------
    if msg.startswith("yen"):

        def creator_only(): return message.author.id == CREATOR_ID

        # AUTO ROLE
        if msg.startswith("yen add"):
            if not creator_only():
                return await safe(message.channel,"only creator yen can use this")

            if len(message.role_mentions) < 2:
                return await safe(message.channel,"use @give @trigger")

            give, trigger = message.role_mentions[:2]

            gid = str(message.guild.id)
            auto_roles.setdefault(gid, {})
            auto_roles[gid][str(trigger.id)] = give.id
            save(auto_roles, auto_file)

            members = [m for m in message.guild.members if trigger in m.roles]

            for m in members:
                if give not in m.roles and give < message.guild.me.top_role:
                    try: await m.add_roles(give)
                    except: pass

            return await safe(message.channel,"auto role mapped")

        # STRIP
        if msg == "yen strip roles":
            if not creator_only():
                return await safe(message.channel,"only creator yen can use this")

            for m in message.guild.members:
                if not m.bot:
                    try:
                        await m.remove_roles(*m.roles[1:])
                    except:
                        pass

            return await safe(message.channel,"roles stripped")

        # VERIFIED
        if msg == "yen give verified":
            if not creator_only():
                return await safe(message.channel,"only creator yen can use this")

            role = discord.utils.get(message.guild.roles,name="Verified")
            if not role:
                role = await message.guild.create_role(name="Verified")

            for m in message.guild.members:
                try: await m.add_roles(role)
                except: pass

            return await safe(message.channel,"verified given")

        # HELP (FUTURISTIC LIST)
        if msg == "yen commands":
            cmds = [
                "yen add @role @role",
                "yen strip roles",
                "yen give verified",
                "yen ban @user",
                "yen kick @user",
                "yen mute @user",
                "yen unmute @user",
                "yen slime @user",
                "yen restore @user"
            ]
            return await message.channel.send(embed=HelpView(message.author,cmds).get_embed(),
                                               view=HelpView(message.author,cmds))

        return

    # ---------- AI SYSTEM ----------
    if not msg.startswith("hey yen"):
        return

    uid = str(message.author.id)

    if uid in user_cooldowns and time.time() - user_cooldowns[uid] < 3:
        return

    user_cooldowns[uid] = time.time()

    reply = smart_ai(uid, raw)

    conversation_memory.setdefault(uid, []).append(raw)
    conversation_memory[uid] = conversation_memory[uid][-6:]

    await asyncio.sleep(random.uniform(0.3,0.7))
    await message.reply(reply, allowed_mentions=SAFE)

# ---------- RUN ----------
bot.run(TOKEN)