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

last_ai_time = 0
personality = "chaotic sarcastic discord gremlin"
chaos_mode = True
chaos_level = 3

memory_file = "memory.json"
uwu_file = "uwu.json"
gossip_file = "gossip.json"

conversation_memory = {}
last_deleted_message = {}

MEMORY_LIMIT = 8

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
    faces = [" uwu"," owo"," >w<"," ^w^"]
    return text + random.choice(faces)

# ---------- AI ----------

def ask_ai(prompt, user_id, reply_context=None):

    history = conversation_memory.get(user_id, [])
    history_text = "\n".join(history)

    random_gossip = random.choice(gossip.get("logs", [""])) if gossip.get("logs") else ""

    context_text = ""
    if reply_context:
        context_text = f"\nMessage being replied to:\n{reply_context}\n"

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": f"""
You are Yen, a smart chaotic Discord AI.

Personality:
{personality}

Rules:
- Talk like a real Discord user
- Be sarcastic, funny, or chill
- Use short replies normally
- Use longer replies ONLY when needed
- Never be unnecessarily long
- React to reply context if present
"""
            },
            {
                "role": "user",
                "content": f"""
Conversation:
{history_text}

{context_text}

User: {prompt}
"""
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
    print("Yen AI Online")

@bot.event
async def on_message_delete(message):
    last_deleted_message[message.channel.id] = {
        "content": message.content,
        "author": message.author.name
    }

@bot.event
async def on_message(message):

    global last_ai_time, chaos_mode, chaos_level, personality

    if message.author.bot:
        return

    msg = message.content.lower()

# ---------- COMMANDS ----------

    if msg == "yen help":
        await message.channel.send("just talk to me or use chaos/memory/uwu")
        return

    if msg == "yen chaos":
        chaos_mode = not chaos_mode
        await message.channel.send(f"chaos: {'on' if chaos_mode else 'off'}")
        return

    if msg.startswith("yen personality"):
        personality = msg.replace("yen personality", "").strip()
        await message.channel.send(f"new personality: {personality}")
        return

# ---------- GOSSIP LEARNING ----------

    if len(message.content.split()) > 4:
        gossip.setdefault("logs", []).append(message.content)
        gossip["logs"] = gossip["logs"][-50:]
        save_json(gossip, gossip_file)

# ---------- AI TRIGGER (UPDATED) ----------

    triggers = ["hey yen", "yo yen", "hi yen", "hello yen"]

    should_reply = (
        msg.startswith("yen")
        or any(t in msg for t in triggers)
        or random.randint(1, 50) == 1
    )

    if not should_reply:
        return

    if time.time() - last_ai_time < 4:
        return

    last_ai_time = time.time()

# ---------- REPLY CONTEXT ----------

    reply_context = None
    if message.reference:
        try:
            replied = await message.channel.fetch_message(message.reference.message_id)
            reply_context = f"{replied.author.name}: {replied.content}"
        except:
            pass

# ---------- CLEAN PROMPT ----------

    clean_prompt = message.content

    if clean_prompt.lower().startswith("yen"):
        clean_prompt = clean_prompt[3:].strip()

    for t in triggers:
        if t in clean_prompt.lower():
            clean_prompt = clean_prompt.lower().replace(t, "").strip()

# ---------- AI ----------

    uid = str(message.author.id)

    reply = ask_ai(clean_prompt, uid, reply_context)

    conversation_memory.setdefault(uid, []).append(clean_prompt)
    conversation_memory[uid].append(reply)
    conversation_memory[uid] = conversation_memory[uid][-MEMORY_LIMIT:]

# ---------- CHAOS ----------

    if chaos_mode and random.randint(1,10) <= chaos_level:
        await message.channel.send(random.choice([
            "this server feels cursed",
            "someone here is lying",
            "im watching all of you"
        ]))

# ---------- UWU LOCK ----------

    if str(message.author.id) in uwulocks:
        reply = uwuify(reply)

    await message.channel.send(reply, allowed_mentions=SAFE_MENTIONS)

# ---------- START ----------

keep_alive()
bot.run(TOKEN)