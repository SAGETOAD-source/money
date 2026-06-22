"""
pov_maker.py — Premium POV Reels Generator
Instagram Reels + YouTube Shorts
Cinematic aesthetic: nature/urban backgrounds + emotional text
"""

import os, sys, random, logging, math, textwrap, requests, time, schedule, json, asyncio
import numpy as np
import moviepy.editor as mp
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.LANCZOS


async def _tts_async(text: str, path: str, voice: str, rate: str):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(path)


def gen_pov_tts(text: str, path: str,
                voice: str = "en-US-ChristopherNeural",
                rate: str = "-15%"):
    asyncio.run(_tts_async(text, path, voice, rate))

sys.path.insert(0, os.path.dirname(__file__))
import config
from groq import Groq

if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.LANCZOS

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    handlers=[logging.StreamHandler(sys.stdout),
              logging.FileHandler("logs/pov_bot.log", encoding="utf-8")])
logger = logging.getLogger(__name__)

client = Groq(api_key=config.GROQ_API_KEY)
W, H, FPS = 1080, 1920, 30

# ── Visual queries ─────────────────────────────────────────────────────────────
VISUAL_QUERIES = {
    "nature":  ["rain window bokeh", "sunset golden field", "ocean waves slow",
                "forest misty light", "flower petals wind", "night sky stars milky",
                "river peaceful nature", "mountains fog sunrise"],
    "urban":   ["city lights rain night", "coffee shop cozy", "hands close up",
                "empty street night fog", "train window moving landscape",
                "rooftop sunset city", "candle flame dark", "neon lights rain"],
}

# ── POV topics ─────────────────────────────────────────────────────────────────
POV_TOPICS = {
    "love":        ["you loved someone who never chose you back",
                    "you realized you were the option, not the priority",
                    "you kept waiting for a text that never came",
                    "you fell for someone already taken",
                    "you said I'm fine but meant please ask me again",
                    "you loved someone you had to let go"],
    "heartbreak":  ["you're deleting their number for the 4th time",
                    "you hear their favorite song in public",
                    "you drove past the place you used to go together",
                    "you finally stopped checking if they posted",
                    "it's been months and a smell still reminds you of them",
                    "you realized healing isn't linear"],
    "loneliness":  ["everyone around you is laughing and you feel nothing",
                    "you smile all day and cry at 2am",
                    "you're in a crowded room and completely alone",
                    "you miss someone but don't know who",
                    "you have people around you but feel invisible"],
    "self-growth": ["you chose yourself for the first time",
                    "you stopped apologizing for existing",
                    "you let go of someone you still loved",
                    "you became someone your younger self needed",
                    "you realized your peace is worth more than their presence"],
    "friendship":  ["your best friend became a stranger slowly",
                    "you stopped reaching out first and learned who cares",
                    "you outgrew people you thought you'd have forever",
                    "you realized some people are seasonal"],
}

HINGLISH_LINES = [
    "kuch log sirf yaadein ban ke reh jaate hain.",
    "jo tera tha, woh kabhi gaya hi nahi.",
    "dil ko samjhao, par dil maanta kab hai.",
    "kuch dard kehne se nahi jaate.",
    "tum yaad aate ho, aur hum chup ho jaate hain.",
    "kuch rishte khatam nahi hote, bas khamosh ho jaate hain.",
    "teri aadat si ho gayi thi.",
    "jo baat kehni thi, woh reh gayi andar.",
]

# ── Accent colors per mood ─────────────────────────────────────────────────────
ACCENTS = {
    "love":        (255, 100, 150),
    "heartbreak":  (180,  80, 255),
    "loneliness":  (100, 150, 255),
    "self-growth": (100, 220, 150),
    "friendship":  (255, 180,  80),
}

