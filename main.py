import discord
from discord.ext import commands
import os, json, time, random, asyncio, math
from datetime import timedelta
from groq import Groq

TOKEN = os.getenv("TOKEN")
GROQ_KEY = os.getenv("GROQ_KEY")

client = Groq(api_key=GROQ_KEY)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="", intents=intents)

SAFE_MENTIONS = discord.AllowedMentions(everyone=False, roles=False, users=True)

CREATOR_ID = 1383111113016872980

personality = "chaotic sarcastic discord gremlin"
chaos_mode = True
chaos_level = 3

memory_file="memory.json"
uwu_file="uwu.json"
gossip_file="gossip.json"
slime_file="slimed.json"
warn_file="warns.json"

conversation_memory={}
user_cooldowns={}
processing_messages={}

MEMORY_LIMIT=8
COOLDOWN_TIME=4

# ---------- FILE ----------

def load_json(f):
    if os.path.exists(f):
        with open(f) as file:
            return json.load(file)
    return {}

def save_json(d,f):
    with open(f,"w") as file:
        json.dump(d,file,indent=2)

uwulocks=load_json(uwu_file)
gossip=load_json(gossip_file)
slimed_users=load_json(slime_file)
warns=load_json(warn_file)

# ---------- HELPERS ----------

def uwuify(t):
    return t.replace("r","w").replace("l","w")+random.choice([" uwu"," owo"])

def can_moderate(a,t,g):
    return a==g.owner or a.top_role>t.top_role

def fancy(text):
    normal="abcdefghijklmnopqrstuvwxyz"
    fancy_="𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝚖𝚗𝚘𝚙𝚚𝚛𝚜𝚝𝚞𝚟𝚠𝚡𝚢𝚣"
    return text.translate(str.maketrans(normal,fancy_))

# ---------- BUTTON VIEW ----------

class HelpView(discord.ui.View):
    def __init__(self, user, cmds):
        super().__init__(timeout=60)
        self.user=user
        self.cmds=cmds
        self.page=0
        self.per=5
        self.pages=math.ceil(len(cmds)/self.per)

    def get_embed(self):
        chunk=self.cmds[self.page*self.per:(self.page+1)*self.per]
        text="\n".join(fancy(c) for c in chunk)
        return discord.Embed(
            title=fancy(f"Yen Commands ({self.page+1}/{self.pages})"),
            description=text,
            color=discord.Color.purple()
        )

    async def interaction_check(self, interaction):
        return interaction.user == self.user

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction, button):
        self.page=(self.page-1)%self.pages
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def next(self, interaction, button):
        self.page=(self.page+1)%self.pages
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

# ---------- AI ----------

def ask_ai(prompt, uid):
    history=conversation_memory.get(uid,[])
    completion=client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role":"system","content":f"Short replies. Personality: {personality}"},
            {"role":"user","content":"\n".join(history[-MEMORY_LIMIT:])+"\n"+prompt}
        ],
        max_tokens=60
    )
    return completion.choices[0].message.content.strip() or "skill issue"

# ---------- EVENTS ----------

@bot.event
async def on_ready():
    print("Yen Online")

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    msg=message.content.lower()
    now=time.time()

# FILTER
    if any(w in msg.replace(" ","") for w in ["nigger","sex","rape","raper","retard","motherfucker"]):
        try: await message.delete()
        except: pass
        await message.channel.send(f"*I'll pretend i didn't see anything {message.author.mention}*")
        return

# DUPLICATE LOCK
    if message.id in processing_messages:
        if now-processing_messages[message.id]<6:
            return
    processing_messages[message.id]=now

# HELP COMMAND
    if msg=="yen commands":
        if not message.author.guild_permissions.administrator:
            return

        cmds=[
            "yen kick @user","yen ban @user","yen timeout @user <min>","yen untimeout @user","yen purge <n>",
            "yen slowmode <sec>","yen nick @user <name>","yen warn @user",
            "yen slime @user","yen restore @user",
            "yen <text>","hey yen"
        ]

        view=HelpView(message.author,cmds)
        await message.channel.send(embed=view.get_embed(), view=view)
        return

