import discord
from discord.ext import commands
from discord.utils import utcnow
from datetime import timedelta
import os
import json
import time
import random
from groq import Groq
from flask import Flask
from threading import Thread

TOKEN=os.getenv("TOKEN")
GROQ_KEY=os.getenv("GROQ_KEY")

client=Groq(api_key=GROQ_KEY)

intents=discord.Intents.all()
bot=commands.Bot(command_prefix="",intents=intents)

SUMMON_TIMEOUT=300
summoned=False
last_action_time=0
last_ai_time=0

personality="mysterious"
interaction_count=0

memory_file="memory.json"
uwu_file="uwu.json"
jokes_file="jokes.json"
profile_file="profiles.json"

# ---------- LOAD DATA ----------

def load_json(file):
    if os.path.exists(file):
        with open(file) as f:
            return json.load(f)
    return {}

def save_json(data,file):
    with open(file,"w") as f:
        json.dump(data,f,indent=2)

memory=load_json(memory_file)
uwulocks=load_json(uwu_file)
inside_jokes=load_json(jokes_file)
profiles=load_json(profile_file)

# ---------- KEEP ALIVE ----------

app=Flask("")

@app.route("/")
def home():
    return "Yen Ascended"

def run():
    port=int(os.environ.get("PORT",8080))
    app.run(host="0.0.0.0",port=port)

def keep_alive():
    Thread(target=run).start()

# ---------- HELPERS ----------

def uwuify(text):
    text=text.replace("r","w").replace("l","w")
    return text+" uwu"

def evolve_personality():
    global personality
    personalities=[
        "mysterious",
        "playful",
        "chaotic",
        "wise",
        "sarcastic",
        "sleepy"
    ]
    personality=random.choice(personalities)

def detect_personality(msg):

    if any(x in msg for x in ["lol","lmao","haha"]):
        return "chaotic"

    if any(x in msg for x in ["thanks","thank you","appreciate"]):
        return "wholesome"

    if any(x in msg for x in ["why","how","meaning"]):
        return "philosopher"

    if any(x in msg for x in ["idiot","stupid"]):
        return "troll"

    return "normal"

def should_ai_respond(message,msg):

    if message.reference:
        return True

    if "?" in msg:
        return True

    if "yen" in msg:
        return True

    if random.randint(1,20)==1:
        return True

    return False

def ask_ai(prompt):

    completion=client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role":"system",
                "content":f"You are Yen, a mystical discord spirit with a {personality} personality."
            },
            {"role":"user","content":prompt}
        ]
    )

    return completion.choices[0].message.content

# ---------- READY ----------

@bot.event
async def on_ready():
    print("Yen Ascended Form Online")

# ---------- MESSAGE ----------

@bot.event
async def on_message(message):

    global summoned,last_action_time,last_ai_time,interaction_count

    if message.author.bot:
        return

    msg=message.content.lower()
    uid=str(message.author.id)

# ---------- USER PROFILE ----------

    if uid not in profiles:
        profiles[uid]={
            "name":message.author.name,
            "personality":"unknown",
            "likes":[]
        }

    profiles[uid]["personality"]=detect_personality(msg)

    if "love" in msg:
        item=msg.split("love")[-1].strip()
        profiles[uid]["likes"].append(item)

    save_json(profiles,profile_file)

# ---------- ARGUMENT DETECTION ----------

    if any(x in msg for x in ["stupid","idiot","shut up"]):

        if random.randint(1,5)==1:
            await message.channel.send(
                "⚖️ Yen senses conflict... peace is advised."
            )

# ---------- CHAOS EVENTS ----------

    if random.randint(1,300)==1:

        events=[
            "🌧 Wisdom rain: 'The quieter you become, the more you can hear.'",
            "🐸 Meme storm has arrived.",
            "🔮 Yen senses chaos in the timeline."
        ]

        await message.channel.send(random.choice(events))

# ---------- SUMMON ----------

    if "hey yen" in msg or "hi yen" in msg:

        summoned=True
        last_action_time=time.time()

        await message.channel.send("🌙 Yen awakens.")
        return

# ---------- IDLE ----------

    if summoned and time.time()-last_action_time>SUMMON_TIMEOUT:

        summoned=False
        await message.channel.send("🕯 Yen fades into silence.")
        return

# ---------- PROFILE COMMAND ----------

    if msg=="yen profile":

        data=profiles.get(uid)

        likes=", ".join(data["likes"][:5]) or "unknown"

        await message.channel.send(
            f"""
👤 Profile

Name: {data['name']}
Personality: {data['personality']}
Likes: {likes}
"""
        )
        return

# ---------- HELP ----------

    if msg=="yen help":

        await message.channel.send("""
🔮 Yen Ascended Commands

Summon
hey yen
hi yen

AI
Talk normally when Yen is awake

Memory
yen remember <fact>
yen memory
yen profile

Server Lore
yen jokes

Moderation
yen purge <number>
yen ban @user
yen kick @user
yen mute @user

Curses
yen uwulock @user
yen unlock @user

Fun
yen judge @user
""")
        return

# ---------- AI CHAT ----------

    if summoned and should_ai_respond(message,msg):

        if time.time()-last_ai_time<5:
            return

        last_ai_time=time.time()
        last_action_time=time.time()

        interaction_count+=1

        if interaction_count%40==0:
            evolve_personality()

        reply=ask_ai(message.content)

        if message.author.id in uwulocks:
            reply=uwuify(reply)

        await message.channel.send(reply)

    await bot.process_commands(message)

keep_alive()
bot.run(TOKEN)