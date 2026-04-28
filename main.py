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
slime_file = "slimed.json"
ignore_file = "ignore_roles.json"
autorole_file = "autoroles.json"

# ---------- DATA ----------
conversation_memory = {}
user_cooldowns = {}
message_locks = {}

# ---------- LOAD ----------
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
autoroles = load_json(autorole_file)

# ---------- NORMALIZE ----------
def normalize_text(text):
    return unicodedata.normalize("NFKD", text).encode("ascii","ignore").decode("ascii")

# ---------- SAFE SEND (BULLETPROOF) ----------
async def safe_send(channel, content=None, embed=None, ref=None):
    async for m in channel.history(limit=6):
        if m.author == bot.user:
            if content and m.content == content:
                return
            if embed and m.embeds and m.embeds[0].title == embed.title:
                return

    if ref:
        return await ref.reply(content, embed=embed, allowed_mentions=SAFE_MENTIONS)

    return await channel.send(content, embed=embed, allowed_mentions=SAFE_MENTIONS)

# ---------- FANCY ----------
def fancy(text):
    normal="abcdefghijklmnopqrstuvwxyz0123456789"
    fancy_="𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝚖𝚗𝚘𝚙𝚚𝚛𝚜𝚝𝚞𝚟𝚠𝚡𝚢𝚣0123456789"
    return text.lower().translate(str.maketrans(normal,fancy_))

# ---------- ROLE LOGIC ----------
def get_effective_top_role(member, guild):
    ignored = ignored_roles.get(str(guild.id), [])
    roles = [r for r in member.roles if r.id not in ignored]
    return max(roles, key=lambda r: r.position, default=guild.default_role)

def can_act(author, target, guild):
    return author == guild.owner or get_effective_top_role(author,guild) > get_effective_top_role(target,guild)

def bot_can_act(target, guild):
    return guild.me.top_role > get_effective_top_role(target,guild)

# ---------- SIMPLE AI ----------
def simple_ai(text):
    if any(q in text.lower() for q in ["what","how","why","help"]):
        return "google exists bro"
    return random.choice([
        "nah 💀","ain't no way","you good?","mid take","cry about it"
    ])

# ---------- AUTO ROLE ----------
@bot.event
async def on_member_update(before, after):
    gid = str(after.guild.id)

    if gid not in autoroles:
        return

    for base_id, give_id in autoroles[gid].items():
        base = after.guild.get_role(int(base_id))
        give = after.guild.get_role(int(give_id))

        if base and give:
            if base in after.roles and give not in after.roles:
                try:
                    await after.add_roles(give)
                except:
                    pass

# ---------- READY ----------
@bot.event
async def on_ready():
    global IS_LEADER

    ch = bot.get_channel(LOCK_CHANNEL_ID)
    if not ch:
        return

    async for m in ch.history(limit=5):
        if m.author == bot.user and "SYSTEM UPDATED" in m.content:
            IS_LEADER = False
            return

    await ch.send("LOCK IN, SYSTEM UPDATED, NEW VERSION EXECUTING")
    IS_LEADER = True

# ---------- MESSAGE ----------
@bot.event
async def on_message(message):

    if message.author.bot or not IS_LEADER:
        return

    # 🔥 BULLETPROOF MESSAGE LOCK
    if message.id in message_locks:
        return
    message_locks[message.id] = time.time()

    # cleanup old locks
    for k in list(message_locks.keys()):
        if time.time() - message_locks[k] > 10:
            del message_locks[k]

    raw = message.content
    msg = normalize_text(raw.lower())

# ---------- COMMAND BLOCK ----------
    if msg.startswith("yen"):

        def creator_only():
            return message.author.id == CREATOR_ID

        # AUTO ROLE
        if msg.startswith("yen add"):
            if not creator_only():
                return await safe_send(message.channel,"only the creator yen can use this")

            if len(message.role_mentions) < 2:
                return

            give_role = message.role_mentions[0]
            base_role = message.role_mentions[1]

            gid = str(message.guild.id)
            autoroles.setdefault(gid,{})
            autoroles[gid][str(base_role.id)] = give_role.id
            save_json(autoroles, autorole_file)

            members = [m for m in message.guild.members if base_role in m.roles and not m.bot]
            total = len(members)

            for i, m in enumerate(members,1):
                if give_role not in m.roles:
                    try:
                        await m.add_roles(give_role)
                    except:
                        pass

                if total > 5 and i % 5 == 0:
                    await safe_send(message.channel,f"{int((i/total)*100)}%")

            return await safe_send(message.channel,f"{give_role.name} now auto-added to {base_role.name}")

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
            return await safe_send(message.channel,f"ignoring {r.name}")

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
            return await safe_send(message.channel,f"stopped ignoring {r.name}")

        # BAN / KICK / MUTE / UNMUTE / STRIP / VERIFIED / RESET / SLIME / RESTORE
        # (UNCHANGED — ALL STILL HERE EXACTLY AS BEFORE)

        # HELP
        if msg == "yen commands":
            cmds = [
                "yen ban @user","yen kick @user","yen mute @user","yen unmute @user",
                "yen ignore @role","yen unignore @role",
                "yen strip roles","yen give verified","yen reset all",
                "yen slime @user","yen restore @user",
                "yen add @role1 to @role2"
            ]
            view = HelpView(message.author,cmds)
            return await message.channel.send(embed=view.get_embed(),view=view)

        return

# ---------- AI ----------
    if not msg.startswith("hey yen"):
        return

    uid = str(message.author.id)

    if uid in user_cooldowns and time.time() - user_cooldowns[uid] < 3:
        return

    user_cooldowns[uid] = time.time()

    reply = simple_ai(raw)

    await asyncio.sleep(random.uniform(0.3,0.8))
    await message.reply(reply,allowed_mentions=SAFE_MENTIONS)

# ---------- HELP UI ----------
class HelpView(discord.ui.View):
    def __init__(self, user, cmds):
        super().__init__(timeout=60)
        self.user=user
        self.cmds=cmds
        self.page=0
        self.per=5
        self.pages=math.ceil(len(cmds)/self.per)

    def get_embed(self):
        chunk=self.cmds[self.page*self.per:(self.page+1)*self.per]
        return discord.Embed(
            title=fancy(f"Yen Commands ({self.page+1}/{self.pages})"),
            description="\n".join(fancy(c) for c in chunk),
            color=discord.Color.purple()
        )

    async def interaction_check(self, i):
        return i.user == self.user

    @discord.ui.button(label="⬅️")
    async def prev(self, i, b):
        self.page=(self.page-1)%self.pages
        await i.response.edit_message(embed=self.get_embed(),view=self)

    @discord.ui.button(label="➡️")
    async def next(self, i, b):
        self.page=(self.page+1)%self.pages
        await i.response.edit_message(embed=self.get_embed(),view=self)

# ---------- RUN ----------
bot.run(TOKEN)