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

TOKEN=os.getenv("TOKEN")
GROQ_KEY=os.getenv("GROQ_KEY")

client=Groq(api_key=GROQ_KEY)

intents=discord.Intents.all()
bot=commands.Bot(command_prefix="",intents=intents)

SAFE_MENTIONS=discord.AllowedMentions(
    everyone=False,
    roles=False,
    users=True
)

CREATOR_ID=1383111113016872980

uwu_file="uwu.json"
memory_file="memory.json"

conversation_memory={}
last_deleted_message={}

MEMORY_LIMIT=6
last_ai_time=0
interaction_count=0
personality="mysterious"

# ---------- FILE HELPERS ----------

def load_json(file):
    if os.path.exists(file):
        with open(file) as f:
            return json.load(f)
    return {}

def save_json(data,file):
    with open(file,"w") as f:
        json.dump(data,f,indent=2)

uwulocks=load_json(uwu_file)
memory_data=load_json(memory_file)

# ---------- KEEP ALIVE ----------

app=Flask("")

@app.route("/")
def home():
    return "Yen Running"

def run():
    port=int(os.environ.get("PORT",8080))
    app.run(host="0.0.0.0",port=port)

def keep_alive():
    Thread(target=run).start()

# ---------- HELPERS ----------

def uwuify(text):

    if not text:
        return "uwu"

    text=text.replace("r","w").replace("l","w")
    text=text.replace("R","W").replace("L","W")

    faces=[" uwu"," owo"," >w<"," ^w^"]

    return text+random.choice(faces)

def evolve_personality():
    global personality
    personalities=["mysterious","playful","chaotic","wise","sarcastic","sleepy"]
    personality=random.choice(personalities)

def should_ai_respond(message,msg):

    if message.reference:
        return True

    if "yen" in msg:
        return True

    if random.randint(1,35)==1:
        return True

    return False

# ---------- EMBED TEXT EXTRACTOR ----------

def extract_embed_text(message):

    text=message.content or ""

    for embed in message.embeds:

        if embed.title:
            text+=" "+embed.title

        if embed.description:
            text+=" "+embed.description

        for field in embed.fields:
            text+=" "+field.name+" "+field.value

    return text.strip()

# ---------- WEBHOOK SEND ----------

async def webhook_send(channel,author,text,embed=None):

    webhook=None

    webhooks=await channel.webhooks()

    for w in webhooks:
        if w.name=="yenhook":
            webhook=w

    if webhook is None:
        webhook=await channel.create_webhook(name="yenhook")

    await webhook.send(
        text,
        username=author.name,
        avatar_url=author.display_avatar.url,
        embed=embed,
        allowed_mentions=SAFE_MENTIONS
    )

# ---------- BOT WAR ----------

async def bot_civil_war(channel,guild):

    bots=[m for m in guild.members if m.bot and m.id!=bot.user.id]

    if len(bots)<2:
        return

    a,b=random.sample(bots,2)

    lines=[
        f"{a.name} just insulted {b.name}",
        f"{b.name} respond",
        f"{a.name} calm down",
        f"{b.name} explain yourself"
    ]

    for line in lines:
        await channel.send(line,allowed_mentions=SAFE_MENTIONS)
        await asyncio.sleep(1.5)

# ---------- AI ----------

def ask_ai(prompt,user_id):

    if int(user_id)==CREATOR_ID and random.randint(1,4)==1:
        return random.choice(["yes.","correct.","agreed.","obviously."])

    history=conversation_memory.get(user_id,[])
    history_text="\n".join(history)

    completion=client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role":"system","content":f"You are Yen. Personality:{personality}. Max 5 lines."},
            {"role":"user","content":f"{history_text}\n{prompt}"}
        ],
        max_tokens=70
    )

    reply=completion.choices[0].message.content
    return "\n".join(reply.split("\n")[:5])

# ---------- READY ----------

@bot.event
async def on_ready():
    print("Yen Online")

# ---------- DELETE TRACK ----------

