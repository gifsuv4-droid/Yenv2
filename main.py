import discord
from discord.ext import commands
import os, json, time, random, asyncio, math
from datetime import timedelta
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
personality = "chaotic sarcastic discord gremlin"
MEMORY_LIMIT = 8
COOLDOWN_TIME = 4

slime_file = "slimed.json"
warn_file = "warns.json"

conversation_memory = {}
user_cooldowns = {}
message_locks = {}

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
warns = load_json(warn_file)

# ---------- SAFE SEND ----------
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

# ---------- HELPERS ----------
def can_moderate(a, t, g):
    return a == g.owner or a.top_role > t.top_role

def fancy(text):
    normal = "abcdefghijklmnopqrstuvwxyz"
    fancy_ = "𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝚖𝚗𝚘𝚙𝚚𝚛𝚜𝚝𝚞𝚟𝚠𝚡𝚢𝚣"
    return text.translate(str.maketrans(normal, fancy_))

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
        text = "\n".join(fancy(c) for c in chunk)
        return discord.Embed(
            title=fancy(f"Yen Commands ({self.page+1}/{self.pages})"),
            description=text,
            color=discord.Color.purple()
        )

    async def interaction_check(self, interaction):
        return interaction.user == self.user

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction, button):
        self.page = (self.page - 1) % self.pages
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def next(self, interaction, button):
        self.page = (self.page + 1) % self.pages
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

# ---------- AI ----------
def ask_ai(prompt, uid):
    history = conversation_memory.get(uid, [])

    messages = [{"role": "system", "content": f"Short replies. Personality: {personality}"}]

    for i, msg in enumerate(history[-MEMORY_LIMIT:]):
        role = "user" if i % 2 == 0 else "assistant"
        messages.append({"role": role, "content": msg})

    messages.append({"role": "user", "content": prompt})

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=60
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(e)
        return "brain lag"

# ---------- READY ----------
@bot.event
async def on_ready():
    global IS_LEADER

    print(f"{bot.user} starting...")

    channel = bot.get_channel(LOCK_CHANNEL_ID)
    if not channel:
        print("Lock channel not found")
        return

    async for msg in channel.history(limit=5):
        if msg.author == bot.user and msg.content == "LOCK":
            IS_LEADER = False
            print("Another instance active → silent")
            return

    await channel.send("LOCK")
    IS_LEADER = True
    print("Leader instance active")

# ---------- MESSAGE ----------
@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if not IS_LEADER:
        return

    now = time.time()

    # GLOBAL LOCK
    if message.id in message_locks:
        if now - message_locks[message.id] < 5:
            return

    message_locks[message.id] = now

    for k in list(message_locks.keys()):
        if now - message_locks[k] > 10:
            del message_locks[k]

    msg = message.content.lower()

    # FILTER
    if message.author.id not in IMMUNE_USERS:
        if any(w in msg.replace(" ", "") for w in ["nigger","sex","rape","raper","retard","motherfucker"]):
            try:
                await message.delete()
            except:
                pass
            await safe_send(message.channel, f"*I'll pretend i didn't see anything {message.author.mention}*")
            return

    # ---------- COMMANDS ----------

    # HELP
    if msg == "yen commands":
        if not message.author.guild_permissions.administrator:
            return

        cmds = [
            "yen kick @user","yen ban @user","yen timeout @user <min>","yen untimeout @user",
            "yen purge <n>","yen slowmode <sec>","yen nick @user <name>","yen warn @user",
            "yen slime @user","yen restore @user","yen <text>","hey yen"
        ]

        view = HelpView(message.author, cmds)
        await message.channel.send(embed=view.get_embed(), view=view)
        return

    # PURGE
    if msg.startswith("yen purge"):
        if not message.author.guild_permissions.manage_messages:
            return
        try:
            n = int(msg.split()[2])
        except:
            await safe_send(message.channel, "invalid number")
            return

        deleted = await message.channel.purge(limit=n + 1)
        await safe_send(message.channel, f"deleted {len(deleted)-1} messages")
        return

    # NICK
    if msg.startswith("yen nick"):
        if not message.author.guild_permissions.manage_nicknames:
            return
        if not message.mentions:
            return

        target = message.mentions[0]

        if not can_moderate(message.author, target, message.guild):
            return

        try:
            name = message.content.split(" ", 3)[3]
        except:
            return

        try:
            await target.edit(nick=name)
            await safe_send(message.channel, "nick changed")
        except:
            await safe_send(message.channel, "failed (role hierarchy?)")
        return

    # ---------- AI ----------
    if not (msg.startswith("yen") or msg.startswith("hey yen") or random.randint(1,50) == 1):
        return

    uid = str(message.author.id)

    if uid in user_cooldowns:
        if now - user_cooldowns[uid] < COOLDOWN_TIME:
            return

    user_cooldowns[uid] = now

    clean = message.content.replace("yen", "", 1).strip()
    reply = ask_ai(clean, uid)

    conversation_memory.setdefault(uid, []).append(clean)
    conversation_memory[uid].append(reply)
    conversation_memory[uid] = conversation_memory[uid][-MEMORY_LIMIT:]

    await asyncio.sleep(random.uniform(0.4, 1.2))
    await safe_send(message.channel, reply, ref=message)

# ---------- RUN ----------
bot.run(TOKEN)