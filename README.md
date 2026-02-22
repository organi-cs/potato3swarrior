# 🤖 Potato3sWarrior — Discord Bot for Your Friend Group

## Features
- `/wouldyourather` — Vote on dilemmas
- `/trivia` — Quiz with leaderboard
- `/roast` — Lighthearted roasts
- `/quote` + `/randomquote` — Save & recall funny friend quotes
- `/poll` — Quick polls with reactions
- `/vibecheck` — Daily mood check-in
- `/bet` + `/bets` + `/settle` — Track friendly bets
- `/dailyquestion` — Random conversation starters
- `/leaderboard` — Trivia scores
- `/help` — See all commands

## Setup

### 1. Install Python
Download Python 3.10+ from https://python.org

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Add your bot token
Open `bot.py` and replace `PASTE_YOUR_TOKEN_HERE` with your actual bot token:
```python
TOKEN = "your-actual-token-here"
```

**OR** (recommended) set it as an environment variable:
```bash
# Windows
set DISCORD_TOKEN=your-token-here

# Mac/Linux
export DISCORD_TOKEN=your-token-here
```

### 4. Run the bot
```bash
python bot.py
```

You should see:
```
✅ HomieBot is online!
✅ Synced 11 slash commands
```

### 5. (Optional) Auto daily question
To auto-post a daily question, find your channel ID:
1. Enable Developer Mode in Discord (Settings → Advanced → Developer Mode)
2. Right-click the channel → Copy Channel ID
3. Set `DAILY_CHANNEL_ID` in bot.py to that number

## Free Hosting Options
- **Railway.app** — free tier, easy deploy
- **Replit** — free, runs in browser
- **Oracle Cloud free tier** — always-free VM
- **Home PC** — just leave it running

## Adding More Content
You can easily add more questions, roasts, trivia, etc. by editing the lists at the top of `bot.py`.
