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


def generate_pov_lines(topic: str, mood: str, language: str) -> list[str]:
    lang_note = (
        "Write in Hinglish (romanized Hindi mixed with English). Poetic, emotional."
        if language == "hinglish"
        else "Write in English. Raw, emotional, hits deep."
    )
    prompt = f"""Write a viral Instagram POV reel. Topic: "POV: {topic}"
{lang_note}

Output EXACTLY 4 lines. Each line max 9 words. No labels, no numbers.
Line 1: The POV hook starting with "POV:"
Line 2: Build the feeling
Line 3: THE LINE — the one that makes them save it
Line 4: The quiet closer that lingers

Only output the 4 lines, nothing else."""

    try:
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120, temperature=0.95)
        lines = [l.strip() for l in r.choices[0].message.content.strip().split("\n")
                 if l.strip()][:4]
        while len(lines) < 4:
            lines.append(random.choice(HINGLISH_LINES))
        return lines
    except Exception as e:
        logger.error(f"Groq: {e}")
        return [f"POV: {topic}", "you know this feeling.", "some things don't need words.",
                random.choice(HINGLISH_LINES)]


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

SHAYARI_SYSTEM = """Tu ek mashoor shayar hai jisme Mirza Ghalib, Gulzar aur Rahat Indori ki rooh bassi hai.
Tujhe ek emotional, viral Instagram reel ke liye shayari likhni hai.

STYLE:
- Romanized Hindi (Hinglish) — jaise log WhatsApp pe likhte hain
- Har line 6-9 words mein — punchy, dil ko chhune wali
- Metaphors use kar — chaand, dariya, aankhein, raat, khamoshi
- Feel: dard + khubsurati dono saath
- Lines aapas mein connected honi chahiye — ek story ki tarah flow karo

FORMAT (bilkul aisa hi):
Line 1: ek aisa sher jo scroll rokde
Line 2: dard gehra karo — pichli line se connected
Line 3: THE LINE — jo log screenshot lete hain
Line 4: khamosh khatma — jo dil mein reh jaaye

SIRF 4 lines likho. Koi label nahi. Koi number nahi. Bas shayari.
Lines natural flow mein honi chahiye — jaise ek shayar bolte bolte ruk jaata hai."""


def generate_shayari(theme: str) -> list[str]:
    prompt = f"""Theme: "{theme}"
Ek viral Instagram shayari likho is theme par.
Sirf 4 lines — har line max 9 words.
Romanized Hindi mein. Dil ko chhune wali."""

    try:
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SHAYARI_SYSTEM},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150, temperature=0.97)
        lines = [l.strip() for l in r.choices[0].message.content.strip().split("\n")
                 if l.strip()][:4]
        while len(lines) < 4:
            lines.append("kuch baatein kehne se nahi jaati.")
        return lines
    except Exception as e:
        logger.error(f"Shayari Groq: {e}")
        return [
            "tum yaad aate ho, aur hum chup ho jaate hain.",
            "kuch rishte khatam nahi hote, bas khamosh ho jaate hain.",
            "jo baat kehni thi, woh reh gayi andar.",
            "kuch dard kehne se nahi jaate.",
        ]


def build_shayari_video(output_path: str) -> tuple[str, str, str]:
    """Build a Hindi shayari POV video."""
    theme  = random.choice(SHAYARI_THEMES)
    visual = random.choice(["nature", "urban"])
    query  = random.choice(VISUAL_QUERIES[visual])
    accent = random.choice([(255,150,180), (180,120,255), (255,200,100), (100,200,255)])
    mood   = random.choice(["love", "heartbreak", "loneliness"])

    logger.info(f"📿 Shayari: '{theme}' | {visual}")

    lines = generate_shayari(theme)
    logger.info(f"📝 Shayari: {lines}")

    bg_path = download_pexels_clip(query)
    total_dur = 15.0
    n_frames  = int(total_dur * FPS)

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
        except Exception as e:
            logger.warning(f"BG failed: {e}")

    rendered = []
    for fi in range(n_frames):
        progress = fi / n_frames
        bg_arr = bg_frames[fi] if bg_frames else None
        frame = render_pov_frame(lines, progress, accent, bg_arr)
        rendered.append(frame)

    final = mp.ImageSequenceClip(rendered, fps=FPS)
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    # TTS — Hindi voice
    # Format shayari for natural recitation — commas create breath pauses
    spoken = ",  ".join(lines) + "."
    audio_path = output_path.replace(".mp4", "_audio.mp3")
    try:
        gen_pov_tts(spoken, audio_path, voice="hi-IN-MadhurNeural", rate="-20%")
        audio_clip = mp.AudioFileClip(audio_path)
        vid_dur = max(total_dur, audio_clip.duration + 1.0)
        if vid_dur > total_dur:
            final = final.set_duration(vid_dur)
        final = final.set_audio(audio_clip)
        logger.info(f"🎤 Shayari audio: {audio_clip.duration:.1f}s")
    except Exception as e:
        logger.warning(f"Hindi TTS failed, trying English: {e}")

    final.write_videofile(output_path, fps=FPS, codec="libx264",
                          audio=True, audio_codec="aac",
                          verbose=False, logger=None,
                          ffmpeg_params=["-crf", "16", "-preset", "slow"])
    final.close()
    if os.path.exists(audio_path):
        os.remove(audio_path)
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
    spoken = ",  ".join(lines) + "."
    audio_path = output_path.replace(".mp4", "_audio.mp3")
    try:
        gen_pov_tts(spoken, audio_path, voice="en-US-ChristopherNeural", rate="-12%")
        audio_clip = mp.AudioFileClip(audio_path)
        vid_dur = max(total_dur, audio_clip.duration + 1.0)
        if vid_dur > total_dur:
            final = final.set_duration(vid_dur)
        final = final.set_audio(audio_clip)
        logger.info(f"🎤 POV audio: {audio_clip.duration:.1f}s")
    except Exception as e:
        logger.warning(f"POV TTS failed: {e}")

    final.write_videofile(output_path, fps=FPS, codec="libx264",
                          audio=True, audio_codec="aac",
                          verbose=False, logger=None,
                          ffmpeg_params=["-crf", "16", "-preset", "slow"])
    final.close()
    if os.path.exists(audio_path):
        os.remove(audio_path)
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
    if random.random() < 0.5:
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
    for folder in ["assets/pov"]:
        if os.path.isdir(folder):
            for f in os.listdir(folder):
                fp = os.path.join(folder, f)
                if os.path.isfile(fp):
                    os.remove(fp)
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