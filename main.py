import discord
from discord.ext import commands
import os
import json
import time
import random
import asyncio
from groq import Groq
from flask import Flask
from threading import Thread

TOKEN = os.getenv("TOKEN")
GROQ_KEY = os.getenv("GROQ_KEY")

client = Groq(api_key=GROQ_KEY)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="", intents=intents)

SAFE_MENTIONS = discord.AllowedMentions(everyone=False, roles=False, users=True)

# ---------- CONFIG ----------

CREATOR_ID = 1383111113016872980

personality = "chaotic sarcastic discord gremlin"
chaos_mode = True
chaos_level = 3

memory_file = "memory.json"
uwu_file = "uwu.json"
gossip_file = "gossip.json"
slime_file = "slimed.json"

conversation_memory = {}
last_deleted_message = {}
user_cooldowns = {}

MEMORY_LIMIT = 8
COOLDOWN_TIME = 4

# ---------- FILE HELPERS ----------

def load_json(file):
    if os.path.exists(file):
        with open(file) as f:
            return json.load(f)
    return {}

def save_json(data, file):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

uwulocks = load_json(uwu_file)
memories = load_json(memory_file)
gossip = load_json(gossip_file)
slimed_users = load_json(slime_file)

# ---------- KEEP ALIVE ----------

app = Flask("")

@app.route("/")
def home():
    return "Yen AI Online"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    Thread(target=run).start()

# ---------- UWU ----------

def uwuify(text):
    text = text.replace("r","w").replace("l","w")
    return text + random.choice([" uwu"," owo"," >w<"])

# ---------- AI ----------

def ask_ai(prompt, user_id, reply_context=None):

    history = conversation_memory.get(user_id, [])
    history_text = "\n".join(history)

    random_gossip = random.choice(gossip.get("logs", [""])) if gossip.get("logs") else ""

    context_text = ""
    if reply_context:
        context_text = f"\nReplying to:\n{reply_context}\n"

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": f"""
You are Yen, a chaotic Discord AI.

Personality: {personality}

Rules:
- Talk like a Discord user
- Mostly short replies
- Longer replies only when needed
- Can roast users
- Use gossip occasionally

Known gossip:
{random_gossip}
"""
            },
            {
                "role": "user",
                "content": f"{history_text}\n{context_text}\nUser: {prompt}"
            }
        ],
        max_tokens=100
    )

    reply = completion.choices[0].message.content.strip()

    if len(reply) < 3:
        reply = random.choice([
            "that sounds illegal",
            "skill issue",
            "i refuse to respond to that"
        ])

    return reply

# ---------- EVENTS ----------

@bot.event
async def on_ready():
    print("Yen Online")

@bot.event
async def on_message_delete(message):
    last_deleted_message[message.channel.id] = {
        "content": message.content,
        "author": message.author.name
    }

@bot.event
async def on_message(message):

    global chaos_mode, chaos_level, personality

    if message.author.bot:
        return

    msg = message.content.lower()

# ---------- SLIME ----------

    if msg.startswith("yen slime"):

        if message.author.id != CREATOR_ID:
            return

        if not message.mentions:
            await message.channel.send("who?")
            return

        target = message.mentions[0]

        role = discord.utils.get(message.guild.roles, name="SLIMED")
        if role is None:
            role = await message.guild.create_role(name="SLIMED")

        slimed_users[str(target.id)] = {
            "roles": [r.id for r in target.roles if r != message.guild.default_role],
            "nickname": target.nick
        }
        save_json(slimed_users, slime_file)

        removable = [r for r in target.roles if r != message.guild.default_role and r < message.guild.me.top_role]

        await target.remove_roles(*removable)
        await target.add_roles(role)

        try:
            await target.edit(nick="*SLIMED*")
        except:
            pass

        await message.channel.send(f"{target.mention} got slimed 🟢")
        return

# ---------- RESTORE ----------

    if msg.startswith("yen restore"):

        if message.author.id != CREATOR_ID:
            return

        if not message.mentions:
            await message.channel.send("who?")
            return

        target = message.mentions[0]

        saved = slimed_users.get(str(target.id))

        if not saved:
            await message.channel.send("no data for this user")
            return

        roles_to_restore = [
            message.guild.get_role(rid)
            for rid in saved["roles"]
            if message.guild.get_role(rid)
        ]

        try:
            await target.add_roles(*roles_to_restore)
        except:
            await message.channel.send("couldn't restore roles")
            return

        role = discord.utils.get(message.guild.roles, name="SLIMED")
        if role:
            try:
                await target.remove_roles(role)
            except:
                pass

        try:
            await target.edit(nick=saved["nickname"])
        except:
            pass

        del slimed_users[str(target.id)]
        save_json(slimed_users, slime_file)

        await message.channel.send(f"{target.mention} restored ✅")
        return

# ---------- GOSSIP LEARNING ----------

    if len(message.content.split()) > 4:
        gossip.setdefault("logs", []).append(message.content)
        gossip["logs"] = gossip["logs"][-50:]
        save_json(gossip, gossip_file)

# ---------- AI TRIGGER (FIXED) ----------

    triggers = ["hey yen", "yo yen", "hi yen", "hello yen"]

    should_reply = False

    if msg.startswith("yen"):
        should_reply = True
    elif any(msg.startswith(t) for t in triggers):
        should_reply = True
    elif random.randint(1, 50) == 1:
        should_reply = True

    if not should_reply:
        return

# ---------- PER USER COOLDOWN ----------

    uid = str(message.author.id)
    now = time.time()

    if uid in user_cooldowns:
        if now - user_cooldowns[uid] < COOLDOWN_TIME:
            return

    user_cooldowns[uid] = now

# ---------- CONTEXT ----------

    reply_context = None
    if message.reference:
        try:
            replied = await message.channel.fetch_message(message.reference.message_id)
            reply_context = f"{replied.author.name}: {replied.content}"
        except:
            pass

    clean = message.content

    if clean.lower().startswith("yen"):
        clean = clean[3:].strip()

    for t in triggers:
        clean = clean.lower().replace(t, "").strip()

# ---------- AI ----------

    reply = ask_ai(clean, uid, reply_context)

    conversation_memory.setdefault(uid, []).append(clean)
    conversation_memory[uid].append(reply)
    conversation_memory[uid] = conversation_memory[uid][-MEMORY_LIMIT:]

# ---------- CHAOS ----------

    if chaos_mode and random.randint(1,10) <= chaos_level:
        await message.channel.send(random.choice([
            "this server is cursed",
            "something feels off",
            "i'm watching"
        ]))

# ---------- UWU LOCK ----------

    if str(message.author.id) in uwulocks:
        reply = uwuify(reply)

    await message.channel.send(reply, allowed_mentions=SAFE_MENTIONS)

# ---------- START ----------

keep_alive()
bot.run(TOKEN)