_FC = {}
def gfont(size: int, bold: bool = False):
    k = (size, bold)
    if k in _FC: return _FC[k]
    paths = [
        "Montserrat-ExtraBold.ttf" if bold else "Montserrat-Regular.ttf",
        "C:/Windows/Fonts/Impact.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    f = ImageFont.load_default()
    for p in paths:
        if os.path.exists(p):
            try: f = ImageFont.truetype(p, size); break
            except: pass
    _FC[k] = f
    return f


def download_pexels_clip(query: str) -> str | None:
    key = config.PEXELS_API_KEY
    if not key or key.startswith("YOUR"):
        return None
    os.makedirs("assets/pov", exist_ok=True)
    try:
        r = requests.get("https://api.pexels.com/videos/search",
            headers={"Authorization": key},
            params={"query": query, "per_page": 10,
                    "orientation": "portrait", "size": "medium"},
            timeout=15)
        videos = r.json().get("videos", [])
        if not videos: return None
        video = random.choice(videos[:6])
        files = [f for f in video["video_files"] if f.get("width", 0) >= 720]
        if not files: files = video["video_files"]
        url = sorted(files, key=lambda x: x.get("width", 0))[-1]["link"]
        vid_id = video["id"]
        path = f"assets/pov/{vid_id}.mp4"
        if os.path.exists(path): return path
        resp = requests.get(url, stream=True, timeout=60)
        with open(path, "wb") as f:
            for chunk in resp.iter_content(65536):
                f.write(chunk)
        logger.info(f"✅ POV clip: {path}")
        return path
    except Exception as e:
        logger.warning(f"Pexels: {e}")
        return None


POV_SYSTEM = """You write emotional viral POV scripts for Instagram Reels and YouTube Shorts.
Your scripts make people stop scrolling because they feel personally seen.

RULES:
- Write EXACTLY 6 lines — no more, no less
- Each line max 10 words
- Line 1: POV hook — starts with "POV:" — makes them stop immediately
- Line 2-3: build the emotion slowly — make them feel it
- Line 4: THE LINE — the one they screenshot and send to someone
- Line 5: the twist or deeper truth
- Line 6: quiet, lingering closer — ends with feeling not words
- NO abrupt endings — the last line should feel like a breath, not a stop
- For Hinglish: mix Hindi and English naturally, like people actually text
- Output ONLY the 6 lines. No labels. No numbers. No explanation."""


def generate_pov_lines(topic: str, mood: str, language: str) -> list[str]:
    lang_note = (
        "Write in Hinglish (romanized Hindi + English mix). Natural, like WhatsApp texts."
        if language == "hinglish"
        else "Write in English. Raw, personal, emotionally intelligent."
    )
    prompt = f"""Topic: "POV: {topic}"
Mood: {mood}
{lang_note}

Write EXACTLY 6 lines. Complete emotional arc. Never end abruptly.
The last line should feel peaceful or heavy — never cut off."""

    try:
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": POV_SYSTEM},
                {"role": "user", "content": prompt}
            ],
            max_tokens=180, temperature=0.95)
        lines = [l.strip() for l in r.choices[0].message.content.strip().split("\n")
                 if l.strip()][:6]
        while len(lines) < 6:
            lines.append(random.choice(HINGLISH_LINES))
        return lines
    except Exception as e:
        logger.error(f"Groq: {e}")
        return [
            f"POV: {topic}",
            "you know this feeling better than anyone.",
            "some days it hits harder than others.",
            "and you sit with it, quietly.",
            "because some things can't be explained.",
            "only felt."
        ]


def ease_in_out(t: float) -> float:
    return t * t * (3 - 2 * t)


