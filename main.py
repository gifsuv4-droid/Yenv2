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

SAFE_MENTIONS=discord.AllowedMentions(everyone=False,roles=False,users=True)

last_ai_time=0
interaction_count=0
personality="lazy chaotic spirit"
chaos_mode=True
chaos_level=3

memory_file="memory.json"
uwu_file="uwu.json"

conversation_memory={}
last_deleted_message={}

MEMORY_LIMIT=6
CREATOR_ID=1383111113016872980

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
memories=load_json(memory_file)

# ---------- KEEP ALIVE ----------

app=Flask("")

@app.route("/")
def home():
    return "Yen Online"

def run():
    port=int(os.environ.get("PORT",8080))
    app.run(host="0.0.0.0",port=port)

def keep_alive():
    Thread(target=run).start()

# ---------- HELPERS ----------

def uwuify(text):

    if not text:
        text="..."

    text=text.replace("r","w").replace("l","w")
    text=text.replace("R","W").replace("L","W")

    faces=[" uwu"," owo"," >w<"," ^w^"," (・`ω´・)"]

    return text+random.choice(faces)

def uwu_embed(embed):

    new=discord.Embed(
        title=uwuify(embed.title) if embed.title else None,
        description=uwuify(embed.description) if embed.description else None,
        color=embed.color
    )

    for field in embed.fields:
        new.add_field(
            name=uwuify(field.name),
            value=uwuify(field.value),
            inline=field.inline
        )

    return new

# ---------- HELP EMBED ----------

def help_embed():

    embed=discord.Embed(
        title="Yen Commands",
        color=discord.Color.purple()
    )

    embed.add_field(
        name="Core",
        value="""
yen help
yen chaos
yen chaos level <1-5>
yen personality <type>
""",
        inline=False
    )

    embed.add_field(
        name="Fun",
        value="""
yen roast @user
yen judge
yen rate
yen choose option | option | option
yen coinflip
yen roll
yen prophecy
""",
        inline=False
    )

    embed.add_field(
        name="Chaos",
        value="""
yen start war @bot
yen civilwar
""",
        inline=False
    )

    embed.add_field(
        name="UwU",
        value="""
yen uwulock @user
yen unlock @user
""",
        inline=False
    )

    embed.add_field(
        name="Utility",
        value="""
yen snipe
yen remember <fact>
yen memories
""",
        inline=False
    )

    return embed

# ---------- WEBHOOK ----------

async def webhook_send(channel,author,text=None,embed=None):

    webhook=None

    webhooks=await channel.webhooks()

    for w in webhooks:
        if w.name=="yenhook":
            webhook=w

    if webhook is None:
        webhook=await channel.create_webhook(name="yenhook")

    await webhook.send(
        text,
        embed=embed,
        username=author.name,
        avatar_url=author.display_avatar.url,
        allowed_mentions=SAFE_MENTIONS
    )

# ---------- AI ----------

def ask_ai(prompt,user_id):

    if random.randint(1,4)!=1:
        short=[
            "nah",
            "ok",
            "maybe",
            "idk",
            "sure",
            "probably",
            "nah fuck you",
            "whatever"
        ]
        return random.choice(short)

    history=conversation_memory.get(user_id,[])
    history_text="\n".join(history)

    completion=client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role":"system","content":f"You are Yen. Personality:{personality}. Replies must be extremely short."},
            {"role":"user","content":f"{history_text}\n{prompt}"}
        ],
        max_tokens=15
    )

    return completion.choices[0].message.content.strip()

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

# ---------- MESSAGE ----------

@bot.event
async def on_message(message):

    global last_ai_time,interaction_count,chaos_mode,chaos_level,personality

    if message.author.id==bot.user.id:
        return

    msg=message.content.lower()

# TRUE UWULOCK

    if message.author.bot:

        if str(message.author.id) in uwulocks:

            if message.embeds:

                embed=uwu_embed(message.embeds[0])

                try:
                    await message.delete()
                except:
                    pass

                await webhook_send(message.channel,message.author,embed=embed)

            elif message.content:

                try:
                    await message.delete()
                except:
                    pass

                await webhook_send(
                    message.channel,
                    message.author,
                    uwuify(message.content)
                )

            return

# HELP

    if msg=="yen help":
        await message.channel.send(embed=help_embed())
        return

# CHAOS

    if msg=="yen chaos":

        chaos_mode=not chaos_mode

        await message.channel.send(
            f"chaos mode: {'on' if chaos_mode else 'off'}"
        )
        return

