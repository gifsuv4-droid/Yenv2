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

# ---------- CONFIG ----------
MEMORY_LIMIT = 6
COOLDOWN_TIME = 3

conversation_memory = {}
user_cooldowns = {}

# ---------- FILES ----------
ignore_file = "ignore_roles.json"
role_map_file = "role_map.json"

def load_json(f):
    if os.path.exists(f):
        with open(f, "r") as file:
            return json.load(file)
    return {}

def save_json(data, f):
    with open(f, "w") as file:
        json.dump(data, file, indent=2)

ignored_roles = load_json(ignore_file)
role_map = load_json(role_map_file)

# ---------- NORMALIZE ----------
def normalize_text(text):
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")

# ---------- SAFE SEND ----------
async def safe_send(channel, content=None, embed=None, ref=None):
    if ref:
        return await ref.reply(content, embed=embed, allowed_mentions=SAFE_MENTIONS)
    return await channel.send(content, embed=embed, allowed_mentions=SAFE_MENTIONS)

# ---------- FANCY TEXT ----------
def fancy(text):
    normal = "abcdefghijklmnopqrstuvwxyz0123456789"
    fancy_ = "𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝚖𝚗𝚘𝚙𝚚𝚛𝚜𝚝𝚞𝚟𝚠𝚡𝚢𝚣0123456789"
    return text.lower().translate(str.maketrans(normal, fancy_))

# ---------- ROLE LOGIC ----------
def get_effective_role(member, guild):
    ignored = ignored_roles.get(str(guild.id), [])
    roles = [r for r in member.roles if r.id not in ignored]
    return max(roles, key=lambda r: r.position, default=guild.default_role)

def can_act(author, target, guild):
    if author.id == CREATOR_ID:
        return True
    return get_effective_role(author, guild) > get_effective_role(target, guild)

def bot_can_act(target, guild):
    return guild.me.top_role > get_effective_role(target, guild)

# ---------- SIMPLE AI ----------
def simple_ai(text):
    replies = [
        "nah 💀",
        "bro what",
        "you good?",
        "skill issue",
        "ain't no way",
        "mid take",
        "💀"
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
        self.pages = math.ceil(len(cmds) / self.per)

    def get_embed(self):
        chunk = self.cmds[self.page*self.per:(self.page+1)*self.per]

        return discord.Embed(
            title=fancy(f"YEN COMMANDS ({self.page+1}/{self.pages})"),
            description="\n".join(fancy(c) for c in chunk),
            color=discord.Color.purple()
        )

    async def interaction_check(self, interaction):
        return interaction.user == self.user

    @discord.ui.button(label="⬅️")
    async def prev(self, interaction, button):
        self.page = (self.page - 1) % self.pages
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="➡️")
    async def next(self, interaction, button):
        self.page = (self.page + 1) % self.pages
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

# ---------- READY ----------
@bot.event
async def on_ready():
    global IS_LEADER
    ch = bot.get_channel(LOCK_CHANNEL_ID)

    if not ch:
        return

    await ch.send("LOCK IN, SYSTEM UPDATED, NEW VERSION EXECUTING")
    IS_LEADER = True

# ---------- ROLE AUTO SYSTEM (FIXED) ----------
@bot.event
async def on_member_update(before, after):

    # role mapping system
    for role_a_id, role_b_id in role_map.get(str(after.guild.id), {}).items():
        role_a = after.guild.get_role(int(role_a_id))
        role_b = after.guild.get_role(int(role_b_id))

        if role_a and role_b:
            if role_a in after.roles and role_b not in after.roles:
                try:
                    await after.add_roles(role_b)
                except:
                    pass