def render_pov_frame(lines: list[str], progress: float,
                     accent: tuple, bg_arr: np.ndarray | None) -> np.ndarray:
    """Render one frame of the POV video."""
    # Background
    if bg_arr is not None:
        img = Image.fromarray(bg_arr).convert("RGBA")
    else:
        # Fallback: dark gradient
        arr = np.zeros((H, W, 3), dtype=np.uint8)
        for y in range(H):
            v = int(10 + (y / H) * 25)
            arr[y, :] = [v, v, v + 15]
        img = Image.fromarray(arr).convert("RGBA")

    draw = ImageDraw.Draw(img, "RGBA")

    # Cinematic dark overlay — heavier at top and bottom
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay, "RGBA")
    for y in range(H):
        ratio = y / H
        # Vignette: dark edges, lighter center
        center_dist = abs(ratio - 0.5) * 2
        alpha = int(80 + center_dist * 120)
        od.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img, "RGBA")

    # Cinematic bars (top and bottom black bars)
    bar_h = 90
    draw.rectangle([(0, 0), (W, bar_h)], fill=(0, 0, 0, 220))
    draw.rectangle([(0, H - bar_h), (W, H)], fill=(0, 0, 0, 220))

    # Render each line with staggered fade-in
    n = len(lines)
    center_y = H // 2
    line_spacing = 130
    total_text_h = (n - 1) * line_spacing
    start_y = center_y - total_text_h // 2 - 40

    for i, line in enumerate(lines):
        # Each line fades in at different times
        threshold = i / (n + 1)
        local_p = max(0.0, min(1.0, (progress - threshold) * (n + 1) * 0.8))
        eased = ease_in_out(local_p)

        if eased < 0.01:
            continue

        alpha = int(eased * 255)
        # Slide up slightly as it appears
        y_offset = int((1 - eased) * 30)
        y = start_y + i * line_spacing + y_offset

        # Font size — line 1 (POV hook) bigger
        if i == 0:
            font = gfont(68, bold=True)
            color = accent
        elif i == 2:
            # The "save it" line — slightly larger, accent color
            font = gfont(58, bold=True)
            color = (255, 255, 255)
        else:
            font = gfont(52, bold=False)
            color = (210, 210, 210)

        # Word wrap
        bb = font.getbbox("A")
        cpl = max(5, (W - 100) // max(1, bb[2] - bb[0]))
        wrapped = textwrap.fill(line, width=cpl).split("\n")
        lh = (font.getbbox("Hg")[3] - font.getbbox("Hg")[1]) + 18

        for j, wline in enumerate(wrapped):
            lb = font.getbbox(wline)
            lw = lb[2] - lb[0]
            lx = (W - lw) // 2
            ly = y + j * lh

            # Glow for accent lines
            if i == 0 or i == 2:
                for ox, oy in [(-4,-4),(4,-4),(-4,4),(4,4)]:
                    draw.text((lx+ox, ly+oy), wline, font=font,
                             fill=(*accent, alpha // 4))

            # Strong outline
            for ox, oy in [(-3,-3),(3,-3),(-3,3),(3,3),(-4,0),(4,0),(0,-4),(0,4)]:
                draw.text((lx+ox, ly+oy), wline, font=font,
                         fill=(0, 0, 0, min(255, alpha)))
            draw.text((lx, ly), wline, font=font,
                     fill=(*color, alpha))

    # Accent line — appears at 70% progress
    if progress > 0.65:
        line_alpha = int(ease_in_out(min(1.0, (progress - 0.65) * 4)) * 200)
        lw = int(W * 0.35)
        lx = (W - lw) // 2
        # Gradient line
        for xi in range(lw):
            ratio = xi / lw
            fade = math.sin(ratio * math.pi)
            a = int(line_alpha * fade)
            draw.rectangle([(lx + xi, H - bar_h - 30),
                            (lx + xi + 1, H - bar_h - 26)],
                           fill=(*accent, a))

    return np.array(img.convert("RGB"))



SHAYARI_THEMES = [
    "judai aur yaad", "mohabbat ka dard", "rishton ka toota hua silsila",
    "akela pan ki raat", "jo baat keh na sake", "woh jo reh gaya andar",
    "intezaar ka dard", "khaamoshi ki awaaz", "aankhon ka samandar",
    "teri kami ka ehsaas", "dil ka bojh", "waqt ka zakhm"
]

SHAYARI_SYSTEM = """Tu Mirza Ghalib, Gulzar aur Rahat Indori ka combination hai.
Teri shayari sunke log ruk jaate hain. Screenshot lete hain. Aankhein bhar aati hain.

STYLE RULES — IN KO KABHI MAT TODO:
- Romanized Hindi — jaise log dil se bolte hain, WhatsApp pe likhte hain
- Har line POORI honi chahiye — adhoori line mat likho, dil tak pahunchni chahiye
- Har line mein ek complete feeling ho — na zyada chhoti, na zyada lambi
- Natural Urdu/Hindi words use kar — tanha, dard, yaad, mohabbat, raat, aansu, khamoshi, waqt
- Metaphors jo dil ko lagein — chaand, dariya, aankhein, raat, mitti, aawaz, khwab, saaya
- LINE 1: Hook — pehli line padh ke scroll rukna chahiye
- LINE 2: Dard gehra karo — LINE 1 se connected, feeling badhao
- LINE 3: THE SCREENSHOT LINE — sabse powerful line, jo log 3 baje rote hain padh ke
- LINE 4: Khamosh khatma — ek aisi line jo ghaav chhod jaaye, dil mein ghus jaaye

EXAMPLES OF GOOD SHAYARI:
"Tumse milke laga tha ke ab koi gham nahi,
par tumhara jaana hi sabse bada gham ban gaya.
Woh jo teri aankhon mein tha ujala kabhi,
ab wahi roshni mujhe andhere mein jalaati hai."

"Teri yaad aati hai toh neend bhaag jaati hai,
raat lambi ho jaati hai, aankhein bhaari ho jaati hain.
Jo baatein kehni thi, woh hothon pe reh gayi,
ab khamoshi hi teri awaaz ban gayi hai."

SIRF 4 lines. Koi number nahi. Koi label nahi. Bas pure dil se shayari.
Har line complete honi chahiye — jaise ek poora sher ho."""


def generate_shayari(theme: str) -> tuple[list[str], str]:
    """Returns (lines, youtube_music_query) — Groq picks both shayari AND best music."""
    prompt = f"""Theme: "{theme}"

Kaam: Do cheezein karo —

1. Is theme par ek COMPLETE shayari likho — 4 poori lines.
   - Har line 8-14 words ki honi chahiye — poori, meaningful
   - Chaaron lines connected honi chahiye — ek flow mein
   - LINE 3 sabse powerful — jo log raat ko yaad karein
   - Koi heading, number ya label mat likho

2. Is shayari ke liye PERFECT background music search query do.
   - YouTube pe search karne ke liye 4-6 English words
   - Real instrumental music — piano, guitar, violin, lofi etc.
   - Mood match karo — sad, romantic, lonely, rainy, peaceful etc.
   - Example queries: "sad piano music no copyright", "romantic violin instrumental", "lofi rain ambience", "emotional guitar background music"

FORMAT (bilkul aisa):
SHAYARI:
[line 1]
[line 2]
[line 3]
[line 4]
MUSIC: [youtube search query]"""

    try:
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SHAYARI_SYSTEM},
                {"role": "user", "content": prompt}
            ],
            max_tokens=350, temperature=0.95)

        raw = r.choices[0].message.content.strip()

        # Parse shayari lines
        lines = []
        music_query = None

        for line in raw.split("\n"):
            line = line.strip()
            if not line: continue
            if line.upper().startswith("SHAYARI:"): continue
            if line.upper().startswith("MUSIC:"):
                music_query = line[6:].strip().strip('"').strip("'")
                continue
            if line.startswith("[") or line.startswith("#"): continue
            lines.append(line)

        lines = [l for l in lines if len(l) > 5][:4]
        while len(lines) < 4:
            lines.append("kuch baatein kehne se nahi jaati.")

        if not music_query:
            music_query = f"{theme} sad piano instrumental no copyright"

        logger.info(f"🎵 Music query: {music_query}")
        return lines, music_query

    except Exception as e:
        logger.error(f"Shayari Groq: {e}")
        return [
            "tum yaad aate ho, aur hum chup ho jaate hain.",
            "kuch rishte khatam nahi hote, bas khamosh ho jaate hain.",
            "jo baat kehni thi, woh reh gayi andar.",
            "kuch dard kehne se nahi jaate.",
        ], f"{theme} sad piano no copyright"



