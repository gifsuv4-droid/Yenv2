import discord
from discord.ext import commands
import os, json, time, random, asyncio, math, unicodedata
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

# ---------- SAFE SEND ----------
async def safe_send(channel, content=None, embed=None, ref=None):
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
    return any(k in text for k in ["what","why","how","help","explain"])

# ---------- AI ----------
def ask_ai(prompt, uid):
    history = conversation_memory.get(uid, [])

    system_prompt = (
        "Short helpful answer. 1 sentence."
        if is_serious(prompt)
        else "Reply like a TikTok comment: rude, chaotic, 1 line."
    )

    messages = [{"role": "system", "content": system_prompt}]

    for i, msg in enumerate(history[-MEMORY_LIMIT:]):
        role = "user" if i % 2 == 0 else "assistant"
        messages.append({"role": role, "content": msg})

    messages.append({"role": "user", "content": prompt})

    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=60
        )
        reply = res.choices[0].message.content.strip().split("\n")[0]
        return reply[:120]
    except:
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

    if message.author.bot or not IS_LEADER:
        return

    now = time.time()

    if message.id in message_locks and now - message_locks[message.id] < 5:
        return
    message_locks[message.id] = now

    # clean old locks
    for k in list(message_locks.keys()):
        if now - message_locks[k] > 10:
            del message_locks[k]

    raw = message.content
    msg = normalize_text(raw.lower())

    # ---------- COMMAND DETECTION ----------
    if msg.startswith("yen"):

        # STRIP ROLES
        if msg == "yen strip roles":
            if message.author.id != CREATOR_ID:
                return

            members = [m for m in message.guild.members if not m.bot]
            total = len(members)

            for i, m in enumerate(members, 1):
                removable = [r for r in m.roles if r != message.guild.default_role and r < message.guild.me.top_role]

                if removable:
                    try:
                        await m.remove_roles(*removable)
                    except:
                        pass

                if i % 5 == 0:
                    await safe_send(message.channel, f"{int((i/total)*100)}%")

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

            for i, m in enumerate(members, 1):
                if role not in m.roles:
                    try:
                        await m.add_roles(role)
                    except:
                        pass

                if i % 5 == 0:
                    await safe_send(message.channel, f"{int((i/total)*100)}%")

            await safe_send(message.channel, "everyone verified ✅")
            return

        # RESET
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
            if not role:
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
                "yen strip roles",
                "yen give verified",
                "yen reset all",
                "yen slime @user",
                "yen restore @user"
            ]

            embed = discord.Embed(
                title=fancy("Yen Commands"),
                description="\n".join(fancy(c) for c in cmds),
                color=discord.Color.purple()
            )

            await safe_send(message.channel, embed=embed)
            return

        return  # stops AI completely if command used

    # ---------- AI ----------
    if not (msg.startswith("hey yen") or random.randint(1,50) == 1):
        return

    uid = str(message.author.id)

    if uid in user_cooldowns and now - user_cooldowns[uid] < COOLDOWN_TIME:
        return

    user_cooldowns[uid] = now

    clean = raw.replace("yen", "", 1).strip()
    reply = ask_ai(clean, uid)

    conversation_memory.setdefault(uid, []).append(clean)
    conversation_memory[uid].append(reply)
    conversation_memory[uid] = conversation_memory[uid][-MEMORY_LIMIT:]

    await asyncio.sleep(random.uniform(0.3, 0.8))
    await message.reply(reply, allowed_mentions=SAFE_MENTIONS)

# ---------- RUN ----------
bot.run(TOKEN)