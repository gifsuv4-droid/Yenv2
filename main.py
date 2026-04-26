import discord
from discord.ext import commands
import os
import json
import time
import random
import asyncio
from groq import Groq

TOKEN = os.getenv("TOKEN")
GROQ_KEY = os.getenv("GROQ_KEY")

client = Groq(api_key=GROQ_KEY)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="", intents=intents)

SAFE_MENTIONS = discord.AllowedMentions(everyone=False, roles=False, users=True)

CREATOR_ID = 1383111113016872980

personality = "chaotic sarcastic discord gremlin"
chaos_mode = True
chaos_level = 3

memory_file = "memory.json"
uwu_file = "uwu.json"
gossip_file = "gossip.json"
slime_file = "slimed.json"

conversation_memory = {}
user_cooldowns = {}
processing_messages = {}

MEMORY_LIMIT = 8
COOLDOWN_TIME = 4

# ---------- FILE ----------

def load_json(file):
    if os.path.exists(file):
        with open(file) as f:
            return json.load(f)
    return {}

def save_json(data, file):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

uwulocks = load_json(uwu_file)
gossip = load_json(gossip_file)
slimed_users = load_json(slime_file)

# ---------- UWU ----------

def uwuify(text):
    return text.replace("r","w").replace("l","w") + random.choice([" uwu"," owo"," >w<"])

# ---------- INTENT ----------

def detect_intent(text):
    text = text.lower()
    if any(k in text for k in ["how","why","explain","help","what is"]):
        return "serious"
    if any(k in text for k in ["roast","lol","funny","joke"]):
        return "joke"
    return "casual"

# ---------- AI ----------

def ask_ai(prompt, user_id):

    history = conversation_memory.get(user_id, [])
    history_text = "\n".join(history[-MEMORY_LIMIT:])

    intent = detect_intent(prompt)

    tone = {
        "serious": "Be helpful and concise.",
        "joke": "Be sarcastic and funny.",
        "casual": "Be natural."
    }[intent]

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": f"""
You are Yen, a Discord AI.

Personality: {personality}

Rules:
- 1-2 sentences only
- no repeating yourself
- answer properly if serious

Tone: {tone}
"""
            },
            {
                "role": "user",
                "content": f"{history_text}\nUser: {prompt}"
            }
        ],
        max_tokens=60
    )

    reply = completion.choices[0].message.content.strip()

    if len(reply) < 3:
        reply = "skill issue"

    return reply

# ---------- EVENTS ----------

@bot.event
async def on_ready():
    print("Yen Online")

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    now = time.time()

    # HARD duplicate lock
    if message.id in processing_messages:
        if now - processing_messages[message.id] < 6:
            return
    processing_messages[message.id] = now

    msg = message.content.lower()

# ---------- SLIME ----------

    if msg.startswith("yen slime"):
        if message.author.id != CREATOR_ID:
            return

        if not message.mentions:
            await message.channel.send("who?")
            return

        target = message.mentions[0]

        role = discord.utils.find(lambda r: r.name.lower() == "slimed", message.guild.roles)
        if role is None:
            role = await message.guild.create_role(name="SLIMED")

        slimed_users[str(target.id)] = {
            "roles": [r.id for r in target.roles if r != message.guild.default_role],
            "nickname": target.nick
        }
        save_json(slimed_users, slime_file)

        removable = [r for r in target.roles if r != message.guild.default_role and r < message.guild.me.top_role]

        if removable:
            await target.remove_roles(*removable)

        await target.add_roles(role)

        try:
            await target.edit(nick="*SLIMED*")
        except:
            pass

        await message.channel.send(f"{target.mention} got slimed")
        return

# ---------- RESTORE ----------

    if msg.startswith("yen restore"):
        if message.author.id != CREATOR_ID:
            return

        if not message.mentions:
            return

        target = message.mentions[0]
        saved = slimed_users.get(str(target.id))

        if not saved:
            return

        roles = [message.guild.get_role(r) for r in saved["roles"] if message.guild.get_role(r)]
        if roles:
            await target.add_roles(*roles)

        role = discord.utils.find(lambda r: r.name.lower() == "slimed", message.guild.roles)
        if role:
            await target.remove_roles(role)

        try:
            await target.edit(nick=saved["nickname"])
        except:
            pass

        del slimed_users[str(target.id)]
        save_json(slimed_users, slime_file)

        await message.channel.send(f"{target.mention} restored")
        return

# ---------- GOSSIP ----------

    if len(message.content.split()) > 4 and not msg.startswith("yen"):
        gossip.setdefault("logs", []).append(message.content)
        gossip["logs"] = gossip["logs"][-50:]
        save_json(gossip, gossip_file)

# ---------- TRIGGER ----------

    triggers = ["hey yen","hi yen","yo yen","hello yen"]

    if not (
        msg.startswith("yen")
        or any(msg.startswith(t) for t in triggers)
        or random.randint(1,50) == 1
    ):
        return

# ---------- COOLDOWN ----------

    uid = str(message.author.id)

    if uid in user_cooldowns and now - user_cooldowns[uid] < COOLDOWN_TIME:
        return

    user_cooldowns[uid] = now

# ---------- CLEAN ----------

    clean = message.content
    if clean.lower().startswith("yen"):
        clean = clean[3:].strip()

# ---------- AI ----------

    reply = ask_ai(clean, uid)

    conversation_memory.setdefault(uid, []).append(clean)
    conversation_memory[uid].append(reply)
    conversation_memory[uid] = conversation_memory[uid][-MEMORY_LIMIT:]

# ---------- CHAOS (merged, not extra send) ----------

    if chaos_mode and random.randint(1,10) <= chaos_level:
        reply = random.choice([
            "this server is cursed",
            "i'm watching",
            "something feels off"
        ])

# ---------- UWU ----------

    if str(message.author.id) in uwulocks:
        reply = uwuify(reply)

# ---------- ANTI DUPLICATE INSTANCE ----------

    await asyncio.sleep(random.uniform(0.4, 1.2))

    async for m in message.channel.history(limit=5):
        if m.author == bot.user and m.reference:
            if m.reference.message_id == message.id:
                return

# ---------- SEND ----------

    await message.reply(reply, allowed_mentions=SAFE_MENTIONS)

# ---------- START ----------

bot.run(TOKEN)