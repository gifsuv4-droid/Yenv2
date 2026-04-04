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

last_ai_time=0
interaction_count=0
personality="mysterious"

memory_file="memory.json"
uwu_file="uwu.json"
jokes_file="jokes.json"

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
memory_data=load_json(jokes_file)


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
        return text

    text=text.replace("r","w")
    text=text.replace("l","w")

    faces=[" uwu"," owo"," >w<"," (・`ω´・)"]

    return text+random.choice(faces)


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


def should_ai_respond(message,msg):

    if message.reference:
        return True

    if "yen" in msg:
        return True

    if random.randint(1,35)==1:
        return True

    return False


# ---------- WEBHOOK IMPERSONATION ----------

async def impersonate(channel,user,text):

    webhook=await channel.create_webhook(name=user.name)

    await webhook.send(
        text,
        username=user.name,
        avatar_url=user.display_avatar.url,
        allowed_mentions=SAFE_MENTIONS
    )

    await webhook.delete()


# ---------- BOT ARGUMENT ----------

async def random_bot_argument(channel,guild):

    bots=[m for m in guild.members if m.bot and m.id!=bot.user.id]

    if len(bots)<2:
        return

    if random.randint(1,120)!=1:
        return

    a,b=random.sample(bots,2)

    lines_a=[
        "bro you look outdated",
        "your commands are useless",
        "who coded you",
        "your uptime is fake"
    ]

    lines_b=[
        "ok bro calm down",
        "at least people use me",
        "nobody asked",
        "stop talking"
    ]

    await impersonate(channel,a,random.choice(lines_a))
    await asyncio.sleep(1.2)
    await impersonate(channel,b,random.choice(lines_b))


# ---------- BOT CIVIL WAR ----------

async def bot_civil_war(channel,guild,starter=None):

    bots=[m for m in guild.members if m.bot and m.id!=bot.user.id]

    if len(bots)<2:
        return

    if starter:
        others=[b for b in bots if b.id!=starter.id]
        if not others:
            return
        target=random.choice(others)
    else:
        starter,target=random.sample(bots,2)

    lines=[
        (starter,"bro your uptime is fake"),
        (target,"says the bot that crashes daily"),
        (starter,"at least people use my commands"),
        (target,"ok grandpa"),
        (starter,"touch grass")
    ]

    for user,text in lines:
        await impersonate(channel,user,text)
        await asyncio.sleep(1.4)


# ---------- AI ----------

def ask_ai(prompt,user_id):

    if int(user_id)==CREATOR_ID and random.randint(1,4)==1:
        return random.choice([
            "yes.",
            "correct.",
            "agreed.",
            "obviously.",
            "you're right."
        ])

    history=conversation_memory.get(user_id,[])
    history_text="\n".join(history)

    completion=client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role":"system","content":f"You are Yen. Personality: {personality}"},
            {"role":"user","content":f"{history_text}\n{prompt}"}
        ],
        max_tokens=70
    )

    reply=completion.choices[0].message.content
    return "\n".join(reply.split("\n")[:5])


# ---------- READY ----------

@bot.event
async def on_ready():
    print("Yen Total Chaos Online")


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

    global last_ai_time,interaction_count

    if message.author==bot.user:
        return

    msg=message.content.lower()


# ---------- TOTAL UWULOCK ----------

    if str(message.author.id) in uwulocks:

        text=uwuify(message.content)

        # EMBEDS
        if message.embeds:

            embed=message.embeds[0]

            new_embed=discord.Embed(
                title=uwuify(embed.title),
                description=uwuify(embed.description),
                color=embed.color
            )

            for field in embed.fields:
                new_embed.add_field(
                    name=uwuify(field.name),
                    value=uwuify(field.value),
                    inline=field.inline
                )

            try:
                await message.delete()
            except:
                pass

            await message.channel.send(embed=new_embed)
            return

        # USERS
        if not message.author.bot and not message.webhook_id:

            try:
                await message.delete()
            except:
                pass

            await impersonate(message.channel,message.author,text)

        # BOTS
        else:

            await message.reply(text,allowed_mentions=SAFE_MENTIONS)

        return


# ---------- ANTI EVERYONE ----------

    if "@everyone" in message.content or "@here" in message.content:

        try:
            await message.delete()
            await message.channel.send(
                "⚠ everyone ping blocked",
                allowed_mentions=SAFE_MENTIONS
            )
        except:
            pass
        return


# ---------- RANDOM BOT CHAOS ----------

    if message.guild:

        await random_bot_argument(message.channel,message.guild)

        if random.randint(1,180)==1:
            await bot_civil_war(message.channel,message.guild)


# ---------- WAR COMMAND ----------

    if msg.startswith("yen start war"):

        starter=None

        if message.mentions:
            starter=message.mentions[0]

        await bot_civil_war(message.channel,message.guild,starter)
        return


# ---------- HELP ----------

    if msg=="yen help":

        embed=discord.Embed(title="🔮 Yen Commands",color=0x9b59b6)

        embed.add_field(name="Memory",value="yen remember / yen memory",inline=False)
        embed.add_field(name="Moderation",value="yen mute @user",inline=False)
        embed.add_field(name="Curses",value="yen uwulock @user",inline=False)
        embed.add_field(name="Utility",value="yen snipe",inline=False)
        embed.add_field(name="Chaos",value="yen start war",inline=False)

        await message.channel.send(embed=embed)
        return


# ---------- MEMORY ----------

    if msg.startswith("yen remember"):

        fact=message.content[12:].strip()

        gid=str(message.guild.id)

        memory_data.setdefault(gid,[])
        memory_data[gid].append(fact)

        save_json(memory_data,jokes_file)

        await message.channel.send("🧠 remembered")
        return


# ---------- SNIPE ----------

    if msg=="yen snipe":

        data=last_deleted_message.get(message.channel.id)

        if not data:
            await message.channel.send("nothing to snipe")
            return

        await message.channel.send(
            f"👻 {data['author']} deleted:\n{data['content']}"
        )
        return


# ---------- UWULOCK COMMAND ----------

    if msg.startswith("yen uwulock"):

        if not message.mentions:
            return

        target=message.mentions[0]

        uwulocks[str(target.id)]=True
        save_json(uwulocks,uwu_file)

        await message.channel.send(f"{target.name} has been uwulocked")
        return


# ---------- UNLOCK ----------

    if msg.startswith("yen unlock"):

        if not message.mentions:
            return

        target=message.mentions[0]

        if str(target.id) in uwulocks:
            del uwulocks[str(target.id)]

        save_json(uwulocks,uwu_file)

        await message.channel.send(f"{target.name} is free")
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

        if str(message.author.id) in uwulocks:
            reply=uwuify(reply)

        await message.channel.send(reply)


keep_alive()
bot.run(TOKEN)