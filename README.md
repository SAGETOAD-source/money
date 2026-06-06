# ⚡ AUTO SHORTS BOT

Fully automated YouTube Shorts + Instagram Reels creation and posting system.  
No manual work required once set up.

---

## What it does (every day, automatically)

1. 🔍 Finds trending topics from Google Trends
2. 🧠 Writes a viral script using Claude AI
3. 🎬 Creates a 30–50 sec vertical MP4 (1080×1920)
4. 🎤 Adds AI voiceover (Microsoft Edge TTS — free)
5. 📤 Posts to YouTube Shorts **and** Instagram Reels
6. 📊 Logs everything to `logs/activity.json`

---

## Setup (do this once)

### Step 1 — Install Python dependencies

```bash
pip install -r requirements.txt
```

On Linux also install ffmpeg:
```bash
sudo apt install ffmpeg
```

On Windows: download from https://ffmpeg.org/download.html and add to PATH.

---

### Step 2 — Fill in `config.py`

Open `config.py` and fill in:

| Field | Where to get it |
|-------|----------------|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com |
| `YOUTUBE_CLIENT_SECRET_FILE` | See Step 3 below |
| `INSTAGRAM_USERNAME` / `PASSWORD` | Your Instagram account |

Also set your `NICHES`, `CHANNEL_NAME`, and `TRENDS_REGION`.

---

### Step 3 — YouTube one-time auth

1. Go to https://console.cloud.google.com/
2. Create a new project (e.g. "AutoShorts")
3. Go to **APIs & Services → Enable APIs**  
   → Enable **YouTube Data API v3**
4. Go to **APIs & Services → Credentials**  
   → Create **OAuth 2.0 Client ID** → Application type: **Desktop app**
5. Download the JSON file → rename it `client_secret.json`  
   → place it in this project folder
6. Run once:
   ```bash
   python setup_youtube_auth.py
   ```
   This opens a browser, you log in once, token is saved.  
   **Never need to do this again.**

---

### Step 4 — Instagram (no extra setup)

Just enter your username and password in `config.py`.  
The bot saves the session so it doesn't re-login every time.

> ⚠️ Use a **dedicated account** for the bot, not your personal one.  
> Instagram *may* ask for email/SMS verification on first login.

---

### Step 5 — Run the bot!

```bash
# Start in background (Linux/Mac)
nohup python main.py &

# Start on Windows
python main.py

# Post one video immediately AND start scheduler
python main.py --now
```

The bot runs 24/7 and posts at scheduled times (default: 3×/day).

---

## Run as a background service (Linux)

Create a systemd service so it auto-starts on reboot:

```bash
sudo nano /etc/systemd/system/autoshorts.service
```

```ini
[Unit]
Description=Auto Shorts Bot
After=network.target

[Service]
ExecStart=/usr/bin/python3 /path/to/auto_shorts/main.py
WorkingDirectory=/path/to/auto_shorts
Restart=always
User=your_username

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable autoshorts
sudo systemctl start autoshorts
sudo systemctl status autoshorts
```

---

## File Structure

```
auto_shorts/
├── main.py                  ← Start here
├── config.py                ← All settings
├── setup_youtube_auth.py    ← Run once for YouTube
├── requirements.txt
├── modules/
│   ├── trend_finder.py      ← Google Trends
│   ├── script_writer.py     ← Claude AI scripts
│   ├── video_maker.py       ← MP4 generation
│   └── uploader.py          ← YouTube + Instagram
├── output/                  ← Generated videos saved here
└── logs/
    ├── bot.log              ← Text log
    └── activity.json        ← JSON log (read by dashboard)
```

---

## Costs (monthly estimate)

| Service | Cost |
|---------|------|
| Anthropic API (~90 scripts/month) | ~$0.50 |
| Edge TTS (voiceover) | FREE |
| YouTube Data API | FREE (10k units/day) |
| instagrapi (Instagram) | FREE |
| **Total** | **~$0.50/month** |

---

## Monetisation path

1. **YouTube** → Apply for monetization at 1000 subs + 4000 watch hours
2. **Instagram** → Apply for Reels bonuses (varies by country)
3. **Both** → Brand deals once you hit 10k followers

Typical faceless short-form channels reach monetization in 3–6 months posting daily.

---

## Troubleshooting

**"pytrends rate limited"** → Bot automatically falls back to built-in topics. Normal.

**"Instagram login failed"** → Delete `instagram_session.json` and retry. May need 2FA.

**"YouTube quota exceeded"** → You hit 10k API units/day. Reduce `VIDEOS_PER_DAY` to 2.

**"ffmpeg not found"** → Install ffmpeg and add it to your system PATH.

**Video has no audio** → Check edge-tts is installed: `pip install edge-tts`
