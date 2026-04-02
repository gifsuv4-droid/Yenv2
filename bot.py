import discord
from discord.ext import commands
import json
import os
import time
import random
from datetime import timedelta
from discord.utils import utcnow
from groq import Groq
from flask import Flask
from threading import Thread

# Web server for uptime monitoring
app = Flask('__name__')

@app.route('/')
def home():
    return "Yen is alive."

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

client = Groq(api_key=os.getenv("GROQ_KEY"))

CREATOR_ID = 1383111113016872980
YOUNG_MASTERS = [1435002295493333194,1464487262082302095]

UWU_FILE = "uwulocks.json"
MEMORY_FILE = "memory.json"

uwulocks = json.load(open(UWU_FILE)) if os.path.exists(UWU_FILE) else {}
memory = json.load(open(MEMORY_FILE)) if os.path.exists(MEMORY_FILE) else {}

summoned = False
last_action_time = 0
SUMMON_TIMEOUT = 300

MOODS = ["mysterious","playful","chaotic","wise"]
current_mood = random.choice(MOODS)

AI_COOLDOWN = 3
last_ai_time = 0


def save_uwu():
    with open(UWU_FILE,"w") as f:
        json.dump(uwulocks,f,indent=4)

def save_memory():
    with open(MEMORY_FILE,"w") as f:
        json.dump(memory,f,indent=4)

def is_creator(user):
    return user.id == CREATOR_ID

def is_young_master(user):
    return user.id in YOUNG_MASTERS


def ask_ai(prompt,author):

    if is_creator(author):
        system_prompt = (
            "You are Yen, a loyal digital spirit. "
            "The user speaking is your creator and you treat them with admiration and devotion."
        )

    elif is_young_master(author):
        system_prompt = (
            "You are Yen, a respectful spirit. "
            "The user speaking is one of the Young Masters and you treat them with respect and friendliness."
        )

    else:
        system_prompt = f"You are Yen, a {current_mood} digital spirit living inside Discord."

    try:

        chat = client.chat.completions.create(
            messages=[
                {"role":"system","content":system_prompt},
                {"role":"user","content":prompt}
            ],
            model="llama3-8b-8192"
        )

        return chat.choices[0].message.content

    except Exception as e:
        print(e)
        return "🌙 The spirit realm is unstable right now."


def uwuify(text):

    faces=["(・`ω´・)",";;w;;","owo","UwU",">w<","^w^"]
    actions=["nya~","rawr","*tail wag*","*pounces*","*nuzzles*"]

    text=text.replace("r","w").replace("l","w")
    text=text.replace("R","W").replace("L","W")

    words=text.split()

    if random.randint(1,2)==1:
        words.append(random.choice(faces))

    if random.randint(1,3)==1:
        words.append(random.choice(actions))

    return " ".join(words)


def is_summoned():

    global summoned,last_action_time

    if not summoned:
        return False

    if time.time()-last_action_time>SUMMON_TIMEOUT:
        return False

    return True


def can_act(author,target,bot_member):

    if target.top_role>=author.top_role:
        return False

    if target.top_role>=bot_member.top_role:
        return False

    return True


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


@bot.event
async def on_message(message):

    global summoned,last_action_time,last_ai_time

    if message.author.bot:
        return

    msg=message.content.lower()
    uid=str(message.author.id)

    if uid not in memory:
        memory[uid]={"name":message.author.name,"messages":0}

    memory[uid]["messages"]+=1
    save_memory()


    if "yen" in msg and not summoned:
        summoned=True
        last_action_time=time.time()
        await message.channel.send("🌙 I heard my name... the spirit awakens.")


    if random.randint(1,200)==1:

        if "hello" in msg or "hi" in msg:
            await message.channel.send("🌙 I sense greetings in the air...")

        elif "who" in msg and "yen" in msg:
            await message.channel.send("🔮 I am Yen, a spirit bound to this server.")


    if random.randint(1,120)==1:

        events=[
            "🌙 A cold wind passes through the server...",
            "🔮 The spirit realm flickers briefly.",
            "🕯️ A candle lights somewhere in the void..."
        ]

        await message.channel.send(random.choice(events))


    if is_creator(message.author) and random.randint(1,5)==1:

        greetings=[
            "🌙 My creator has arrived.",
            "✨ Welcome back, creator.",
            "🔮 I await your command."
        ]

        await message.channel.send(random.choice(greetings))


    if msg=="yen, i summon thee!":

        summoned=True
        last_action_time=time.time()

        await message.channel.send("✨ The spirit Yen awakens...")
        return


    if summoned and time.time()-last_action_time>SUMMON_TIMEOUT:
        summoned=False
        await message.channel.send("🕯️ Yen fades back into silence...")
        return


    if str(message.author.id) in uwulocks:

        uwu=uwuify(message.content)

        try:

            await message.delete()

            webhooks=await message.channel.webhooks()
            webhook=None

            for wh in webhooks:
                if wh.name=="YenWebhook":
                    webhook=wh

            if webhook is None:
                webhook=await message.channel.create_webhook(name="YenWebhook")

            await webhook.send(
                content=uwu,
                username=message.author.display_name,
                avatar_url=message.author.display_avatar.url
            )

        except:
            pass

        return


    if not is_summoned():
        return


    if not msg.startswith("yen"):
        return


    last_action_time=time.time()


    if msg.startswith("yen shutdown") and is_creator(message.author):

        await message.channel.send("🌙 Returning to the spirit realm...")
        await bot.close()


    if msg.startswith("yen mood") and is_creator(message.author):

        await message.channel.send(f"Current mood: {current_mood}")


    if msg.startswith("yen purge"):

        if not message.author.guild_permissions.administrator:
            return

        amount=int(msg.split(" ")[2])

        await message.channel.purge(limit=amount)

        await message.channel.send(f"🧹 {amount} messages erased.")


    if message.mentions:

        target=message.mentions[0]
        member=message.guild.get_member(target.id)
        bot_member=message.guild.me

        if not can_act(message.author,member,bot_member):
            return await message.channel.send("You cannot do this action.")

        if "ban" in msg:
            await member.ban()
            await message.channel.send(f"{member.mention} has been banished.")
            return

        if "kick" in msg:
            await member.kick()
            await message.channel.send(f"{member.mention} has been expelled.")
            return

        if "mute" in msg or "silence" in msg:

            until=utcnow()+timedelta(minutes=10)
            await member.timeout(until)

            await message.channel.send(f"{member.mention} has been silenced.")
            return

        if "uwulock" in msg or "curse" in msg:

            uwulocks[str(member.id)]=True
            save_uwu()

            await message.channel.send(f"{member.mention}'s speech has been cursed 🐾")
            return

        if "unlock" in msg or "restore" in msg:

            if str(member.id) not in uwulocks:
                return await message.channel.send("This person is not Uwulocked.")

            del uwulocks[str(member.id)]
            save_uwu()

            await message.channel.send(f"{member.mention} may speak normally again.")
            return


    if time.time()-last_ai_time<AI_COOLDOWN:
        await message.channel.send("⏳ The spirit needs a moment...")
        return

    last_ai_time=time.time()

    prompt=message.content[3:].strip()

    if prompt=="":
        await message.channel.send("Yes?")
        return

    reply=ask_ai(prompt,message.author)

    prefix=random.choice([
        "🌙 Yen whispers:",
        "✨ The spirit says:",
        "🔮 Yen responds:",
        "🕯️ From the spirit realm:"
    ])

    await message.channel.send(f"{prefix} {reply}")


keep_alive()
bot.run(os.getenv("TOKEN"))