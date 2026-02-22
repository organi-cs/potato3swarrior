import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
import random
import os
import urllib.request
import html
import urllib.parse
import asyncio
import glob
import aiohttp
from datetime import datetime, time, timedelta

from flask import Flask
from threading import Thread

app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is alive and running!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ============================================================
# CONFIG
# ============================================================
TOKEN = os.getenv("DISCORD_TOKEN", "REPLACE_WITH_YOUR_TOKEN_IN_KOYEB")  # <-- PUT YOUR TOKEN HERE
DAILY_CHANNEL_ID = None  # Set this to your channel ID for daily posts
MUSIC_FOLDER = os.getenv("MUSIC_FOLDER", "./music")  # Put your music files here

# ============================================================
# BOT SETUP
# ============================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ============================================================
# DATA STORAGE (JSON file)
# ============================================================
DATA_FILE = "bot_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"quotes": [], "bets": [], "vibes": {}, "trivia_scores": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ============================================================
# WOULD YOU RATHER
# ============================================================
WYR_PROMPTS = [
    ("Have unlimited money", "Have unlimited time"),
    ("Be able to fly", "Be able to read minds"),
    ("Never use social media again", "Never watch movies again"),
    ("Always be 10 minutes late", "Always be 20 minutes early"),
    ("Live without music", "Live without TV"),
    ("Have free WiFi everywhere", "Have free food everywhere"),
    ("Be famous but hated", "Be unknown but loved"),
    ("Fight 100 duck-sized horses", "Fight 1 horse-sized duck"),
    ("Know how you die", "Know when you die"),
    ("Live in the past", "Live in the future"),
    ("Only eat pizza forever", "Never eat pizza again"),
    ("Have no phone", "Have no friends"),
    ("Be the funniest person in the room", "Be the smartest"),
    ("Speak every language", "Play every instrument"),
    ("Always be cold", "Always be hot"),
    ("Lose your keys every day", "Lose your phone every day"),
    ("Have a rewind button for life", "Have a pause button for life"),
    ("Give up breakfast", "Give up dinner"),
    ("Be a famous athlete", "Be a famous musician"),
    ("Have super speed", "Have super strength"),
]

# ============================================================
# TRIVIA — powered by Open Trivia Database (opentdb.com)
# ============================================================
def fetch_trivia(category=None, difficulty=None):
    """Fetch a trivia question from the API. Returns None on failure."""
    url = "https://opentdb.com/api.php?amount=1&type=multiple"
    if category:
        url += f"&category={category}"
    if difficulty:
        url += f"&difficulty={difficulty}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "HomieBot/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        if data["response_code"] != 0:
            return None
        q = data["results"][0]
        return {
            "q": html.unescape(q["question"]),
            "a": html.unescape(q["correct_answer"]),
            "options": [html.unescape(a) for a in q["incorrect_answers"]] + [html.unescape(q["correct_answer"])],
            "category": html.unescape(q["category"]),
            "difficulty": q["difficulty"],
        }
    except Exception:
        return None

# Fallback questions in case API is down
FALLBACK_TRIVIA = [
    {"q": "What planet is known as the Red Planet?", "a": "Mars", "options": ["Venus", "Mars", "Jupiter", "Saturn"], "category": "Science", "difficulty": "easy"},
    {"q": "What is the capital of Australia?", "a": "Canberra", "options": ["Sydney", "Melbourne", "Canberra", "Brisbane"], "category": "Geography", "difficulty": "medium"},
    {"q": "Who painted the Mona Lisa?", "a": "Leonardo da Vinci", "options": ["Michelangelo", "Leonardo da Vinci", "Raphael", "Donatello"], "category": "Art", "difficulty": "easy"},
]

# Category IDs from opentdb.com
TRIVIA_CATEGORIES = {
    "general": 9,
    "science": 17,
    "history": 23,
    "geography": 22,
    "sports": 21,
    "music": 12,
    "film": 11,
    "games": 15,
    "anime": 31,
    "computers": 18,
}

# ============================================================
# DAILY QUESTIONS
# ============================================================
DAILY_QUESTIONS = [
    "What's the best meal you've had this week?",
    "If you could swap lives with anyone for a day, who would it be?",
    "What's a skill you wish you had?",
    "What's the last thing that made you laugh out loud?",
    "If you won the lottery tomorrow, what's the first thing you'd buy?",
    "What's your hot take that would get you cancelled?",
    "What's the most overrated thing everyone loves?",
    "If you could only listen to one song for the rest of your life, what would it be?",
    "What's the dumbest thing you believed as a kid?",
    "What would your reality TV show be called?",
    "What's something you're weirdly good at?",
    "If you had to eat one cuisine forever, what would it be?",
    "What's the worst fashion trend you participated in?",
    "What's your comfort movie?",
    "If your life had a theme song, what would it be?",
    "What's the most useless talent you have?",
    "What's something everyone should try at least once?",
    "Would you rather know all the world's secrets or be the world's best at one thing?",
    "What's the best advice you've ever received?",
    "If you could have dinner with any person, dead or alive, who?",
]

# ============================================================
# ROASTS (lighthearted)
# ============================================================
ROASTS = [
    "{user} is the type of person to Google 'Google'.",
    "{user} brings a spoon to the Super Bowl.",
    "{user}'s WiFi password is probably 'password123'.",
    "{user} still counts on their fingers. Respect.",
    "If {user} were a spice, they'd be flour.",
    "{user} is the human equivalent of a participation trophy.",
    "{user} looks like they'd clap when the plane lands.",
    "I'd agree with {user}, but then we'd both be wrong.",
    "{user} is proof that even evolution takes breaks.",
    "{user} types with their index fingers only.",
    "{user}'s search history is just 'how to be cool'.",
    "{user} is the kind of person who waves back at someone who wasn't waving at them.",
    "If {user} were a candle, they'd be unscented.",
    "{user} puts water in cereal.",
    "{user} is the reason shampoo has instructions.",
]

