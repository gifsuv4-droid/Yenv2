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
user_cooldowns = {}
processed_messages = set()

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
gossip = load_json(gossip_file)
slimed_users = load_json(slime_file)

# ---------- UWU ----------

def uwuify(text):
    text = text.replace("r","w").replace("l","w")
    return text + random.choice([" uwu"," owo"," >w<"])

# ---------- INTENT ----------

def detect_intent(text):
    text = text.lower()

    serious = ["how","why","explain","what is","help","guide"]
    joke = ["lol","roast","joke","funny","rate"]

    if any(k in text for k in serious):
        return "serious"
    if any(k in text for k in joke):
        return "joke"
    return "casual"

# ---------- AI ----------

def ask_ai(prompt, user_id, reply_context=None):

    history = conversation_memory.get(user_id, [])
    history_text = "\n".join(history[-MEMORY_LIMIT:])

    intent = detect_intent(prompt)

    if intent == "serious":
        tone = "Be helpful and concise."
    elif intent == "joke":
        tone = "Be sarcastic and funny."
    else:
        tone = "Be casual."

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
- Help if it's a real question
- Avoid long paragraphs
- Don't repeat yourself

Tone:
{tone}
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

    # fallback
    if len(reply) < 3:
        reply = random.choice([
            "that sounds illegal",
            "skill issue",
            "no comment"
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
async def on_message(message):

    if message.author.bot:
        return

    # ---------- DUPLICATE FIX ----------
    if message.id in processed_messages:
        return

    processed_messages.add(message.id)

    if len(processed_messages) > 1000:
        processed_messages.clear()

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

    triggers = ["hey yen","yo yen","hi yen","hello yen"]

    if not (
        msg.startswith("yen")
        or any(msg.startswith(t) for t in triggers)
        or random.randint(1,50) == 1
    ):
        return

# ---------- COOLDOWN ----------

    uid = str(message.author.id)
    now = time.time()

    if uid in user_cooldowns and now - user_cooldowns[uid] < COOLDOWN_TIME:
        return

    user_cooldowns[uid] = now

# ---------- CLEAN INPUT ----------

    clean = message.content
    if clean.lower().startswith("yen"):
        clean = clean[3:].strip()

# ---------- AI ----------

    reply = ask_ai(clean, uid)

    conversation_memory.setdefault(uid, []).append(clean)
    conversation_memory[uid].append(reply)
    conversation_memory[uid] = conversation_memory[uid][-MEMORY_LIMIT:]

# ---------- CHAOS (FIXED) ----------

    if chaos_mode and random.randint(1,10) <= chaos_level:
        reply = random.choice([
            "this server is cursed",
            "something feels off",
            "i'm watching"
        ])

# ---------- UWU ----------

    if str(message.author.id) in uwulocks:
        reply = uwuify(reply)

# ---------- SINGLE SEND ----------

    await message.channel.send(reply, allowed_mentions=SAFE_MENTIONS)

# ---------- START ----------

bot.run(TOKEN)