# SLIME / RESTORE
    if msg.startswith("yen slime") and message.author.id==CREATOR_ID:
        if not message.mentions: return
        t=message.mentions[0]
        role=discord.utils.get(message.guild.roles,name="SLIMED") or await message.guild.create_role(name="SLIMED")
        slimed_users[str(t.id)]={"roles":[r.id for r in t.roles if r!=message.guild.default_role],"nickname":t.nick}
        save_json(slimed_users,slime_file)
        await t.edit(nick="*SLIMED*")
        await t.add_roles(role)
        await message.channel.send("slimed")
        return

    if msg.startswith("yen restore") and message.author.id==CREATOR_ID:
        if not message.mentions: return
        t=message.mentions[0]
        data=slimed_users.get(str(t.id))
        if not data: return
        roles=[message.guild.get_role(r) for r in data["roles"] if message.guild.get_role(r)]
        if roles: await t.add_roles(*roles)
        role=discord.utils.get(message.guild.roles,name="SLIMED")
        if role: await t.remove_roles(role)
        await t.edit(nick=data["nickname"])
        del slimed_users[str(t.id)]
        save_json(slimed_users,slime_file)
        await message.channel.send("restored")
        return

# MOD COMMANDS
    if msg.startswith("yen kick"):
        if not message.author.guild_permissions.kick_members: return
        t=message.mentions[0]
        if not can_moderate(message.author,t,message.guild): return
        await t.kick()
        await message.channel.send("kicked"); return

    if msg.startswith("yen ban"):
        if not message.author.guild_permissions.ban_members: return
        t=message.mentions[0]
        if not can_moderate(message.author,t,message.guild): return
        await t.ban()
        await message.channel.send("banned"); return

    if msg.startswith("yen timeout"):
        if not message.author.guild_permissions.moderate_members: return
        t=message.mentions[0]
        mins=int(msg.split()[3])
        await t.timeout(timedelta(minutes=mins))
        await message.channel.send("timed out"); return

    if msg.startswith("yen untimeout"):
        t=message.mentions[0]
        await t.timeout(None)
        await message.channel.send("untimeout"); return

    if msg.startswith("yen purge"):
        if not message.author.guild_permissions.manage_messages: return
        n=int(msg.split()[2])
        await message.channel.purge(limit=n+1); return

    if msg.startswith("yen slowmode"):
        if not message.author.guild_permissions.manage_channels: return
        s=int(msg.split()[2])
        await message.channel.edit(slowmode_delay=s)
        await message.channel.send("slowmode set"); return

    if msg.startswith("yen nick"):
        if not message.author.guild_permissions.manage_nicknames: return
        t=message.mentions[0]
        name=message.content.split(" ",3)[3]
        await t.edit(nick=name)
        await message.channel.send("nick changed"); return

    if msg.startswith("yen warn"):
        t=message.mentions[0]
        warns.setdefault(str(t.id),[]).append("warn")
        save_json(warns,warn_file)
        await message.channel.send("warned"); return

# TRIGGER
    if not (msg.startswith("yen") or msg.startswith("hey yen") or random.randint(1,50)==1):
        return

# COOLDOWN
    uid=str(message.author.id)
    if uid in user_cooldowns and now-user_cooldowns[uid]<COOLDOWN_TIME:
        return
    user_cooldowns[uid]=now

# AI
    clean=message.content.replace("yen","",1).strip()
    reply=ask_ai(clean,uid)

    await asyncio.sleep(random.uniform(0.4,1.2))

    async for m in message.channel.history(limit=5):
        if m.author==bot.user and m.reference and m.reference.message_id==message.id:
            return

    await message.reply(reply)

bot.run(TOKEN)