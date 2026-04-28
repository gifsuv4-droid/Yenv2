import discord
from discord.ext import commands
import os, json, time, random, asyncio, unicodedata, math

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("Missing TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="", intents=intents)

SAFE_MENTIONS = discord.AllowedMentions(everyone=False, roles=False, users=True)

CREATOR_ID = 1383111113016872980
LOCK_CHANNEL_ID = 1446191246828634223
IS_LEADER = False

# FILES
slime_file = "slimed.json"
ignore_file = "ignore_roles.json"
auto_file = "auto_roles.json"
filter_file = "filter.json"

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
auto_roles = load_json(auto_file)
filtered_words = load_json(filter_file)

DEFAULT_FILTER = ["badword1", "badword2"]

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

# ---------- AUTO ROLE LISTENER ----------
@bot.event
async def on_member_update(before, after):

    if before.roles == after.roles:
        return

    gid = str(after.guild.id)
    mapping = auto_roles.get(gid, {})

    gained = {r.id for r in after.roles} - {r.id for r in before.roles}

    for role_id in gained:
        if str(role_id) in mapping:

            role_to_add = after.guild.get_role(mapping[str(role_id)])

            if not role_to_add:
                continue

            # hierarchy check
            if role_to_add >= after.guild.me.top_role:
                continue

            if role_to_add not in after.roles:
                try:
                    await after.add_roles(role_to_add)
                except:
                    pass

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

# ---------- SIMPLE AI ----------
def simple_ai(text):
    if any(q in text.lower() for q in ["what","why","how","help"]):
        return "google exists bro"
    return random.choice(["nah 💀","skill issue","cry about it","mid take"])

# ---------- MESSAGE ----------
@bot.event
async def on_message(message):

    if message.author.bot or not IS_LEADER:
        return

    raw = message.content
    msg = normalize_text(raw.lower())

    # FILTER
    words = filtered_words.get(str(message.guild.id), DEFAULT_FILTER)
    for w in words:
        if w in msg:
            try: await message.delete()
            except: pass
            return await safe_send(message.channel,"watch your language")

    # ---------- COMMANDS ----------
    if msg.startswith("yen"):

        def creator():
            return message.author.id == CREATOR_ID

        # AUTO ROLE (FIXED)
        if msg.startswith("yen add"):

            if not creator():
                return await safe_send(message.channel,"only the creator yen can use this")

            parts = message.role_mentions

            if len(parts) < 2:
                return await safe_send(message.channel,"use: yen add @role to @role")

            give = parts[0]
            trigger = parts[1]

            gid = str(message.guild.id)
            auto_roles.setdefault(gid, {})
            auto_roles[gid][str(trigger.id)] = give.id
            save_json(auto_roles, auto_file)

            # apply to existing users
            members = [m for m in message.guild.members if trigger in m.roles]

            for m in members:
                if give not in m.roles and give < message.guild.me.top_role:
                    try:
                        await m.add_roles(give)
                    except:
                        pass

            return await safe_send(message.channel,f"{give.name} now auto-added to {trigger.name}")

        # STRIP
        if msg == "yen strip roles":
            if not creator():
                return await safe_send(message.channel,"only the creator yen can use this")

            for m in message.guild.members:
                if m.bot: continue
                removable = [r for r in m.roles if r != message.guild.default_role and r < message.guild.me.top_role]
                if removable:
                    try: await m.remove_roles(*removable)
                    except: pass

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

        # HELP (FULL LIST FIXED)
        if msg == "yen commands":
            cmds = [
                "yen add @role to @role",
                "yen strip roles",
                "yen give verified",
                "yen reset all",
                "yen ban @user",
                "yen kick @user",
                "yen mute @user",
                "yen unmute @user",
                "yen ignore @role",
                "yen unignore @role",
                "yen slime @user",
                "yen restore @user"
            ]
            view = HelpView(message.author, cmds)
            return await message.channel.send(embed=view.get_embed(), view=view)

        return

    # ---------- AI ----------
    if not msg.startswith("hey yen"):
        return

    await asyncio.sleep(random.uniform(0.3,0.7))
    await message.reply(simple_ai(raw), allowed_mentions=SAFE_MENTIONS)

# ---------- RUN ----------
bot.run(TOKEN)