# ============================================================
# EVENTS & SETUP COMMANDS
# ============================================================
@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online!")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} global slash commands.")
        
        # Force sync to all guilds the bot is currently in (overrides the 1-hour wait)
        for guild in bot.guilds:
            try:
                bot.tree.copy_global_to(guild=guild)
                await bot.tree.sync(guild=guild)
                print(f"✅ Force-synced commands to {guild.name}")
            except Exception as e:
                print(f"⚠️ Could not force-sync to {guild.name}: {e}")
                
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

    # Start daily tasks
    if not daily_question_task.is_running():
        daily_question_task.start()

@bot.command(name="sync", help="Force sync new slash commands instantly to this server")
@commands.has_permissions(administrator=True)
async def sync(ctx):
    await ctx.send("Syncing slash commands to this server... ⏳")
    bot.tree.copy_global_to(guild=ctx.guild)
    synced = await bot.tree.sync(guild=ctx.guild)
    await ctx.send(f"✅ Successfully synced **{len(synced)}** slash commands to this server! They should appear immediately.")

@bot.command(name="desync", help="Remove server-specific slash commands to fix duplicates")
@commands.has_permissions(administrator=True)
async def desync(ctx):
    await ctx.send("Clearing server-specific commands... ⏳")
    bot.tree.clear_commands(guild=ctx.guild)
    await bot.tree.sync(guild=ctx.guild)
    await ctx.send("✅ Cleared server-specific commands! You should only see the global commands now (if they still appear duplicated, just restart your Discord app).")


# ============================================================
# /wouldyourather
# ============================================================
@bot.tree.command(name="wouldyourather", description="Would you rather... vote with reactions!")
async def would_you_rather(interaction: discord.Interaction):
    option_a, option_b = random.choice(WYR_PROMPTS)
    embed = discord.Embed(
        title="⚡ Would You Rather?",
        description=f"🅰️ {option_a}\n\n🅱️ {option_b}",
        color=discord.Color.purple()
    )
    embed.set_footer(text="React to vote!")
    await interaction.response.send_message(embed=embed)
    msg = await interaction.original_response()
    await msg.add_reaction("🅰️")
    await msg.add_reaction("🅱️")

# ============================================================
# /trivia
# ============================================================
class TriviaView(discord.ui.View):
    def __init__(self, question_data, user_id):
        super().__init__(timeout=30)
        self.correct = question_data["a"]
        self.user_id = user_id
        self.answered = set()

        random.shuffle(question_data["options"])
        for i, option in enumerate(question_data["options"]):
            button = discord.ui.Button(
                label=option,
                style=discord.ButtonStyle.primary,
                custom_id=f"trivia_{i}"
            )
            button.callback = self.make_callback(option)
            self.add_item(button)

    def make_callback(self, option):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id in self.answered:
                await interaction.response.send_message("You already answered!", ephemeral=True)
                return

            self.answered.add(interaction.user.id)
            data = load_data()
            user_name = interaction.user.display_name
            scores = data.get("trivia_scores", {})

            if option == self.correct:
                scores[user_name] = scores.get(user_name, 0) + 1
                data["trivia_scores"] = scores
                save_data(data)
                await interaction.response.send_message(
                    f"✅ **{user_name}** got it right! (+1 point, total: {scores[user_name]})",
                )
            else:
                await interaction.response.send_message(
                    f"❌ **{user_name}** wrong! The answer was **{self.correct}**",
                )
        return callback

@bot.tree.command(name="trivia", description="Test your knowledge! Thousands of questions from the internet.")
@app_commands.describe(
    category="Pick a category (optional)",
    difficulty="Pick difficulty (optional)"
)
@app_commands.choices(
    category=[
        app_commands.Choice(name="General Knowledge", value="general"),
        app_commands.Choice(name="Science", value="science"),
        app_commands.Choice(name="History", value="history"),
        app_commands.Choice(name="Geography", value="geography"),
        app_commands.Choice(name="Sports", value="sports"),
        app_commands.Choice(name="Music", value="music"),
        app_commands.Choice(name="Film", value="film"),
        app_commands.Choice(name="Video Games", value="games"),
        app_commands.Choice(name="Anime & Manga", value="anime"),
        app_commands.Choice(name="Computers", value="computers"),
    ],
    difficulty=[
        app_commands.Choice(name="Easy", value="easy"),
        app_commands.Choice(name="Medium", value="medium"),
        app_commands.Choice(name="Hard", value="hard"),
    ]
)
async def trivia(interaction: discord.Interaction, category: str = None, difficulty: str = None):
    cat_id = TRIVIA_CATEGORIES.get(category) if category else None
    q = fetch_trivia(category=cat_id, difficulty=difficulty)

    if q is None:
        q = random.choice(FALLBACK_TRIVIA)

    diff_emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(q["difficulty"], "⚪")
    embed = discord.Embed(
        title="🧠 Trivia Time!",
        description=q["q"],
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"{diff_emoji} {q['difficulty'].title()} • {q['category']}")
    view = TriviaView(q.copy(), interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="leaderboard", description="See trivia scores")
