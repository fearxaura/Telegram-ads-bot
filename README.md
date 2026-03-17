# Personal Telegram Ads Bot

A personal Telegram bot that:
- Sends a promo message **only to groups you select** on a configurable interval
- Automatically replies to anyone who messages the bot while **you are marked as offline**
- Forwards every incoming private message to you (the owner) so you never miss anything

---

## Quick Start

### 1. Prerequisites

- A Linux/Ubuntu VPS (or any machine with Python 3.9+)
- A Telegram Bot token — obtain one from [@BotFather](https://t.me/BotFather)
- Your Telegram numeric user ID — get it from [@userinfobot](https://t.me/userinfobot)

### 2. Clone / copy the files

```bash
git clone https://github.com/fearxaura/Telegram-ads-bot.git
cd Telegram-ads-bot
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure

Edit `config.json` and fill in your details:

```json
{
  "bot_token": "YOUR_BOT_TOKEN_HERE",
  "owner_id": 123456789,
  "selected_groups": [],
  "promo_message": "👋 Hello! Check out our latest offers!",
  "away_message": "👋 Hi! The owner is currently offline. Leave your message and they will reply soon.",
  "owner_online": true,
  "send_interval_minutes": 60
}
```

| Field | Description |
|---|---|
| `bot_token` | Token from @BotFather |
| `owner_id` | Your numeric Telegram user ID |
| `selected_groups` | List of group chat IDs the bot will post to |
| `promo_message` | The message sent to all selected groups |
| `away_message` | Auto-reply sent to anyone who messages the bot while you are offline |
| `owner_online` | `true` = online (no auto-reply), `false` = offline (auto-reply active) |
| `send_interval_minutes` | How often (in minutes) the bot auto-sends the promo to all selected groups |

> **Tip:** You can also set `BOT_TOKEN` and `OWNER_ID` as environment variables instead of editing `config.json`.

### 5. Add the bot to your groups

In each Telegram group you want to send to, add the bot as a **member** (or admin if you need it to post).  
Then run the bot and use `/addgroup` with the group's numeric ID.

> To find a group ID: forward any message from the group to [@userinfobot](https://t.me/userinfobot) or use [@getidsbot](https://t.me/getidsbot).

### 6. Run the bot

```bash
python bot.py
```

---

## Bot Commands (owner only)

| Command | Description |
|---|---|
| `/start` | Show help |
| `/addgroup <group_id>` | Add a group to the send list |
| `/removegroup <group_id>` | Remove a group from the send list |
| `/listgroups` | Show all selected groups |
| `/setmessage <text>` | Set the promo message |
| `/setaway <text>` | Set the away auto-reply message |
| `/setinterval <minutes>` | Change the auto-send interval |
| `/send` | Send promo message to all selected groups right now |
| `/online` | Mark yourself as online — disables auto-reply |
| `/offline` | Mark yourself as offline — enables auto-reply |
| `/status` | Show current bot settings |

---

## Deploying on a VPS (step-by-step)

### Recommended VPS providers
- [DigitalOcean](https://www.digitalocean.com/) — $4/month Droplet
- [Hetzner](https://www.hetzner.com/) — €3.29/month (cheapest in Europe)
- [Vultr](https://www.vultr.com/) — $2.50/month
- [Linode / Akamai](https://www.linode.com/) — $5/month

Choose **Ubuntu 22.04 LTS** when creating the server.

---

### Step 1 — Create and connect to your VPS

```bash
ssh root@YOUR_VPS_IP
```

### Step 2 — Update the system

```bash
apt update && apt upgrade -y
```

### Step 3 — Install Python and pip

```bash
apt install -y python3 python3-pip git
```

### Step 4 — Clone the repo

```bash
git clone https://github.com/fearxaura/Telegram-ads-bot.git
cd Telegram-ads-bot
```

### Step 5 — Install Python dependencies

```bash
pip3 install -r requirements.txt
```

### Step 6 — Set up the config

```bash
nano config.json
```

Fill in your `bot_token` and `owner_id`, then save (`Ctrl+O`, `Enter`, `Ctrl+X`).

### Step 7 — Run with `screen` (keeps it alive after you disconnect)

```bash
apt install -y screen
screen -S tgbot
python3 bot.py
```

Detach from the screen session with **Ctrl+A, D**.  
To re-attach later:

```bash
screen -r tgbot
```

### Step 8 (optional) — Run as a systemd service (starts automatically on reboot)

Create the service file:

```bash
nano /etc/systemd/system/tgbot.service
```

Paste the following (adjust the path if needed):

```ini
[Unit]
Description=Personal Telegram Ads Bot
After=network.target

[Service]
WorkingDirectory=/root/Telegram-ads-bot
ExecStart=/usr/bin/python3 /root/Telegram-ads-bot/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
systemctl daemon-reload
systemctl enable tgbot
systemctl start tgbot
systemctl status tgbot
```

Check logs at any time:

```bash
journalctl -u tgbot -f
```

---

## File structure

```
Telegram-ads-bot/
├── bot.py            ← Main bot (new personalised version)
├── config.json       ← Your settings (keep private — not committed with secrets)
├── requirements.txt  ← Python dependencies
└── README.md         ← This file
```

---

## Security note

Never share your `bot_token` publicly.  
You can instead set it as an environment variable:

```bash
export BOT_TOKEN="your_token_here"
export OWNER_ID="your_numeric_id"
python3 bot.py
```