@bot.event
async def on_message_delete(message):

    last_deleted_message[message.channel.id]={
        "content":message.content,
        "author":message.author.name
    }

# ---------- MESSAGE EDIT ----------

@bot.event
async def on_message_edit(before,after):

    if str(after.author.id) not in uwulocks:
        return

    try:
        await after.delete()
    except:
        return

    text=uwuify(extract_embed_text(after))
    await webhook_send(after.channel,after.author,text)

# ---------- MESSAGE ----------

@bot.event
async def on_message(message):

    global last_ai_time,interaction_count

    if message.author.id==bot.user.id:
        return

    msg=message.content.lower()

# ---------- TRUE UWULOCK ----------

    if str(message.author.id) in uwulocks:

        try:
            await message.delete()
        except:
            pass

        text=extract_embed_text(message)
        text=uwuify(text)

        await webhook_send(message.channel,message.author,text)

        return

# ---------- ANTI EVERYONE ----------

    if "@everyone" in message.content or "@here" in message.content:

        try:
            await message.delete()
            await message.channel.send(
                "everyone ping blocked",
                allowed_mentions=SAFE_MENTIONS
            )
        except:
            pass
        return

# ---------- COMMANDS ----------

    if msg=="yen help":

        embed=discord.Embed(title="Yen Commands")

        embed.add_field(name="memory",
        value="yen remember <fact>\nyen memory",inline=False)

        embed.add_field(name="uwu curse",
        value="yen uwulock @user\nyen unlock @user",inline=False)

        embed.add_field(name="utility",
        value="yen snipe",inline=False)

        embed.add_field(name="chaos",
        value="yen start war",inline=False)

        await message.channel.send(embed=embed,allowed_mentions=SAFE_MENTIONS)
        return

# ---------- MEMORY ----------

    if msg.startswith("yen remember"):

        fact=message.content[12:].strip()
        gid=str(message.guild.id)

        memory_data.setdefault(gid,[])
        memory_data[gid].append(fact)

        save_json(memory_data,memory_file)

        await message.channel.send("remembered")
        return

    if msg=="yen memory":

        gid=str(message.guild.id)
        facts=memory_data.get(gid,[])

        if not facts:
            await message.channel.send("i remember nothing")
            return

        text="\n".join([f"• {x}" for x in facts[:10]])

        await message.channel.send(text)
        return

# ---------- UWULOCK ----------

    if msg.startswith("yen uwulock"):

        if not message.mentions:
            return

        target=message.mentions[0]

        uwulocks[str(target.id)]=True
        save_json(uwulocks,uwu_file)

        await message.channel.send(f"{target.name} uwulocked")
        return

    if msg.startswith("yen unlock"):

        if not message.mentions:
            return

        target=message.mentions[0]

        if str(target.id) in uwulocks:
            del uwulocks[str(target.id)]

        save_json(uwulocks,uwu_file)

        await message.channel.send(f"{target.name} unlocked")
        return

# ---------- SNIPE ----------

    if msg=="yen snipe":

        data=last_deleted_message.get(message.channel.id)

        if not data:
            await message.channel.send("nothing to snipe")
            return

        await message.channel.send(
            f"{data['author']} deleted:\n{data['content']}"
        )
        return

# ---------- BOT WAR ----------

    if msg.startswith("yen start war"):
        await bot_civil_war(message.channel,message.guild)
        return

# ---------- AI ----------

    if should_ai_respond(message,msg):

        if time.time()-last_ai_time<4:
            return

        last_ai_time=time.time()

        interaction_count+=1

        if interaction_count%40==0:
            evolve_personality()

        uid=str(message.author.id)

        reply=ask_ai(message.content,uid)

        conversation_memory.setdefault(uid,[]).append(message.content)
        conversation_memory[uid].append(reply)

        conversation_memory[uid]=conversation_memory[uid][-MEMORY_LIMIT:]

        await message.channel.send(reply,allowed_mentions=SAFE_MENTIONS)

keep_alive()
bot.run(TOKEN)