async def leaderboard(interaction: discord.Interaction):
    data = load_data()
    scores = data.get("trivia_scores", {})
    if not scores:
        await interaction.response.send_message("No scores yet! Play `/trivia` first.")
        return

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, (name, score) in enumerate(sorted_scores[:10]):
        medal = medals[i] if i < 3 else f"#{i+1}"
        lines.append(f"{medal} **{name}** — {score} points")

    embed = discord.Embed(
        title="🏆 Trivia Leaderboard",
        description="\n".join(lines),
        color=discord.Color.gold()
    )
    await interaction.response.send_message(embed=embed)

# ============================================================
# /roast
# ============================================================
@bot.tree.command(name="roast", description="Roast someone (or get roasted randomly)")
@app_commands.describe(target="Who to roast (leave empty for random)")
async def roast(interaction: discord.Interaction, target: discord.Member = None):
    if target is None:
        members = [m for m in interaction.guild.members if not m.bot]
        target = random.choice(members)

    roast_text = random.choice(ROASTS).format(user=target.display_name)
    embed = discord.Embed(
        title="🔥 Roast Alert",
        description=roast_text,
        color=discord.Color.red()
    )
    await interaction.response.send_message(embed=embed)

# ============================================================
# /quote
# ============================================================
@bot.tree.command(name="quote", description="Save a funny quote")
@app_commands.describe(person="Who said it", text="What they said")
async def quote_save(interaction: discord.Interaction, person: str, text: str):
    data = load_data()
    data["quotes"].append({
        "person": person,
        "text": text,
        "added_by": interaction.user.display_name,
        "date": datetime.now().strftime("%Y-%m-%d")
    })
    save_data(data)
    embed = discord.Embed(
        title="💬 Quote Saved!",
        description=f'"{text}"\n— **{person}**',
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Added by {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="randomquote", description="Get a random saved quote")
async def quote_random(interaction: discord.Interaction):
    data = load_data()
    if not data["quotes"]:
        await interaction.response.send_message("No quotes saved yet! Use `/quote` to add one.")
        return

    q = random.choice(data["quotes"])
    embed = discord.Embed(
        title="💬 Random Quote",
        description=f'"{q["text"]}"\n— **{q["person"]}**',
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Added by {q['added_by']} on {q['date']}")
    await interaction.response.send_message(embed=embed)

# ============================================================
# /poll
# ============================================================
@bot.tree.command(name="poll", description="Create a quick poll")
@app_commands.describe(
    question="Your question",
    option1="Option 1",
    option2="Option 2",
    option3="Option 3 (optional)",
    option4="Option 4 (optional)"
)
async def poll(interaction: discord.Interaction, question: str, option1: str, option2: str, option3: str = None, option4: str = None):
    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
    options = [option1, option2]
    if option3: options.append(option3)
    if option4: options.append(option4)

    desc = "\n".join([f"{emojis[i]} {opt}" for i, opt in enumerate(options)])
    embed = discord.Embed(
        title=f"📊 {question}",
        description=desc,
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Poll by {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)
    msg = await interaction.original_response()
    for i in range(len(options)):
        await msg.add_reaction(emojis[i])

# ============================================================
# /vibecheck
# ============================================================
class VibeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        vibes = [("😄", "Great"), ("🙂", "Good"), ("😐", "Meh"), ("😔", "Bad"), ("💀", "Dead")]
        for emoji, label in vibes:
            button = discord.ui.Button(label=f"{emoji} {label}", style=discord.ButtonStyle.secondary)
            button.callback = self.make_callback(emoji, label)
            self.add_item(button)

    def make_callback(self, emoji, label):
        async def callback(interaction: discord.Interaction):
            data = load_data()
            today = datetime.now().strftime("%Y-%m-%d")
            if "vibes" not in data:
                data["vibes"] = {}
            if today not in data["vibes"]:
                data["vibes"][today] = {}
            data["vibes"][today][interaction.user.display_name] = f"{emoji} {label}"
            save_data(data)
            await interaction.response.send_message(
                f"{emoji} **{interaction.user.display_name}** is feeling **{label}** today!",
            )
        return callback

@bot.tree.command(name="vibecheck", description="How are you feeling today?")
async def vibecheck(interaction: discord.Interaction):
    embed = discord.Embed(
        title="✨ Vibe Check",
        description="How are you feeling today?",
        color=discord.Color.teal()
    )
    await interaction.response.send_message(embed=embed, view=VibeView())

# ============================================================
# /bet
# ============================================================
@bot.tree.command(name="bet", description="Make a bet with someone")
@app_commands.describe(target="Who you're betting against", bet="What's the bet?")
async def bet(interaction: discord.Interaction, target: discord.Member, bet: str):
    data = load_data()
    bet_data = {
        "id": len(data["bets"]) + 1,
        "challenger": interaction.user.display_name,
        "target": target.display_name,
        "bet": bet,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "status": "active"
    }
    data["bets"].append(bet_data)
    save_data(data)

    embed = discord.Embed(
        title="🎲 New Bet!",
        description=f"**{interaction.user.display_name}** vs **{target.display_name}**\n\n📝 {bet}",
        color=discord.Color.orange()
    )
    embed.set_footer(text=f"Bet #{bet_data['id']} • Use /bets to see all active bets")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="bets", description="See all active bets")
async def bets_list(interaction: discord.Interaction):
    data = load_data()
    active = [b for b in data["bets"] if b["status"] == "active"]
    if not active:
        await interaction.response.send_message("No active bets! Use `/bet` to start one.")
        return

    lines = []
    for b in active:
        lines.append(f"**#{b['id']}** {b['challenger']} vs {b['target']}: {b['bet']}")

    embed = discord.Embed(
        title="🎲 Active Bets",
        description="\n".join(lines),
        color=discord.Color.orange()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="settle", description="Settle a bet")
@app_commands.describe(bet_id="Bet number", winner="Who won?")
async def settle(interaction: discord.Interaction, bet_id: int, winner: discord.Member):
    data = load_data()
    for b in data["bets"]:
        if b["id"] == bet_id and b["status"] == "active":
            b["status"] = "settled"
            b["winner"] = winner.display_name
            save_data(data)
            embed = discord.Embed(
                title="✅ Bet Settled!",
                description=f"**#{bet_id}**: {b['bet']}\n\n🏆 Winner: **{winner.display_name}**",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
            return

    await interaction.response.send_message(f"Couldn't find active bet #{bet_id}.")

# ============================================================
# /dailyquestion
# ============================================================
@bot.tree.command(name="dailyquestion", description="Get a random conversation starter")
async def daily_question(interaction: discord.Interaction):
    question = random.choice(DAILY_QUESTIONS)
    embed = discord.Embed(
        title="💭 Daily Question",
        description=question,
        color=discord.Color.magenta()
    )
    await interaction.response.send_message(embed=embed)

# ============================================================
# FUN COMMANDS
# ============================================================
@bot.tree.command(name="imagine", description="Generate an AI image based on your prompt")
@app_commands.describe(prompt="What do you want to see?")
async def imagine(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    
    safe_prompt = urllib.parse.quote(prompt)
    seed = random.randint(1, 1000000)
    image_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?seed={seed}&nologo=True"
    
    embed = discord.Embed(
        title=f"🎨 {prompt}",
        color=discord.Color.purple()
    )
    embed.set_image(url=image_url)
    embed.set_footer(text=f"Requested by {interaction.user.display_name} • Powered by Pollinations.ai")
    
    await interaction.followup.send(embed=embed)

RESPONSES_8BALL = [
    "It is certain.", "It is decidedly so.", "Without a doubt.", "Yes definitely.", "You may rely on it.",
    "As I see it, yes.", "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
    "Reply hazy, try again.", "Ask again later.", "Better not tell you now.", "Cannot predict now.", "Concentrate and ask again.",
    "Don't count on it.", "My reply is no.", "My sources say no.", "Outlook not so good.", "Very doubtful."
]

@bot.tree.command(name="8ball", description="Ask the magic 8-ball a question")
@app_commands.describe(question="Your yes/no question")
async def magic_8ball(interaction: discord.Interaction, question: str):
    answer = random.choice(RESPONSES_8BALL)
    embed = discord.Embed(
        title="🎱 Magic 8-Ball",
        description=f"**Q:** {question}\n**A:** {answer}",
        color=discord.Color.dark_purple()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="coinflip", description="Flip a coin")
async def coinflip(interaction: discord.Interaction):
    result = random.choice(["Heads", "Tails"])
    embed = discord.Embed(
        title="🪙 Coin Toss",
        description=f"It landed on **{result}**!",
        color=discord.Color.gold()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="roll", description="Roll a dice")
@app_commands.describe(sides="Number of sides (default is 6)")
async def roll(interaction: discord.Interaction, sides: int = 6):
    if sides < 2:
        await interaction.response.send_message("A dice needs at least 2 sides!", ephemeral=True)
        return
    
    result = random.randint(1, sides)
    embed = discord.Embed(
        title="🎲 Dice Roll",
        description=f"You rolled a **{result}** (out of {sides})",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ship", description="Check the love compatibility between two people")
@app_commands.describe(user1="First person", user2="Second person")
async def ship(interaction: discord.Interaction, user1: discord.Member, user2: discord.Member):
    percentage = random.randint(0, 100)
    
    if percentage == 100:
        msg = "True love! 💍"
        color = discord.Color.gold()
    elif percentage >= 75:
        msg = "Looking good! ❤️"
        color = discord.Color.red()
    elif percentage >= 50:
        msg = "There is potential. 💕"
        color = discord.Color.magenta()
    elif percentage >= 25:
        msg = "Might want to just stay friends. 😬"
        color = discord.Color.orange()
    else:
        msg = "Absolutely not. 💀"
        color = discord.Color.dark_grey()
        
    bar_length = 10
    filled = int((percentage / 100) * bar_length)
    empty = bar_length - filled
    bar = "█" * filled + "░" * empty
        
    embed = discord.Embed(
        title="💘 Matchmaker",
        description=f"**{user1.display_name}** & **{user2.display_name}**\n\nCompatibility: **{percentage}%**\n`{bar}`\n{msg}",
        color=color
    )
    await interaction.response.send_message(embed=embed)

SLAP_ITEMS = [
    "a large trout 🐟", "a rubber chicken 🐔", "a wet noodle 🍜", "a heavy book 📚",
    "a frying pan 🍳", "a moldy baguette 🥖", "a keyboard ⌨️", "a surprisingly soft pillow 🛏️"
]

@bot.tree.command(name="slap", description="Playfully slap someone")
@app_commands.describe(target="Who gets slapped?")
async def slap(interaction: discord.Interaction, target: discord.Member):
    item = random.choice(SLAP_ITEMS)
    embed = discord.Embed(
        title="💥 SLAP!",
        description=f"**{interaction.user.display_name}** slapped **{target.display_name}** around a bit with {item}",
        color=discord.Color.dark_red()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="mock", description="MoCk SoMe TeXt")
@app_commands.describe(text="The text to mock")
async def mock(interaction: discord.Interaction, text: str):
    mocked = "".join(c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(text))
    embed = discord.Embed(
        title="🤨",
        description=mocked,
        color=discord.Color.dark_theme()
    )
    embed.set_footer(text=f"Mocked by {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)

def fetch_joke():
    try:
        req = urllib.request.Request("https://official-joke-api.appspot.com/random_joke", headers={"User-Agent": "HomieBot/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return data["setup"], data["punchline"]
    except Exception:
        return "Why do programmers prefer dark mode?", "Because light attracts bugs."

@bot.tree.command(name="joke", description="Tell a random joke")
async def joke(interaction: discord.Interaction):
    setup, punchline = fetch_joke()
    embed = discord.Embed(
        title="🤡 Joke",
        description=f"{setup}\n\n||{punchline}||",
        color=discord.Color.gold()
    )
    await interaction.response.send_message(embed=embed)

CHINESE_POEMS = [
    {
        "title": "静夜思 (Quiet Night Thought)",
        "author": "李白 (Li Bai)",
        "lines": "床前明月光，\n疑是地上霜。\n举头望明月，\n低头思故乡。",
        "translation": "Before my bed, the moon is shining bright,\nI think that it is frost upon the ground.\nI raise my head and look at the bright moon,\nI lower my head and think of home."
    },
    {
        "title": "春晓 (Spring Dawn)",
        "author": "孟浩然 (Meng Haoran)",
        "lines": "春眠不觉晓，\n处处闻啼鸟。\n夜来风雨声，\n花落知多少。",
        "translation": "Spring slumbers, unaware of dawn's first light,\nBirds sing everywhere, a joyful sound.\nLast night, the wind and rain were blowing strong,\nHow many fallen flowers on the ground?"
    },
    {
        "title": "登鹳雀楼 (On the Stork Tower)",
        "author": "王之涣 (Wang Zhihuan)",
        "lines": "白日依山尽，\n黄河入海流。\n欲穷千里目，\n更上一层楼。",
        "translation": "The sun beyond the mountain glows;\nThe Yellow River seaward flows.\nYou can enjoy a grander sight,\nBy climbing to a greater height."
    }
]

@bot.tree.command(name="poem", description="Recite a classic Chinese poem")
async def poem(interaction: discord.Interaction):
    selected = random.choice(CHINESE_POEMS)
    embed = discord.Embed(
        title=f"📜 {selected['title']}",
        description=f"**{selected['author']}**\n\n{selected['lines']}\n\n*Translation:*\n*{selected['translation']}*",
        color=discord.Color.red()
    )
    await interaction.response.send_message(embed=embed)

# ============================================================
# PHASE 2: MINIGAMES & CHALLENGES
# ============================================================
@bot.tree.command(name="rps", description="Play Rock, Paper, Scissors against the bot")
@app_commands.describe(choice="Rock, Paper, or Scissors?")
@app_commands.choices(choice=[
    app_commands.Choice(name="Rock 🪨", value="rock"),
    app_commands.Choice(name="Paper 📄", value="paper"),
    app_commands.Choice(name="Scissors ✂️", value="scissors"),
])
async def rps(interaction: discord.Interaction, choice: str):
    bot_choice = random.choice(["rock", "paper", "scissors"])
    
    emoji_map = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
    
    if choice == bot_choice:
        result = "It's a tie! 🤝"
        color = discord.Color.gold()
    elif (choice == "rock" and bot_choice == "scissors") or \
         (choice == "paper" and bot_choice == "rock") or \
         (choice == "scissors" and bot_choice == "paper"):
        result = "You win! 🏆"
        color = discord.Color.green()
    else:
        result = "I win! 😈"
        color = discord.Color.red()
        
    embed = discord.Embed(
        title="Rock, Paper, Scissors",
        description=f"You chose: **{emoji_map[choice]} {choice.title()}**\nI chose: **{emoji_map[bot_choice]} {bot_choice.title()}**\n\n**{result}**",
        color=color
    )
    await interaction.response.send_message(embed=embed)

class TicTacToeButton(discord.ui.Button):
    def __init__(self, x: int, y: int):
        super().__init__(style=discord.ButtonStyle.secondary, label="\u200b", row=y)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        view: 'TicTacToeView' = self.view
        
        if interaction.user != view.current_player:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return
            
        if self.label != "\u200b":
            await interaction.response.send_message("That spot is already taken!", ephemeral=True)
            return

        self.label = view.current_mark
        self.style = discord.ButtonStyle.success if view.current_mark == "X" else discord.ButtonStyle.danger
        self.disabled = True
        
        view.board[self.y][self.x] = view.current_mark

        if view.check_winner():
            for child in view.children:
                child.disabled = True
            await interaction.response.edit_message(content=f"🎉 **{view.current_player.mention} won the game!**", view=view)
        elif view.is_tie():
            await interaction.response.edit_message(content="🤝 **It's a tie!**", view=view)
        else:
            view.current_player = view.player2 if view.current_player == view.player1 else view.player1
            view.current_mark = "O" if view.current_mark == "X" else "X"
            await interaction.response.edit_message(content=f"It's {view.current_player.mention}'s turn ({view.current_mark})", view=view)

class TicTacToeView(discord.ui.View):
    def __init__(self, player1: discord.Member, player2: discord.Member):
        super().__init__(timeout=300)
        self.player1 = player1
        self.player2 = player2
        self.current_player = player1
        self.current_mark = "X"
        self.board = [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0]
        ]
        
        for y in range(3):
            for x in range(3):
                self.add_item(TicTacToeButton(x, y))

    def check_winner(self):
        b = self.board
        for i in range(3):
            if b[i][0] == b[i][1] == b[i][2] != 0: return True
            if b[0][i] == b[1][i] == b[2][i] != 0: return True
        if b[0][0] == b[1][1] == b[2][2] != 0: return True
        if b[0][2] == b[1][1] == b[2][0] != 0: return True
        return False
        
    def is_tie(self):
        for row in self.board:
            if 0 in row: return False
        return True

@bot.tree.command(name="tictactoe", description="Play Tic-Tac-Toe with a friend")
@app_commands.describe(opponent="Who do you want to play against?")
async def tictactoe(interaction: discord.Interaction, opponent: discord.Member):
    if opponent.bot:
        await interaction.response.send_message("You can't play against a bot!", ephemeral=True)
        return
    if opponent == interaction.user:
        await interaction.response.send_message("You can't play against yourself!", ephemeral=True)
        return
        
    view = TicTacToeView(interaction.user, opponent)
    await interaction.response.send_message(f"🎮 **Tic-Tac-Toe**\n{interaction.user.mention} (X) vs {opponent.mention} (O)\n\n{interaction.user.mention}'s turn!", view=view)

@bot.tree.command(name="russianroulette", description="Spin the chamber. 1/6 chance to get timed out!")
async def russianroulette(interaction: discord.Interaction):
    await interaction.response.defer()
    
    msg = await interaction.followup.send("🔫 Spinning the cylinder... *click clack*")
    await asyncio.sleep(2)
    await msg.edit(content="🔫 Pointing it at your head...")
    await asyncio.sleep(2)
    
    if random.randint(1, 6) == 1:
        try:
            await interaction.user.timeout(timedelta(seconds=60), reason="Lost Russian Roulette")
            await msg.edit(content=f"💥 **BANG!**\n{interaction.user.mention} took the bullet and was timed out for 60 seconds. R.I.P. 💀")
        except discord.Forbidden:
            await msg.edit(content=f"💥 **BANG!**\n{interaction.user.mention} took the bullet!... wait, what? They are immortal. (I don't have permission to time them out). 💀")
    else:
        await msg.edit(content=f"💨 *Click.* Nothing happened.\n{interaction.user.mention} survives... for now. 😅")

# ============================================================
# PHASE 2: PRANKS
# ============================================================
HACK_MESSAGES = [
    "Finding IP address... `192.168.0.42`",
    "Bypassing mainframe firewall...",
    "Extracting search history...",
    "Found search: 'how to look cool'",
    "Found search: 'download more ram free'",
    "Selling Discord token on the dark web...",
    "Stealing V-Bucks...",
]

@bot.tree.command(name="hack", description="Fake 'hack' someone for a joke")
@app_commands.describe(target="Who to hack")
async def hack(interaction: discord.Interaction, target: discord.Member):
    await interaction.response.defer()
    msg = await interaction.followup.send(f"💻 Initiating hack on **{target.display_name}**...")
    
    for hack_msg in HACK_MESSAGES:
        await asyncio.sleep(1.5)
        await msg.edit(content=f"💻 {hack_msg}")
        
    await asyncio.sleep(2)
    embed = discord.Embed(
        title="✅ HACK COMPLETE",
        description=f"Successfully ruined {target.mention}'s digital life. (jk, this is a prank command)",
        color=discord.Color.dark_green()
    )
    await msg.edit(content=None, embed=embed)

@bot.tree.command(name="impersonate", description="Make the bot say something as another user in this channel")
@app_commands.describe(target="Who to impersonate", message="What they should say")
async def impersonate(interaction: discord.Interaction, target: discord.Member, message: str):
    if not interaction.channel.permissions_for(interaction.guild.me).manage_webhooks:
        await interaction.response.send_message("❌ I need 'Manage Webhooks' permission in this channel to do this!", ephemeral=True)
        return
        
    await interaction.response.defer(ephemeral=True)
    
    webhook = await interaction.channel.create_webhook(name=target.display_name)
    try:
        await webhook.send(
            content=message,
            username=target.display_name,
            avatar_url=target.display_avatar.url if target.display_avatar else target.default_avatar.url
        )
        await interaction.followup.send("✅ Prank executed successfully!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Failed: {e}", ephemeral=True)
    finally:
        await webhook.delete()

# ============================================================
# PHASE 2: AI TEXT UPGRADES
# ============================================================
async def fetch_pollinations_text(prompt: str) -> str:
    safe_prompt = urllib.parse.quote(prompt)
    url = f"https://text.pollinations.ai/prompt/{safe_prompt}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.text()
    except Exception:
        pass
    return "I couldn't contact my brain cells right now. Try again later."

@bot.tree.command(name="roast_ai", description="Get a brutal, AI-generated roast for someone")
@app_commands.describe(target="Who to roast")
async def roast_ai(interaction: discord.Interaction, target: discord.Member):
    await interaction.response.defer()
    prompt = f"Write a funny, creative, and slightly brutal 2-sentence roast for a Discord user named {target.display_name}. Do not use bad language."
    
    roast_text = await fetch_pollinations_text(prompt)
    
    embed = discord.Embed(
        title="🔥 AI Roast",
        description=f"{target.mention}, {roast_text}",
        color=discord.Color.dark_orange()
    )
    embed.set_footer(text=f"Requested by {interaction.user.display_name} • Powered by Pollinations.ai")
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="story", description="Contribute to the server's ongoing AI story")
@app_commands.describe(action="What to do", text="The sentence to add to the story (only for 'add')")
@app_commands.choices(action=[
    app_commands.Choice(name="Add a sentence", value="add"),
    app_commands.Choice(name="Read story", value="read"),
    app_commands.Choice(name="Clear story", value="clear"),
])
async def story(interaction: discord.Interaction, action: str, text: str = None):
    # Initialize story memory
    if not hasattr(bot, 'server_stories'):
        bot.server_stories = {}
        
    guild_id = interaction.guild.id
    if guild_id not in bot.server_stories:
        bot.server_stories[guild_id] = []
        
    if action == "add":
        if not text:
            await interaction.response.send_message("❌ You must provide `text` to add to the story!", ephemeral=True)
            return
            
        bot.server_stories[guild_id].append(f"**{interaction.user.display_name}:** {text}")
        await interaction.response.send_message(f"✅ Sentence added to the story! Use `/story read` to see the whole chaotic mess.")
        
    elif action == "read":
        story_lines = bot.server_stories[guild_id]
        if not story_lines:
            await interaction.response.send_message("📖 The story is completely empty. Add to it with `/story add`!")
            return
            
        full_story = "\n".join(story_lines)
        embed = discord.Embed(
            title="📖 The Neverending Story",
            description=full_story,
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed)
        
    elif action == "clear":
        bot.server_stories[guild_id] = []
        await interaction.response.send_message("🧹 The story has been wiped clean. Time to start fresh!")

# ============================================================
# MUSIC / VOICE CHANNEL
# ============================================================
@bot.tree.command(name="join", description="Bot joins your voice channel")
async def join(interaction: discord.Interaction):
    if not interaction.user.voice:
        await interaction.response.send_message("❌ You need to be in a voice channel first!")
        return

    channel = interaction.user.voice.channel
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.move_to(channel)
    else:
        await channel.connect()
    await interaction.response.send_message(f"🔊 Joined **{channel.name}**!")

@bot.tree.command(name="leave", description="Bot leaves voice channel")
async def leave(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("👋 Left the voice channel!")
    else:
        await interaction.response.send_message("❌ I'm not in a voice channel.")

def get_all_songs():
    """Find all music files in the music folder."""
    if not os.path.exists(MUSIC_FOLDER):
        os.makedirs(MUSIC_FOLDER)
        return []
    extensions = ["*.mp3", "*.wav", "*.ogg", "*.m4a", "*.flac"]
    all_songs = []
    for ext in extensions:
        all_songs.extend(glob.glob(os.path.join(MUSIC_FOLDER, ext)))
    return all_songs

@bot.tree.command(name="play", description="Play a song from the music folder")
@app_commands.describe(song="Song name (or part of it) — leave empty for random")
async def play(interaction: discord.Interaction, song: str = None):
    if not interaction.user.voice:
        await interaction.response.send_message("❌ Join a voice channel first!")
        return

    vc = interaction.guild.voice_client
    if not vc:
        vc = await interaction.user.voice.channel.connect()

    all_songs = get_all_songs()
    if not all_songs:
        await interaction.response.send_message(
            f"📁 No music files found! Put .mp3/.wav/.ogg files in the `{MUSIC_FOLDER}` folder next to bot.py."
        )
        return

    if song:
        matches = [s for s in all_songs if song.lower() in os.path.basename(s).lower()]
        if not matches:
            await interaction.response.send_message(f"❌ No song matching '{song}'. Use `/songs` to see available songs.")
            return
        chosen = matches[0]
    else:
        chosen = random.choice(all_songs)

    if vc.is_playing():
        vc.stop()

    song_name = os.path.splitext(os.path.basename(chosen))[0]
    source = discord.FFmpegPCMAudio(chosen)
    vc.play(source)

    embed = discord.Embed(
        title="🎵 Now Playing",
        description=f"**{song_name}**",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="stop", description="Stop the current song")
async def stop(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await interaction.response.send_message("⏹️ Stopped.")
    else:
        await interaction.response.send_message("❌ Nothing is playing.")

@bot.tree.command(name="pause", description="Pause the current song")
async def pause(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await interaction.response.send_message("⏸️ Paused.")
    elif vc and vc.is_paused():
        await interaction.response.send_message("Already paused. Use `/resume`.")
    else:
        await interaction.response.send_message("❌ Nothing is playing.")

@bot.tree.command(name="resume", description="Resume the paused song")
async def resume(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await interaction.response.send_message("▶️ Resumed!")
    else:
        await interaction.response.send_message("❌ Nothing is paused.")

@bot.tree.command(name="songs", description="List all available songs")
async def songs_list(interaction: discord.Interaction):
    all_songs = get_all_songs()
    if not all_songs:
        await interaction.response.send_message(f"📁 No songs found! Add .mp3/.wav/.ogg files to the `{MUSIC_FOLDER}` folder.")
        return

    song_names = [os.path.splitext(os.path.basename(s))[0] for s in sorted(all_songs)]
    lines = [f"**{i+1}.** {name}" for i, name in enumerate(song_names)]

    embed = discord.Embed(
        title=f"🎵 Available Songs ({len(song_names)})",
        description="\n".join(lines[:25]),
        color=discord.Color.green()
    )
    if len(song_names) > 25:
        embed.set_footer(text=f"...and {len(song_names) - 25} more")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="shuffle", description="Play all songs in random order")
async def shuffle_play(interaction: discord.Interaction):
    if not interaction.user.voice:
        await interaction.response.send_message("❌ Join a voice channel first!")
        return

    vc = interaction.guild.voice_client
    if not vc:
        vc = await interaction.user.voice.channel.connect()

    all_songs = get_all_songs()
    if not all_songs:
        await interaction.response.send_message("📁 No songs found!")
        return

    random.shuffle(all_songs)

    if not hasattr(bot, 'queue'):
        bot.queue = {}
    bot.queue[interaction.guild.id] = all_songs

    if vc.is_playing():
        vc.stop()

    song_name = os.path.splitext(os.path.basename(all_songs[0]))[0]

    def play_next(error):
        queue = bot.queue.get(interaction.guild.id, [])
        if queue:
            queue.pop(0)
        if queue and vc.is_connected():
            source = discord.FFmpegPCMAudio(queue[0])
            vc.play(source, after=play_next)

    source = discord.FFmpegPCMAudio(all_songs[0])
    vc.play(source, after=play_next)

    embed = discord.Embed(
        title="🔀 Shuffle Play",
        description=f"Playing **{len(all_songs)}** songs in random order\n\n🎵 Now: **{song_name}**",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="skip", description="Skip to the next song")
async def skip(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await interaction.response.send_message("⏭️ Skipped!")
    else:
        await interaction.response.send_message("❌ Nothing is playing.")

@bot.tree.command(name="nowplaying", description="Show what's currently playing")
async def nowplaying(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if not vc or not (vc.is_playing() or vc.is_paused()):
        await interaction.response.send_message("❌ Nothing is playing right now.")
        return

    queue = getattr(bot, 'queue', {}).get(interaction.guild.id, [])
    status = "⏸️ Paused" if vc.is_paused() else "▶️ Playing"

    if queue:
        song_name = os.path.splitext(os.path.basename(queue[0]))[0]
        remaining = len(queue) - 1
        embed = discord.Embed(
            title=f"🎵 {status}",
            description=f"**{song_name}**",
            color=discord.Color.green()
        )
        if remaining > 0:
            embed.set_footer(text=f"{remaining} songs remaining in queue")
    else:
        embed = discord.Embed(
            title=f"🎵 {status}",
            description="A song is playing",
            color=discord.Color.green()
        )
    await interaction.response.send_message(embed=embed)

# ============================================================
@bot.tree.command(name="timer", description="Set a timer or countdown")
@app_commands.describe(duration="Time in seconds (e.g., 60)", reason="What is the timer for? (Optional)")
async def timer(interaction: discord.Interaction, duration: int, reason: str = "Time's up!"):
    if duration <= 0:
        await interaction.response.send_message("❌ The timer must be at least 1 second!", ephemeral=True)
        return
    if duration > 3600:
        await interaction.response.send_message("❌ The maximum timer is 1 hour (3600 seconds)!", ephemeral=True)
        return
        
    minutes, seconds = divmod(duration, 60)
    time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"

    embed = discord.Embed(
        title="⏳ Timer Started",
        description=f"I will ping you in **{time_str}**.\nReason: *{reason}*",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed)
    
    await asyncio.sleep(duration)
    
    embed_done = discord.Embed(
        title="⏰ 叮咚! (Ding Dong!)",
        description=f"Your timer for **{time_str}** has finished!\nReason: *{reason}*",
        color=discord.Color.green()
    )
    await interaction.channel.send(f"{interaction.user.mention}", embed=embed_done)

# ============================================================
# /help
# ============================================================
@bot.tree.command(name="help", description="See all bot commands")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 HomieBot Commands",
        color=discord.Color.blurple()
    )
    cmds = [
        ("🎮 Games (Phase 1)", "`/wouldyourather` — Vote on dilemmas\n`/trivia` — Answer trivia questions\n`/leaderboard` — See trivia scores\n`/roll` — Roll a dice\n`/coinflip` — Flip a coin"),
        ("🎮 Minigames (Phase 2)", "`/rps` — Rock, Paper, Scissors against the bot\n`/tictactoe` — Play Tic-Tac-Toe\n`/russianroulette` — Spin the chamber (risky!)"),
        ("🔥 Fun & Pranks", "`/roast` — Standard roasts\n`/hack` — Fake hacking prank\n`/impersonate` — Make the bot talk as a friend\n`/slap` — Slap someone\n`/mock` — mOcK tExT\n`/joke` — Random jokes\n`/poem` — Chinese poem"),
        ("🤖 AI Powered", "`/imagine` — Generate AI images\n`/roast_ai` — AI-generated custom roasts\n`/story` — Group interactive story"),
        ("💬 Social & Utils", "`/timer` — Set a countdown\n`/dailyquestion` — Conversation starter\n`/vibecheck` — Share your mood\n`/8ball` — Magic 8-Ball\n`/ship` — Matchmaker\n`/quote` — Save quotes\n`/randomquote` — Get a random quote\n`/poll` — Create a poll"),
        ("🎲 Bets", "`/bet` — Start a bet\n`/bets` — See active bets\n`/settle` — Settle a bet"),
        ("🎵 Music", "`/join` — Join VC\n`/leave` — Leave VC\n`/play` — Play a song\n`/songs` — List songs\n`/shuffle` — Play all randomly\n`/skip` `/pause` `/resume` `/stop`\n`/nowplaying` — What's playing?"),
    ]
    for name, value in cmds:
        embed.add_field(name=name, value=value, inline=False)

    await interaction.response.send_message(embed=embed)

# ============================================================
# DAILY AUTO-POST (posts a question every day at 8AM UTC+7)
# ============================================================
@tasks.loop(time=time(hour=1, minute=0))  # 8AM Cambodia (UTC+7) = 1:00 UTC
async def daily_question_task():
    if DAILY_CHANNEL_ID is None:
        return

    channel = bot.fetch_channel(DAILY_CHANNEL_ID)
    if channel is None:
        return

    question = random.choice(DAILY_QUESTIONS)
    embed = discord.Embed(
        title="☀️ Good Morning! Daily Question",
        description=question,
        color=discord.Color.magenta()
    )
    await channel.send(embed=embed)

# ============================================================
# RUN
# ============================================================
if __name__ == "__main__":
    t = Thread(target=run_server)
    t.start()
    bot.run(TOKEN)