# CHAOS LEVEL

    if msg.startswith("yen chaos level"):

        try:
            level=int(msg.split(" ")[3])

            if 1<=level<=5:

                chaos_level=level
                await message.channel.send(f"chaos level {level}")

        except:
            pass

        return

# START WAR

    if msg.startswith("yen start war"):

        if message.mentions:

            target=message.mentions[0]

            lines=[
                f"{target.name} explain yourself",
                "bro nobody uses you",
                "your code outdated",
                "skill issue"
            ]

            for line in lines:
                await message.channel.send(line)
                await asyncio.sleep(1)

        return

# CIVIL WAR

    if msg=="yen civilwar":

        bots=[m for m in message.guild.members if m.bot and m.id!=bot.user.id]

        if len(bots)<2:
            return

        a,b=random.sample(bots,2)

        lines=[
            f"{a.name} just called {b.name} outdated",
            f"{b.name} respond to that",
            f"{a.name} explain yourself",
            "this is awkward"
        ]

        for line in lines:
            await message.channel.send(line)
            await asyncio.sleep(1.5)

        return

# FUN COMMANDS

    if msg.startswith("yen roast"):

        if message.mentions:

            user=message.mentions[0]

            roasts=[
                "built like a microwave",
                "npc energy",
                "wifi brain",
                "skill issue"
            ]

            await message.channel.send(
                f"{user.mention} {random.choice(roasts)}",
                allowed_mentions=SAFE_MENTIONS
            )

        return

    if msg.startswith("yen judge"):
        await message.channel.send(random.choice(["cringe","based","npc"]))
        return

    if msg.startswith("yen rate"):
        await message.channel.send(f"{random.randint(1,10)}/10")
        return

    if msg.startswith("yen choose"):

        parts=message.content.split("|")

        if len(parts)>1:
            await message.channel.send(random.choice(parts[1:]).strip())

        return

    if msg=="yen coinflip":
        await message.channel.send(random.choice(["heads","tails"]))
        return

    if msg=="yen roll":
        await message.channel.send(f"🎲 {random.randint(1,6)}")
        return

    if msg=="yen prophecy":

        prophecies=[
            "chaos approaches",
            "wifi will betray you",
            "destiny says maybe"
        ]

        await message.channel.send("🔮 "+random.choice(prophecies))
        return

# PERSONALITY

    if msg.startswith("yen personality"):

        new=msg.replace("yen personality","").strip()

        if new:
            personality=new
            await message.channel.send(f"personality -> {new}")

        return

# SNIPE

    if msg=="yen snipe":

        data=last_deleted_message.get(message.channel.id)

        if not data:
            await message.channel.send("nothing to snipe")
            return

        await message.channel.send(
            f"{data['author']} deleted:\n{data['content']}"
        )

        return

# UWULOCK

    if msg.startswith("yen uwulock"):

        if message.mentions:

            target=message.mentions[0]

            uwulocks[str(target.id)]=True
            save_json(uwulocks,uwu_file)

            await message.channel.send(f"{target.name} uwulocked")

        return

# UNLOCK

    if msg.startswith("yen unlock"):

        if message.mentions:

            target=message.mentions[0]

            if str(target.id) in uwulocks:
                del uwulocks[str(target.id)]

            save_json(uwulocks,uwu_file)

            await message.channel.send(f"{target.name} freed")

        return

# MEMORY

    if msg.startswith("yen remember"):

        fact=message.content.replace("yen remember","").strip()

        if fact:

            memories.setdefault("facts",[]).append(fact)
            save_json(memories,memory_file)

            await message.channel.send("noted")

        return

    if msg=="yen memories":

        facts=memories.get("facts",[])

        if not facts:
            await message.channel.send("i remember nothing")
            return

        await message.channel.send("\n".join(facts[-10:]))

        return

# AI

    if "yen" in msg or random.randint(1,60)==1:

        if time.time()-last_ai_time<6:
            return

        last_ai_time=time.time()

        uid=str(message.author.id)

        reply=ask_ai(message.content,uid)

        conversation_memory.setdefault(uid,[]).append(message.content)
        conversation_memory[uid].append(reply)

        conversation_memory[uid]=conversation_memory[uid][-MEMORY_LIMIT:]

        if str(message.author.id) in uwulocks:
            reply=uwuify(reply)

        if message.author.id==CREATOR_ID:
            reply="yes"

        await message.channel.send(reply,allowed_mentions=SAFE_MENTIONS)

keep_alive()
bot.run(TOKEN)