# ---------- MESSAGE ----------
@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if not IS_LEADER:
        return

    raw = message.content
    msg = normalize_text(raw.lower())

    # ---------- COMMAND BLOCK ----------
    if msg.startswith("yen"):

        # IGNORE ROLE
        if msg.startswith("yen ignore"):
            if message.author.id != CREATOR_ID:
                return await safe_send(message.channel, "only creator yen can use this")

            if message.role_mentions:
                r = message.role_mentions[0]
                gid = str(message.guild.id)

                ignored_roles.setdefault(gid, [])
                if r.id not in ignored_roles[gid]:
                    ignored_roles[gid].append(r.id)
                    save_json(ignored_roles, ignore_file)

            return

        # UNIGNORE
        if msg.startswith("yen unignore"):
            if message.author.id != CREATOR_ID:
                return await safe_send(message.channel, "only creator yen can use this")

            if message.role_mentions:
                r = message.role_mentions[0]
                gid = str(message.guild.id)

                if r.id in ignored_roles.get(gid, []):
                    ignored_roles[gid].remove(r.id)
                    save_json(ignored_roles, ignore_file)

            return

        # BAN
        if msg.startswith("yen ban"):
            if not message.mentions:
                return

            t = message.mentions[0]

            if not can_act(message.author, t, message.guild):
                return await safe_send(message.channel, "you aren't high enough in the role hierarchy")

            if not bot_can_act(t, message.guild):
                return await safe_send(message.channel, "bot role too low")

            await t.ban()
            return await safe_send(message.channel, f"{t} banned")

        # KICK
        if msg.startswith("yen kick"):
            if not message.mentions:
                return

            t = message.mentions[0]

            if not can_act(message.author, t, message.guild):
                return await safe_send(message.channel, "you aren't high enough in the role hierarchy")

            await t.kick()
            return await safe_send(message.channel, f"{t} kicked")

        # MUTE
        if msg.startswith("yen mute"):
            if not message.mentions:
                return

            t = message.mentions[0]

            role = discord.utils.get(message.guild.roles, name="Muted")
            if not role:
                role = await message.guild.create_role(name="Muted")

            await t.add_roles(role)
            return await safe_send(message.channel, f"{t} muted")

        # UNMUTE
        if msg.startswith("yen unmute"):
            if not message.mentions:
                return

            t = message.mentions[0]
            role = discord.utils.get(message.guild.roles, name="Muted")

            if role:
                await t.remove_roles(role)

            return await safe_send(message.channel, f"{t} unmuted")

        # STRIP ROLES
        if msg == "yen strip roles":
            if message.author.id != CREATOR_ID:
                return

            for m in message.guild.members:
                if m.bot:
                    continue

                try:
                    roles = [r for r in m.roles if r != message.guild.default_role]
                    await m.remove_roles(*roles)
                except:
                    pass

            return await safe_send(message.channel, "roles stripped")

        # ROLE MAP SYSTEM
        if msg.startswith("yen add"):
            if message.author.id != CREATOR_ID:
                return

            if len(message.role_mentions) >= 2:
                a, b = message.role_mentions[0], message.role_mentions[1]

                role_map.setdefault(str(message.guild.id), {})
                role_map[str(message.guild.id)][str(a.id)] = str(b.id)
                save_json(role_map, role_map_file)

            return await safe_send(message.channel, "role mapping added")

        # VERIFIED
        if msg == "yen give verified":
            if message.author.id != CREATOR_ID:
                return

            role = discord.utils.get(message.guild.roles, name="Verified")
            if not role:
                role = await message.guild.create_role(name="Verified")

            for m in message.guild.members:
                if role not in m.roles:
                    try:
                        await m.add_roles(role)
                    except:
                        pass

            return await safe_send(message.channel, "verified given")

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
                "yen add @role @role"
            ]

            view = HelpView(message.author, cmds)
            return await message.channel.send(embed=view.get_embed(), view=view)

        return

    # ---------- AI ----------
    if not msg.startswith("hey yen"):
        return

    await message.reply(simple_ai(raw))

# ---------- RUN ----------
bot.run(TOKEN)