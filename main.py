import discord
from discord.ext import commands
import os, json, time, random, asyncio, unicodedata, math
from groq import Groq

# ---------- ENV ----------
TOKEN = os.getenv("TOKEN")
GROQ_KEY = os.getenv("GROQ_KEY")

if not TOKEN or not GROQ_KEY:
    raise ValueError("Missing TOKEN or GROQ_KEY")

client = Groq(api_key=GROQ_KEY)

# ---------- BOT ----------
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="", intents=intents)

SAFE_MENTIONS = discord.AllowedMentions(everyone=False, roles=False, users=True)

CREATOR_ID = 1383111113016872980
IMMUNE_USERS = {CREATOR_ID, 1464487262082302095}

LOCK_CHANNEL_ID = 1446191246828634223
IS_LEADER = False

# ---------- CONFIG ----------
MEMORY_LIMIT = 8
COOLDOWN_TIME = 4

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

    async for m in channel.history(limit=10):
        if m.author != bot.user:
            continue

        if content and m.content == content:
            return

        if embed and m.embeds:
            try:
                if m.embeds[0].title == embed.title:
                    return
            except:
                pass

    if ref:
        return await ref.reply(content, embed=embed, allowed_mentions=SAFE_MENTIONS)

    return await channel.send(content, embed=embed, allowed_mentions=SAFE_MENTIONS)

# ---------- HELPERS ----------
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

# ---------- HELP UI ----------
class HelpView(discord.ui.View):
    def __init__(self, user, cmds):
        super().__init__(timeout=60)
        self.user = user
        self.cmds = cmds
        self.page = 0
        self.per_page = 5
        self.total_pages = math.ceil(len(cmds) / self.per_page)

    def get_embed(self):
        start = self.page * self.per_page
        end = start + self.per_page
        chunk = self.cmds[start:end]

        embed = discord.Embed(
            title=fancy(f"Yen Commands ({self.page+1}/{self.total_pages})"),
            description="\n".join(fancy(c) for c in chunk),
            color=discord.Color.purple()
        )
        return embed

    async def interaction_check(self, interaction):
        return interaction.user == self.user

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction, button):
        self.page = (self.page - 1) % self.total_pages
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def next(self, interaction, button):
        self.page = (self.page + 1) % self.total_pages
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

# ---------- READY ----------
@bot.event
async def on_ready():
    global IS_LEADER

    channel = bot.get_channel(LOCK_CHANNEL_ID)
    if not channel:
        return

    async for msg in channel.history(limit=5):
        if msg.author == bot.user and msg.content in ["LOCK", "LOCK IN"]:
            IS_LEADER = False
            return

    await channel.send("LOCK IN")
    IS_LEADER = True

# ---------- MESSAGE ----------
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

# ---------- COMMAND BLOCK ----------
    if msg.startswith("yen"):

        def creator_only():
            return message.author.id == CREATOR_ID

        # ---------- HELP ----------
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
                "yen reset all",
                "yen slime @user",
                "yen restore @user"
            ]

            # delete old help embeds
            async for m in message.channel.history(limit=10):
                if m.author == bot.user and m.embeds:
                    try:
                        if "yen commands" in m.embeds[0].title.lower():
                            await m.delete()
                    except:
                        pass

            view = HelpView(message.author, cmds)

            # slight delay = "animated feel"
            msg_obj = await message.channel.send("loading commands...")
            await asyncio.sleep(0.4)
            await msg_obj.edit(content=None, embed=view.get_embed(), view=view)

            return

        return  # stops AI from triggering on commands

# ---------- AI ----------
    if not (msg.startswith("hey yen") or random.randint(1,50) == 1):
        return

    uid = str(message.author.id)

    if uid in user_cooldowns and now - user_cooldowns[uid] < COOLDOWN_TIME:
        return

    user_cooldowns[uid] = now

    await message.reply("idk bro ask again later 💀", allowed_mentions=SAFE_MENTIONS)

# ---------- RUN ----------
bot.run(TOKEN)