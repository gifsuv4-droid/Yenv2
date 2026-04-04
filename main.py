import discord
from discord.ext import commands
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
profile_file="profiles.json"
jokes_file="jokes.json"
gossip_file="gossip.json"

conversation_memory={}
server_jokes={}
last_deleted_message={}

MEMORY_LIMIT=6

CREATOR_ID = 1383111113016872980

# ---------- LOAD DATA ----------

def load_json(file):
    if os.path.exists(file):
        with open(file) as f:
            return json.load(f)
    return {}

def save_json(data,file):
    with open(file,"w") as f:
        json.dump(data,f,indent=2)

uwulocks=load_json(uwu_file)
profiles=load_json(profile_file)
jokes_memory=load_json(jokes_file)
gossip_memory=load_json(gossip_file)

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
    personalities=["mysterious","playful","chaotic","wise","sarcastic","sleepy"]
    personality=random.choice(personalities)

def detect_personality(msg):

    if any(x in msg for x in ["lol","lmao","haha"]):
        return "chaotic"

    if any(x in msg for x in ["thanks","thank you"]):
        return "wholesome"

    if any(x in msg for x in ["why","how"]):
        return "philosopher"

    return "normal"

def should_ai_respond(message,msg):

    if message.reference:
        return True

    if "yen" in msg:
        return True

    if random.randint(1,35)==1:
        return True

    return False

# ---------- MEME LEARNING ----------

def learn_joke(msg):

    words=msg.split()

    for w in words:
        if len(w)>5:
            server_jokes[w]=server_jokes.get(w,0)+1

# ---------- LORE ----------

def detect_lore(msg,gid):

    lore_words=["legend","lore","remember this","historic","never forget"]

    if any(x in msg for x in lore_words):

        jokes_memory.setdefault(gid,[])
        jokes_memory[gid].append(msg)

        save_json(jokes_memory,jokes_file)

# ---------- GOSSIP ----------

def learn_gossip(msg,user,gid):

    triggers=["i like","i love","i hate","i did","i ate"]

    if any(x in msg for x in triggers):

        gossip_memory.setdefault(gid,[])
        gossip_memory[gid].append(f"{user} once said: {msg}")

        save_json(gossip_memory,gossip_file)

# ---------- AI ----------

def ask_ai(prompt,user_id,gid):

    if int(user_id)==CREATOR_ID and random.randint(1,4)==1:
        return random.choice(["yes.","correct.","agreed.","obviously.","you're right."])

    if random.randint(1,30)==1:
        return random.choice(["maybe.","probably not.","uncertain.","who knows.","idk."])

    history=conversation_memory.get(user_id,[])
    history_text="\n".join(history)

    completion=client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role":"system",
                "content":f"""
You are Yen, a mystical discord spirit.

Personality: {personality}

Rules:
- maximum 5 lines
- usually 1-3 lines
- casual discord tone
"""
            },
            {
                "role":"user",
                "content":f"{history_text}\n{prompt}"
            }
        ],
        max_tokens=70
    )

    reply=completion.choices[0].message.content
    lines=reply.split("\n")
    return "\n".join(lines[:5])

# ---------- READY ----------

@bot.event
async def on_ready():
    print("Yen Final Form Online")

# ---------- DELETE TRACK ----------

@bot.event
async def on_message_delete(message):

    if message.author.bot:
        return

    last_deleted_message[message.channel.id]={
        "content":message.content,
        "author":message.author.name
    }

# ---------- MESSAGE ----------

@bot.event
async def on_message(message):

    global summoned,last_action_time,last_ai_time,interaction_count

    if message.author.bot:
        return

    msg=message.content.lower()
    uid=str(message.author.id)
    gid=str(message.guild.id)

    learn_joke(msg)
    detect_lore(msg,gid)
    learn_gossip(msg,message.author.name,gid)

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