def mix_ambient_audio(voice_path: str, output_path: str, duration: float):
    """Mix soft ambient tone under the voice (used for English POV only)."""
    try:
        ambient_path = output_path.replace(".mp4", "_ambient.mp3")
        os.system(f'ffmpeg -f lavfi -i "sine=frequency=432:duration={int(duration+2)}" -af "volume=0.07,aecho=0.8:0.5:60:0.3" "{ambient_path}" -y -loglevel quiet')
        if os.path.exists(ambient_path):
            voice   = mp.AudioFileClip(voice_path)
            ambient = mp.AudioFileClip(ambient_path).set_duration(voice.duration)
            mixed   = mp.CompositeAudioClip([ambient, voice])
            mixed_path = output_path.replace(".mp4", "_mixed.mp3")
            mixed.write_audiofile(mixed_path, fps=44100, verbose=False, logger=None)
            voice.close()
            ambient.close()
            if os.path.exists(ambient_path):
                os.remove(ambient_path)
            return mixed_path
    except Exception as e:
        logger.warning(f"Ambient mix failed: {e}")
    return voice_path


# ── Mood-matched royalty-free music (Pixabay — no copyright) ──────────────────
# All tracks from pixabay.com/music — 100% free, no attribution required
# Music generated via ffmpeg — no downloads needed, always works
# Each mood uses specific frequencies + effects to match the shayari vibe
SHAYARI_MUSIC_PARAMS = {
    # freq, echo_delay, echo_decay, reverb, description
    "sad":        (220, 80,  0.5, True,  "Minor A — melancholic piano feel"),
    "rain":       (196, 120, 0.6, True,  "G note — rainy ambient"),
    "night":      (174, 100, 0.55,True,  "F note — midnight lofi"),
    "love":       (261, 60,  0.4, False, "C note — warm romantic"),
    "loneliness": (185, 140, 0.65,True,  "F#/Gb — empty, lonely"),
}

# Map shayari theme → music mood
THEME_TO_MUSIC_MOOD = {
    "judai aur yaad":               "sad",
    "mohabbat ka dard":             "love",
    "rishton ka toota hua silsila": "sad",
    "akela pan ki raat":            "night",
    "jo baat keh na sake":          "sad",
    "woh jo reh gaya andar":        "sad",
    "intezaar ka dard":             "rain",
    "khaamoshi ki awaaz":           "night",
    "aankhon ka samandar":          "rain",
    "teri kami ka ehsaas":          "loneliness",
    "dil ka bojh":                  "sad",
    "waqt ka zakhm":                "loneliness",
}

# Map visual query keywords → music mood fallback
VISUAL_TO_MUSIC_MOOD = {
    "rain":      "rain",
    "night":     "night",
    "ocean":     "sad",
    "forest":    "loneliness",
    "sunset":    "love",
    "stars":     "night",
    "city":      "night",
    "candle":    "sad",
    "flower":    "love",
    "mountains": "loneliness",
}


def pick_music_mood(theme: str, query: str) -> str:
    """Pick music mood based on theme first, then visual query."""
    if theme in THEME_TO_MUSIC_MOOD:
        return THEME_TO_MUSIC_MOOD[theme]
    for keyword, mood in VISUAL_TO_MUSIC_MOOD.items():
        if keyword in query.lower():
            return mood
    return "sad"


