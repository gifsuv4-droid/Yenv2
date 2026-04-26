import discord
from discord.ext import commands
import os
import json
import time
import random
from groq import Groq

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

# ---------- UWU ----------

def uwuify(text):
    text = text.replace("r","w").replace("l","w")
    return text + random.choice([" uwu"," owo"," >w<"])

# ---------- INTENT DETECTION ----------

def detect_intent(text):
    text = text.lower()

    serious_keywords = [
        "how", "why", "explain", "what is", "help",
        "can you", "teach", "difference", "guide"
    ]

    joke_keywords = [
        "lol", "lmao", "roast", "joke", "funny",
        "sus", "weird", "rate me"
    ]

    if any(k in text for k in serious_keywords):
        return "serious"
    if any(k in text for k in joke_keywords):
        return "joke"

    return "casual"

# ---------- AI ----------

def ask_ai(prompt, user_id, reply_context=None):

    history = conversation_memory.get(user_id, [])
    history_text = "\n".join(history[-MEMORY_LIMIT:])

    random_gossip = random.choice(gossip.get("logs", [""])) if gossip.get("logs") else ""

    context_text = f"\nReplying to:\n{reply_context}\n" if reply_context else ""

    intent = detect_intent(prompt)

    if intent == "serious":
        tone_instruction = "Be helpful, clear, and concise. Answer properly but briefly."
    elif intent == "joke":
        tone_instruction = "Be sarcastic, chaotic, or funny."
    else:
        tone_instruction = "Be casual and natural."

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
- Keep replies short (1–2 sentences)
- If it's a real question, give a helpful answer
- Don't dismiss serious questions
- Be sarcastic only when appropriate
- Avoid long paragraphs
- Adjust tone based on user intent

Tone:
{tone_instruction}

Known gossip:
{random_gossip}
"""
            },
            {
                "role": "user",
                "content": f"{history_text}\n{context_text}\nUser: {prompt}"
            }
        ],
        max_tokens=60
    )

    reply = completion.choices[0].message.content.strip()

    # fallback
    if len(reply) < 3:
        reply = random.choice([
            "that sounds illegal",
            "skill issue",
            "i refuse to respond to that"
        ])

    # HARD LIMIT
    words = reply.split()
    if len(words) > 25:
        reply = " ".join(words[:25]) + "..."

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

        role = discord.utils.find(lambda r: r.name.lower() == "slimed", message.guild.roles)

        if role is None:
            role = await message.guild.create_role(name="SLIMED", reason="Slime system")

        slimed_users[str(target.id)] = {
            "roles": [r.id for r in target.roles if r != message.guild.default_role],
            "nickname": target.nick
        }
        save_json(slimed_users, slime_file)

        removable = [
            r for r in target.roles
            if r != message.guild.default_role and r < message.guild.me.top_role
        ]

        if removable:
            await target.remove_roles(*removable)
        else:
            await message.channel.send("⚠️ couldn't remove some roles")

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
            await message.channel.send("no saved data")
            return

        roles_to_restore = [
            message.guild.get_role(rid)
            for rid in saved["roles"]
            if message.guild.get_role(rid)
        ]

        if roles_to_restore:
            await target.add_roles(*roles_to_restore)

        role = discord.utils.find(lambda r: r.name.lower() == "slimed", message.guild.roles)
        if role:
            await target.remove_roles(role)

        try:
            await target.edit(nick=saved["nickname"])
        except:
            pass

        del slimed_users[str(target.id)]
        save_json(slimed_users, slime_file)

        await message.channel.send(f"{target.mention} restored ✅")
        return

# ---------- GOSSIP ----------

    if (
        len(message.content.split()) > 4
        and not msg.startswith("yen")
    ):
        gossip.setdefault("logs", []).append(message.content)
        gossip["logs"] = gossip["logs"][-50:]
        save_json(gossip, gossip_file)

# ---------- TRIGGER ----------

    triggers = ["hey yen", "yo yen", "hi yen", "hello yen"]

    if not (
        msg.startswith("yen")
        or any(msg.startswith(t) for t in triggers)
        or random.randint(1, 50) == 1
    ):
        return

# ---------- COOLDOWN ----------

    uid = str(message.author.id)
    now = time.time()

    if uid in user_cooldowns and now - user_cooldowns[uid] < COOLDOWN_TIME:
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

# ---------- UWU ----------

    if str(message.author.id) in uwulocks:
        reply = uwuify(reply)

    await message.channel.send(reply, allowed_mentions=SAFE_MENTIONS)

# ---------- START ----------

bot.run(TOKEN)