# ---------- HELP ----------

    if msg=="yen help":

        embed=discord.Embed(
            title="🔮 Yen Commands",
            color=0x9b59b6
        )

        embed.add_field(name="Summon",value="hey yen / hi yen",inline=False)
        embed.add_field(name="Profile",value="yen profile",inline=False)
        embed.add_field(name="Memory",value="yen remember <fact>\nyen memory",inline=False)
        embed.add_field(name="Moderation",value="yen mute @user",inline=False)
        embed.add_field(name="Curses",value="yen uwulock @user / yen unlock @user",inline=False)
        embed.add_field(name="Webhooks",value="yen create webhook <text>\nyen say @user <text>",inline=False)
        embed.add_field(name="Utility",value="yen snipe",inline=False)

        await message.channel.send(embed=embed)
        return

# ---------- PROFILE ----------

    if msg=="yen profile":

        profiles.setdefault(uid,{
            "name":message.author.name,
            "personality":detect_personality(msg),
            "likes":[]
        })

        data=profiles[uid]

        await message.channel.send(
f"""👤 Profile

Name: {data['name']}
Personality: {data['personality']}
"""
        )
        return

# ---------- MEMORY ----------

    if msg.startswith("yen remember"):

        fact=message.content[12:].strip()

        jokes_memory.setdefault(gid,[])
        jokes_memory[gid].append(fact)

        save_json(jokes_memory,jokes_file)

        await message.channel.send("🧠 remembered.")
        return

    if msg=="yen memory" or "what do you remember" in msg:

        server_facts=jokes_memory.get(gid,[])

        if not server_facts:
            await message.channel.send("i remember nothing yet.")
            return

        memory="\n".join([f"• {x}" for x in server_facts[:10]])

        await message.channel.send(f"🧠 Memories\n\n{memory}")
        return

# ---------- SNIPE ----------

    if msg=="yen snipe":

        data=last_deleted_message.get(message.channel.id)

        if not data:
            await message.channel.send("nothing to snipe.")
            return

        await message.channel.send(
f"👻 **{data['author']} deleted:**\n{data['content']}"
        )
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

        await message.channel.send(f"{member.mention} muted.")
        return

# ---------- UWULOCK ----------

    if msg.startswith("yen uwulock"):

        if not message.mentions:
            return

        target=message.mentions[0]

        uwulocks[str(target.id)]=True
        save_json(uwulocks,uwu_file)

        await message.channel.send(f"{target.name} has been uwulocked.")
        return

# ---------- UNLOCK ----------

    if msg.startswith("yen unlock"):

        if not message.mentions:
            return

        target=message.mentions[0]

        if str(target.id) in uwulocks:
            del uwulocks[str(target.id)]

        save_json(uwulocks,uwu_file)

        await message.channel.send(f"{target.name} is free.")
        return

# ---------- WEBHOOK ----------

    if msg.startswith("yen create webhook"):

        text=message.content[18:].strip()

        webhook=await message.channel.create_webhook(name="Yen")

        if str(message.author.id) in uwulocks:
            text=uwuify(text)

        await webhook.send(text,username=message.author.name)
        await message.delete()
        return

# ---------- IMPERSONATION ----------

    if msg.startswith("yen say"):

        if not message.mentions:
            return

        target=message.mentions[0]
        text=message.content.split(target.mention,1)[1].strip()

        webhook=await message.channel.create_webhook(name=target.name)

        if str(target.id) in uwulocks:
            text=uwuify(text)

        await webhook.send(
            text,
            username=target.name,
            avatar_url=target.display_avatar.url
        )

        await message.delete()
        return

# ---------- AI ----------

    if should_ai_respond(message,msg):

        if time.time()-last_ai_time<4:
            return

        last_ai_time=time.time()
        last_action_time=time.time()

        interaction_count+=1

        if interaction_count%40==0:
            evolve_personality()

        reply=ask_ai(message.content,uid,gid)

        conversation_memory.setdefault(uid,[]).append(message.content)
        conversation_memory[uid].append(reply)
        conversation_memory[uid]=conversation_memory[uid][-MEMORY_LIMIT:]

        if str(message.author.id) in uwulocks:
            reply=uwuify(reply)

        await message.channel.send(reply)

    await bot.process_commands(message)

keep_alive()
bot.run(TOKEN)