def download_music(mood: str, output_path: str,
                   search_query: str = None) -> str | None:
    """
    Search YouTube for mood-matched royalty-free music using yt-dlp.
    Uses Groq-generated search query for best match per shayari.
    Falls back to numpy synthesis if yt-dlp fails.
    """
    import subprocess
    os.makedirs("assets/music", exist_ok=True)

    # Use search query from Groq if provided, else use mood defaults
    if not search_query:
        DEFAULT_QUERIES = {
            "sad":        "sad piano music no copyright",
            "night":      "lofi night calm instrumental no copyright",
            "love":       "romantic piano music no copyright",
            "rain":       "rain piano ambient music no copyright",
            "loneliness": "lonely piano emotional instrumental no copyright",
        }
        search_query = DEFAULT_QUERIES.get(mood, "sad piano music no copyright")

    # Add "no copyright" if not already there
    if "no copyright" not in search_query.lower() and "royalty free" not in search_query.lower():
        search_query += " no copyright"

    # Unique cache key per search query
    safe_key = "".join(c if c.isalnum() else "_" for c in search_query)[:40]
    mp3_path  = f"assets/music/{safe_key}.mp3"

    if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 100000:
        logger.info(f"🎵 Music cached: {mp3_path}")
        return mp3_path

    tmp_path = f"assets/music/tmp_{safe_key}"
    logger.info(f"🎵 Searching music: '{search_query}'")

    try:
        result = subprocess.run([
            "yt-dlp",
            f"ytsearch3:{search_query}",   # search top 3 results
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "5",
            "--output", tmp_path + ".%(ext)s",
            "--no-playlist",
            "--match-filter", "duration > 60 & duration < 600",  # 1-10 min tracks
            "--quiet",
            "--no-warnings",
            "--max-downloads", "1",        # only download first match
        ], capture_output=True, text=True, timeout=90)

        downloaded = tmp_path + ".mp3"
        if os.path.exists(downloaded) and os.path.getsize(downloaded) > 100000:
            # Trim to 65s with fade
            subprocess.run([
                "ffmpeg", "-i", downloaded,
                "-t", "65",
                "-af", "afade=t=in:ss=0:d=4,afade=t=out:st=61:d=4,volume=0.75",
                mp3_path, "-y", "-loglevel", "error"
            ], capture_output=True, timeout=30)
            try: os.remove(downloaded)
            except: pass
            if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 50000:
                logger.info(f"🎵 Music ready: {mp3_path} ({os.path.getsize(mp3_path)//1024}KB)")
                return mp3_path
        else:
            logger.warning(f"yt-dlp output: {result.stderr[:200]}")
    except Exception as e:
        logger.warning(f"yt-dlp failed: {e}")

    # Fallback: numpy synthesis
    logger.warning("⚠️  Falling back to numpy music synthesis")
    return _generate_numpy_music(mood, f"assets/music/{mood}_numpy.mp3")


def _generate_numpy_music(mood: str, mp3_path: str) -> str | None:
    """Fallback numpy music generator."""
    import numpy as np, wave, subprocess
    wav_path = mp3_path.replace(".mp3", ".wav")
    CHORDS = {
        "sad":        [220.0, 261.6, 329.6, 440.0],
        "night":      [174.6, 207.7, 261.6, 349.2],
        "love":       [261.6, 329.6, 392.0, 523.3],
        "rain":       [196.0, 233.1, 293.7, 392.0],
        "loneliness": [185.0, 220.0, 277.2, 370.0],
    }
    ECHO = {
        "sad":        (0.08, 0.45, 0.18, 0.25),
        "night":      (0.10, 0.50, 0.22, 0.28),
        "love":       (0.06, 0.38, 0.14, 0.20),
        "rain":       (0.12, 0.52, 0.25, 0.30),
        "loneliness": (0.14, 0.55, 0.28, 0.32),
    }
    SR = 44100; DUR = 65
    freqs = CHORDS.get(mood, CHORDS["sad"])
    weights = [0.50, 0.32, 0.22, 0.15]
    e1d, e1v, e2d, e2v = ECHO.get(mood, (0.08, 0.45, 0.18, 0.25))
    try:
        t = np.linspace(0, DUR, SR * DUR, endpoint=False)
        audio = np.zeros(len(t))
        for freq, w in zip(freqs, weights):
            audio += w * np.sin(2 * np.pi * freq * t)
            audio += (w * 0.08) * np.sin(2 * np.pi * (freq * 1.004) * t)
        d1 = int(SR * e1d); e1 = np.zeros(len(audio)); e1[d1:] = audio[:-d1] * e1v; audio += e1
        d2 = int(SR * e2d); e2 = np.zeros(len(audio)); e2[d2:] = audio[:-d2] * e2v; audio += e2
        fi = int(SR * 5); fo = int(SR * 5)
        audio[:fi] *= np.linspace(0, 1, fi); audio[-fo:] *= np.linspace(1, 0, fo)
        audio = audio / np.max(np.abs(audio)) * 0.80
        audio_int = (audio * 32767).astype(np.int16)
        with wave.open(wav_path, "w") as wf:
            wf.setnchannels(1); wf.setsampwidth(2)
            wf.setframerate(SR); wf.writeframes(audio_int.tobytes())
        subprocess.run(["ffmpeg", "-i", wav_path, "-codec:a", "libmp3lame",
            "-qscale:a", "2", mp3_path, "-y", "-loglevel", "error"],
            capture_output=True, timeout=30)
        try: os.remove(wav_path)
        except: pass
        if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 5000:
            return mp3_path
    except Exception as e:
        logger.warning(f"Numpy music failed: {e}")
    return None


def mix_shayari_music(music_path: str, output_path: str, duration: float) -> str | None:
    """Trim/loop music to video duration, fade in/out, return mixed path."""
    mixed_path = output_path.replace(".mp4", "_music.mp3")
    try:
        music = mp.AudioFileClip(music_path)
        if music.duration < duration:
            loops = math.ceil(duration / music.duration)
            music = mp.concatenate_audioclips([music] * loops)
        music = music.subclip(0, duration)
        music = music.audio_fadein(1.5).audio_fadeout(2.0)
        music = music.volumex(0.35)
        music.write_audiofile(mixed_path, fps=44100, verbose=False, logger=None)
        music.close()
        logger.info(f"🎵 Music ready: {mixed_path}")
        return mixed_path
    except Exception as e:
        logger.warning(f"Music mix failed: {e}")
        return None

