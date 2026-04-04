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

    if embed.footer:
        new.set_footer(text=uwuify(embed.footer.text))

    if embed.thumbnail:
        new.set_thumbnail(url=embed.thumbnail.url)

    if embed.image:
        new.set_image(url=embed.image.url)

    return new

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

# ---------- WEBHOOK SEND ----------

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

# ---------- BOT ARGUMENT ----------

async def random_bot_argument(channel,guild):

    bots=[m for m in guild.members if m.bot and m.id!=bot.user.id]

    if len(bots)<1:
        return

    if random.randint(1,120)!=1:
        return

    target=random.choice(bots)

    insults=[
        "do you even work",
        "bro nobody uses you",
        "you were coded in notepad",
        "explain yourself",
        "calm down"
    ]

    await channel.send(
        f"{target.name} {random.choice(insults)}",
        allowed_mentions=SAFE_MENTIONS
    )

# ---------- BOT CIVIL WAR ----------

async def bot_civil_war(channel,guild):

    bots=[m for m in guild.members if m.bot and m.id!=bot.user.id]

    if len(bots)<2:
        return

    a,b=random.sample(bots,2)

    lines=[
        f"{a.name} just called {b.name} outdated",
        f"{b.name} respond to that",
        f"{a.name} explain yourself",
        f"{b.name} this is awkward",
        "i'm just watching"
    ]

    for line in lines:
        await channel.send(line,allowed_mentions=SAFE_MENTIONS)
        await asyncio.sleep(1.5)

# ---------- AI ----------

def ask_ai(prompt,user_id):

    if int(user_id)==CREATOR_ID and random.randint(1,4)==1:
        return random.choice(["yes.","correct.","agreed.","obviously.","you're right."])

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
    print("Yen Absolute Form Online")

# ---------- DELETE TRACK ----------

@bot.event
async def on_message_delete(message):

    last_deleted_message[message.channel.id]={
        "content":message.content,
        "author":message.author.name
    }

# ---------- EDIT UWULOCK ----------

@bot.event
async def on_message_edit(before,after):

    if str(after.author.id) not in uwulocks:
        return

    try:
        await after.delete()
    except:
        return

    if after.embeds:
        embed=uwu_embed(after.embeds[0])
        await webhook_send(after.channel,after.author,embed=embed)
    else:
        text=uwuify(after.content)
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

        if message.embeds:
            embed=uwu_embed(message.embeds[0])
            await webhook_send(message.channel,message.author,embed=embed)
        else:
            text=uwuify(message.content)
            await webhook_send(message.channel,message.author,text)

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

# ---------- RANDOM CHAOS ----------

    if message.guild:

        await random_bot_argument(message.channel,message.guild)

        if random.randint(1,180)==1:
            await bot_civil_war(message.channel,message.guild)

# ---------- WAR COMMAND ----------

    if msg.startswith("yen start war"):

        await bot_civil_war(message.channel,message.guild)
        return

# ---------- HELP ----------

    if msg=="yen help":

        embed=discord.Embed(title="🔮 Yen Commands",color=0x9b59b6)

        embed.add_field(name="Summon",value="hey yen / hi yen",inline=False)
        embed.add_field(name="Memory",value="yen remember <fact>\nyen memory",inline=False)
        embed.add_field(name="Moderation",value="yen mute @user",inline=False)
        embed.add_field(name="Curses",value="yen uwulock @user / yen unlock @user",inline=False)
        embed.add_field(name="Utility",value="yen snipe",inline=False)
        embed.add_field(name="Chaos",value="yen start war",inline=False)

        await message.channel.send(embed=embed,allowed_mentions=SAFE_MENTIONS)
        return

# ---------- MEMORY ----------

    if msg.startswith("yen remember"):

        fact=message.content[12:].strip()
        gid=str(message.guild.id)

        memory_data.setdefault(gid,[])
        memory_data[gid].append(fact)

        save_json(memory_data,jokes_file)

        await message.channel.send("🧠 remembered",allowed_mentions=SAFE_MENTIONS)
        return

    if msg=="yen memory":

        gid=str(message.guild.id)
        facts=memory_data.get(gid,[])

        if not facts:
            await message.channel.send("i remember nothing")
            return

        text="\n".join([f"• {x}" for x in facts[:10]])

        await message.channel.send(f"🧠 Memories\n\n{text}")
        return

# ---------- SNIPE ----------

    if msg=="yen snipe":

        data=last_deleted_message.get(message.channel.id)

        if not data:
            await message.channel.send("nothing to snipe")
            return

        await message.channel.send(f"👻 {data['author']} deleted:\n{data['content']}")
        return

# ---------- MUTE ----------

    if msg.startswith("yen mute"):

        if not message.author.guild_permissions.manage_messages:
            return

        if not message.mentions:
            return

        member=message.mentions[0]

        mute_role=discord.utils.get(message.guild.roles,name="Muted")

        if mute_role is None:

            mute_role=await message.guild.create_role(name="Muted")

            for channel in message.guild.channels:
                await channel.set_permissions(mute_role,send_messages=False)

        await member.add_roles(mute_role)

        await message.channel.send(f"{member.mention} muted")
        return

# ---------- UWULOCK ----------

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

        await message.channel.send(reply,allowed_mentions=SAFE_MENTIONS)

keep_alive()
bot.run(TOKEN)