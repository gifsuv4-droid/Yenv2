import discord
from discord.ext import commands
import os, json, time, random, asyncio, math
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
def fancy(text):
    normal = "abcdefghijklmnopqrstuvwxyz0123456789"
    fancy_ = "𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝚖𝚗𝚘𝚙𝚚𝚛𝚜𝚝𝚞𝚟𝚠𝚡𝚢𝚣0123456789"
    return text.translate(str.maketrans(normal, fancy_))

def is_serious(text):
    text = text.lower()
    keywords = ["what","why","how","explain","help","teach","difference","meaning"]
    return any(k in text for k in keywords)

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

    serious = is_serious(prompt)

    system_prompt = (
        "Short helpful answer. 1 sentence. No line breaks."
        if serious else
        "Reply like a TikTok comment: short, chaotic, rude, 1 line."
    )

    messages = [{"role": "system", "content": system_prompt}]

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

        reply = completion.choices[0].message.content.strip()
        reply = reply.split("\n")[0]
        return reply[:120] if reply else "..."
    except Exception as e:
        print(e)
        return "brain lag"

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

    # ---------- COMMANDS FIRST (PREVENT AI INTERFERENCE) ----------

    # STRIP ROLES
    if msg == "yen strip roles":
        if message.author.id != CREATOR_ID:
            return

        members = [m for m in message.guild.members if not m.bot]
        total = len(members)
        done = 0

        for m in members:
            removable = [
                r for r in m.roles
                if r != message.guild.default_role and r < message.guild.me.top_role
            ]

            if removable:
                try:
                    await m.remove_roles(*removable)
                except:
                    pass

            done += 1
            if done % 5 == 0:
                percent = int((done / total) * 100)
                await safe_send(message.channel, f"stripping roles... {percent}%")

        await safe_send(message.channel, "done stripping roles 💀")
        return

    # GIVE VERIFIED
    if msg == "yen give verified":
        if message.author.id != CREATOR_ID:
            return

        role = discord.utils.get(message.guild.roles, name="Verified")
        if not role:
            await safe_send(message.channel, "verified role not found")
            return

        members = [m for m in message.guild.members if not m.bot]
        total = len(members)
        done = 0

        for m in members:
            if role not in m.roles:
                try:
                    await m.add_roles(role)
                except:
                    pass

            done += 1
            if done % 5 == 0:
                percent = int((done / total) * 100)
                await safe_send(message.channel, f"giving verified... {percent}%")

        await safe_send(message.channel, "everyone verified ✅")
        return

    # RESET MEMORY
    if msg == "yen reset all":
        if message.author.id != CREATOR_ID:
            return

        conversation_memory.clear()
        await safe_send(message.channel, "memory wiped 🧠💀")
        return

    # SLIME
    if msg.startswith("yen slime") and message.author.id == CREATOR_ID:
        if not message.mentions:
            return

        t = message.mentions[0]

        role = discord.utils.get(message.guild.roles, name="SLIMED")
        if role is None:
            role = await message.guild.create_role(name="SLIMED")

        slimed_users[str(t.id)] = {
            "roles": [r.id for r in t.roles if r != message.guild.default_role],
            "nickname": t.nick
        }
        save_json(slimed_users, slime_file)

        removable = [r for r in t.roles if r != message.guild.default_role and r < message.guild.me.top_role]

        if removable:
            await t.remove_roles(*removable)

        await t.add_roles(role)

        try:
            await t.edit(nick="*SLIMED*")
        except:
            pass

        await safe_send(message.channel, f"{t.mention} got slimed 🟢")
        return

    # RESTORE
    if msg.startswith("yen restore") and message.author.id == CREATOR_ID:
        if not message.mentions:
            return

        t = message.mentions[0]
        data = slimed_users.get(str(t.id))

        if not data:
            return

        roles = [message.guild.get_role(r) for r in data["roles"] if message.guild.get_role(r)]

        if roles:
            await t.add_roles(*roles)

        role = discord.utils.get(message.guild.roles, name="SLIMED")
        if role:
            await t.remove_roles(role)

        try:
            await t.edit(nick=data["nickname"])
        except:
            pass

        del slimed_users[str(t.id)]
        save_json(slimed_users, slime_file)

        await safe_send(message.channel, f"{t.mention} restored")
        return

    # HELP
    if msg == "yen commands":
        cmds = [
            "yen reset all (creator only)",
            "yen slime @user",
            "yen restore @user",
            "yen <text>",
            "hey yen"
        ]

        view = HelpView(message.author, cmds)
        await message.channel.send(embed=view.get_embed(), view=view)
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

    await asyncio.sleep(random.uniform(0.3, 0.8))
    await safe_send(message.channel, reply, ref=message)

# ---------- RUN ----------
bot.run(TOKEN)