def render_shayari_frame(lines: list[str], progress: float,
                         accent: tuple, bg_arr) -> np.ndarray:
    """Render one frame — aesthetic shayari page style. No voice, pure visuals."""
    # Background
    if bg_arr is not None:
        img = Image.fromarray(bg_arr).convert("RGBA")
    else:
        arr = np.zeros((H, W, 3), dtype=np.uint8)
        for y in range(H):
            v = int(5 + (y / H) * 20)
            arr[y, :] = [v, v+5, v+15]
        img = Image.fromarray(arr).convert("RGBA")

    # Heavy cinematic overlay — darker than POV for a more melancholic page feel
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay, "RGBA")
    for y in range(H):
        ratio = y / H
        center_dist = abs(ratio - 0.5) * 2
        # Darker overall — like ink on a page at night
        alpha = int(120 + center_dist * 100)
        od.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img, "RGBA")

    # Thin decorative top line (accent color)
    line_alpha = int(ease_in_out(min(1.0, progress * 3)) * 180)
    lw = int(W * 0.25)
    lx = (W - lw) // 2
    for xi in range(lw):
        fade = math.sin((xi / lw) * math.pi)
        a = int(line_alpha * fade)
        draw.rectangle([(lx+xi, 160), (lx+xi+1, 163)], fill=(*accent, a))

    # Urdu-style ornament dot (center top)
    if progress > 0.1:
        dot_alpha = int(ease_in_out(min(1.0, (progress - 0.1) * 4)) * 200)
        cx = W // 2
        draw.ellipse([(cx-6, 145), (cx+6, 157)], fill=(*accent, dot_alpha))

    # Lines layout — centered, generous spacing, staggered reveal
    n = len(lines)
    center_y = H // 2 + 40          # slightly below center — feels heavier
    line_spacing = 180               # more breathing room between shayari lines
    total_text_h = (n - 1) * line_spacing
    start_y = center_y - total_text_h // 2

    for i, line in enumerate(lines):
        threshold = i / (n + 1)
        local_p = max(0.0, min(1.0, (progress - threshold) * (n + 1) * 0.75))
        eased = ease_in_out(local_p)
        if eased < 0.01:
            continue

        alpha = int(eased * 255)
        y_drift = int((1 - eased) * 20)   # subtle upward drift
        y = start_y + i * line_spacing + y_drift

        # THE LINE (line 2, 0-indexed) gets accent treatment
        if i == 2:
            font = gfont(60, bold=True)
            color = accent
        elif i == 0:
            font = gfont(56, bold=True)
            color = (240, 240, 240)
        else:
            font = gfont(50, bold=False)
            color = (190, 190, 200)   # slightly cool white — more poetic

        bb = font.getbbox("A")
        cpl = max(5, (W - 140) // max(1, bb[2] - bb[0]))
        wrapped = textwrap.fill(line, width=cpl).split("\n")
        lh = (font.getbbox("Hg")[3] - font.getbbox("Hg")[1]) + 20

        for j, wline in enumerate(wrapped):
            lb = font.getbbox(wline)
            lw2 = lb[2] - lb[0]
            lx2 = (W - lw2) // 2
            ly = y + j * lh

            # Soft glow behind accent line
            if i == 2:
                glow_surf = Image.new("RGBA", (lw2 + 60, lh + 40), (0, 0, 0, 0))
                gd = ImageDraw.Draw(glow_surf, "RGBA")
                for spread in range(12, 0, -2):
                    ga = int((alpha / 255) * (13 - spread) * 4)
                    gd.rectangle([(spread, spread),
                                  (lw2 + 60 - spread, lh + 40 - spread)],
                                 fill=(*accent, ga))
                img.alpha_composite(glow_surf, dest=(lx2 - 30, ly - 20))
                draw = ImageDraw.Draw(img, "RGBA")

            # Strong dark outline for readability
            for ox, oy in [(-3,-3),(3,-3),(-3,3),(3,3),(-4,0),(4,0),(0,-4),(0,4)]:
                draw.text((lx2+ox, ly+oy), wline, font=font, fill=(0,0,0,min(255,alpha)))
            draw.text((lx2, ly), wline, font=font, fill=(*color, alpha))

    # Bottom thin accent line — mirror of top
    if progress > 0.7:
        ba = int(ease_in_out(min(1.0, (progress - 0.7) * 4)) * 160)
        lw3 = int(W * 0.25)
        lx3 = (W - lw3) // 2
        for xi in range(lw3):
            fade = math.sin((xi / lw3) * math.pi)
            a = int(ba * fade)
            draw.rectangle([(lx3+xi, H-163), (lx3+xi+1, H-160)], fill=(*accent, a))

    # Subtle watermark / channel handle — bottom center
    if progress > 0.8:
        wm_alpha = int(ease_in_out(min(1.0, (progress - 0.8) * 5)) * 120)
        try:
            wm_font = gfont(32, bold=False)
            wm_text = "@anime_community447"
            lb = wm_font.getbbox(wm_text)
            wm_w = lb[2] - lb[0]
            draw.text(((W - wm_w) // 2, H - 130), wm_text,
                      font=wm_font, fill=(200, 200, 200, wm_alpha))
        except:
            pass

    return np.array(img.convert("RGB"))


def build_shayari_video(output_path: str) -> tuple[str, str, str]:
    """Build a Hindi shayari video — NO voice, mood-matched music + aesthetic text page."""
    theme  = random.choice(SHAYARI_THEMES)
    visual = random.choice(["nature", "urban"])
    query  = random.choice(VISUAL_QUERIES[visual])
    accent = random.choice([(255,150,180), (180,120,255), (255,200,100), (100,200,255)])

    logger.info(f"📿 Shayari: \'{theme}\' | {visual} | query: {query}")

    lines, music_query = generate_shayari(theme)
    logger.info(f"📝 Shayari lines: {lines}")
    logger.info(f"🎵 Music query from Groq: {music_query}")

    bg_path = download_pexels_clip(query)
    total_dur = 18.0    # slightly longer — shayari needs time to breathe
    n_frames  = int(total_dur * FPS)

    # Load background frames
    bg_frames = None
    if bg_path:
        try:
            raw = mp.VideoFileClip(bg_path, audio=False)
            if raw.duration < total_dur:
                loops = math.ceil(total_dur / raw.duration)
                raw = mp.concatenate_videoclips([raw] * loops)
            raw = raw.subclip(0, total_dur)
            raw = raw.resize(height=H)
            if raw.w < W:
                raw = raw.resize(width=W)
            x_off = max(0, (raw.w - W) // 2)
            y_off = max(0, (raw.h - H) // 2)
            raw = raw.crop(x1=x_off, y1=y_off, x2=x_off+W, y2=y_off+H)
            bg_frames = []
            for fi in range(n_frames):
                t = fi / FPS
                try:
                    frame = raw.get_frame(t)
                    bg_frames.append(frame)
                except:
                    bg_frames.append(bg_frames[-1] if bg_frames else np.zeros((H, W, 3), dtype=np.uint8))
            raw.close()
            logger.info("🎥 Shayari BG loaded")
        except Exception as e:
            logger.warning(f"Shayari BG failed: {e}")

    # Render frames using shayari-specific renderer
    rendered = []
    for fi in range(n_frames):
        progress = fi / n_frames
        bg_arr = bg_frames[fi] if bg_frames else None
        frame = render_shayari_frame(lines, progress, accent, bg_arr)
        rendered.append(frame)

    final = mp.ImageSequenceClip(rendered, fps=FPS)
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    # ── Music (NO voice for shayari) ──────────────────────────────────────────
    music_mood = pick_music_mood(theme, query)
    logger.info(f"🎵 Music mood: {music_mood}")
    music_local = download_music(music_mood, output_path, search_query=music_query)

    if music_local:
        music_path = mix_shayari_music(music_local, output_path, total_dur)
        if music_path and os.path.exists(music_path):
            try:
                audio_clip = mp.AudioFileClip(music_path)
                final = final.set_audio(audio_clip)
                logger.info(f"🎵 Music added: {music_mood} mood")
            except Exception as e:
                logger.warning(f"Music attach failed: {e}")
    else:
        logger.warning("⚠️  No music — posting silent shayari video")

    final.write_videofile(output_path, fps=FPS, codec="libx264",
                          audio=True, audio_codec="aac",
                          verbose=False, logger=None,
                          ffmpeg_params=["-crf", "16", "-preset", "slow"])
    final.close()
    import gc; gc.collect()
    import time; time.sleep(2)
    # Cleanup temp music files
    for suffix in ["_music.mp3"]:
        f = output_path.replace(".mp4", suffix)
        try:
            if os.path.exists(f): os.remove(f)
        except: pass
    logger.info(f"✅ Shayari saved: {output_path}")

    title   = lines[0]
    body    = "\n".join(lines[1:])
    caption = f"{title}\n\n{body}\n\n#shayari #urdu #hindi #dard #mohabbat #feelings #viral #fyp #reels"
    return title, body, caption


def build_pov_video(output_path: str) -> tuple[str, str, str]:
    """Build one premium POV video. Returns (title, body, caption)."""
    mood     = random.choice(list(POV_TOPICS.keys()))
    topic    = random.choice(POV_TOPICS[mood])
    language = random.choice(["english", "hinglish", "hinglish"])  # bias toward hinglish
    visual   = random.choice(["nature", "urban"])
    query    = random.choice(VISUAL_QUERIES[visual])
    accent   = ACCENTS.get(mood, (255, 100, 150))

    logger.info(f"🎬 POV: '{topic}' | {mood} | {language} | {visual}")

    lines = generate_pov_lines(topic, mood, language)
    logger.info(f"📝 Lines: {lines}")

    bg_path = download_pexels_clip(query)

    total_dur = 15.0
    n_frames  = int(total_dur * FPS)

    # Pre-load background video frames
    bg_frames = None
    if bg_path:
        try:
            raw = mp.VideoFileClip(bg_path, audio=False)
            if raw.duration < total_dur:
                loops = math.ceil(total_dur / raw.duration)
                raw = mp.concatenate_videoclips([raw] * loops)
            raw = raw.subclip(0, total_dur)
            raw = raw.resize(height=H)
            if raw.w < W:
                raw = raw.resize(width=W)
            x_off = max(0, (raw.w - W) // 2)
            y_off = max(0, (raw.h - H) // 2)
            raw = raw.crop(x1=x_off, y1=y_off, x2=x_off+W, y2=y_off+H)
            # Sample frames at intervals
            bg_frames = []
            for fi in range(n_frames):
                t = fi / FPS
                try:
                    frame = raw.get_frame(t)
                    bg_frames.append(frame)
                except:
                    bg_frames.append(bg_frames[-1] if bg_frames else np.zeros((H, W, 3), dtype=np.uint8))
            raw.close()
            logger.info("🎥 BG frames loaded")
        except Exception as e:
            logger.warning(f"BG load failed: {e}")
            bg_frames = None

    # Render all frames
    rendered = []
    for fi in range(n_frames):
        progress = fi / n_frames
        bg_arr = bg_frames[fi] if bg_frames else None
        frame = render_pov_frame(lines, progress, accent, bg_arr)
        rendered.append(frame)

    final = mp.ImageSequenceClip(rendered, fps=FPS)
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    # Add Christopher voice TTS
    # Format POV for natural emotional delivery
    spoken = ".  ".join(lines) + "."
    audio_path = output_path.replace(".mp4", "_audio.mp3")
    try:
        gen_pov_tts(spoken, audio_path, voice="en-US-ChristopherNeural", rate="-10%")
        final_audio = mix_ambient_audio(audio_path, output_path, total_dur)
        audio_clip = mp.AudioFileClip(final_audio)
        vid_dur = max(total_dur, audio_clip.duration + 1.0)
        if vid_dur > total_dur:
            final = final.set_duration(vid_dur)
        dur_info = audio_clip.duration
        final = final.set_audio(audio_clip)
        logger.info(f"🎤 POV audio: {dur_info:.1f}s")
    except Exception as e:
        logger.warning(f"POV TTS failed: {e}")

    final.write_videofile(output_path, fps=FPS, codec="libx264",
                          audio=True, audio_codec="aac",
                          verbose=False, logger=None,
                          ffmpeg_params=["-crf", "16", "-preset", "slow"])
    final.close()
    import gc; gc.collect(); import time; time.sleep(2)
    for f in [audio_path, audio_path.replace("_audio.mp3","_mixed.mp3")]:
        try:
            if os.path.exists(f): os.remove(f)
        except: pass
    logger.info(f"✅ POV saved: {output_path}")

    title   = lines[0]
    body    = "\n".join(lines[1:])
    caption = f"{title}\n\n{body}\n\n#pov #emotional #relatable #fyp #foryou #viral #shorts #feelings"
    return title, body, caption


def make_and_post_pov():
    """Full POV pipeline: generate → upload to YouTube + Instagram."""
    logger.info("━" * 50)
    logger.info("🎭 POV pipeline starting…")
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = os.path.join(config.OUTPUT_DIR, f"pov_{ts}.mp4")
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    # 50/50 chance — POV English or Hindi Shayari
    if random.random() < 0.8:
        title, body, caption = build_shayari_video(out)
        logger.info("📿 Type: Shayari")
    else:
        title, body, caption = build_pov_video(out)
        logger.info("🎭 Type: POV")

    from modules.uploader import upload_pov
    result = upload_pov(out, title, body, vars(config))

    yt_url = (result.get("youtube") or {}).get("url", "N/A")
    ig_url = (result.get("instagram") or {}).get("url", "N/A")
    logger.info(f"🎉 POV Done! YouTube: {yt_url} | Instagram: {ig_url}")

    # Cleanup
    if os.path.exists(out):
        os.remove(out)
    import gc; gc.collect()
    import time; time.sleep(2)
    for folder in ["assets/pov"]:
        if os.path.isdir(folder):
            for f in os.listdir(folder):
                fp = os.path.join(folder, f)
                try:
                    if os.path.isfile(fp): os.remove(fp)
                except: pass
    logger.info("━" * 50)


def run_pov_scheduler():
    os.makedirs("logs", exist_ok=True)
    logger.info("=" * 50)
    logger.info("  POV BOT — 3 videos/day → YouTube + Instagram")
    logger.info("=" * 50)

    for t in ["10:00", "15:30", "20:00"]:
        schedule.every().day.at(t).do(make_and_post_pov)
        logger.info(f"⏰ POV scheduled at {t}")

    if "--now" in sys.argv:
        make_and_post_pov()

    logger.info("🤖 POV Bot running.")
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    run_pov_scheduler()