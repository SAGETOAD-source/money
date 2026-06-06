"""
manga_maker.py — Daily Manga/Manhwa Explanation Bot
1 video/day → YouTube + Instagram
Explains the most gripping moment/arc from popular manga/manhwa
"""

import os, sys, asyncio, random, logging, math, textwrap, requests, time, schedule, json
import numpy as np
import moviepy.editor as mp
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
import config
from groq import Groq

if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.LANCZOS

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    handlers=[logging.StreamHandler(sys.stdout),
              logging.FileHandler("logs/manga_bot.log", encoding="utf-8")])
logger = logging.getLogger(__name__)

client = Groq(api_key=config.GROQ_API_KEY)
W, H, FPS = 1080, 1920, 30

# ── Popular series rotation ────────────────────────────────────────────────────
MANGA_SERIES = [
    # Manhwa
    {"title": "Solo Leveling", "type": "manhwa",
     "hooks": ["Sung Jinwoo went from weakest to unstoppable. Here's how.",
               "The scene in Solo Leveling that broke everyone.",
               "Why Sung Jinwoo is the most feared hunter alive."]},
    {"title": "Lookism", "type": "manhwa",
     "hooks": ["Lookism shows the darkest truth about society.",
               "The hidden meaning behind Daniel Park's two bodies.",
               "Why Lookism is more than just a beauty story."]},
    {"title": "Tower of God", "type": "manhwa",
     "hooks": ["Bam climbed the tower for one person. It destroyed him.",
               "The twist in Tower of God nobody saw coming.",
               "Why Tower of God's ending hits different."]},
    {"title": "Omniscient Reader", "type": "manhwa",
     "hooks": ["He read the story. Then he lived it.",
               "Omniscient Reader has the most emotional ending in manhwa.",
               "Why Kim Dokja is the most tragic protagonist ever."]},
    {"title": "The Beginning After the End", "type": "manhwa",
     "hooks": ["Arthur Leywin carries two lifetimes of pain.",
               "The moment TBATE became something else entirely.",
               "Why TBATE's power system is genius."]},
    {"title": "Eleceed", "type": "manhwa",
     "hooks": ["The funniest manhwa hiding the deepest story.",
               "Kayden inside a cat. The premise that works perfectly.",
               "Why Eleceed's friendship hits harder than any romance."]},
    # Manga
    {"title": "Berserk", "type": "manga",
     "hooks": ["Guts carried more pain than any fictional character.",
               "The Eclipse in Berserk is the darkest scene in manga history.",
               "Why Berserk's ending was inevitable from chapter one."]},
    {"title": "Chainsaw Man", "type": "manga",
     "hooks": ["Denji just wanted a normal life. He never got it.",
               "Chainsaw Man has the most devastating plot twist in manga.",
               "Why Makima is the best written villain in modern manga."]},
    {"title": "Vinland Saga", "type": "manga",
     "hooks": ["Thorfinn's revenge arc is the greatest character arc in manga.",
               "Vinland Saga's message about violence will stay with you.",
               "The moment Thorfinn became something greater than a warrior."]},
    {"title": "Jujutsu Kaisen", "type": "manga",
     "hooks": ["Gege Akutami hates his characters. The proof is everywhere.",
               "The Shibuya arc changed JJK forever.",
               "Why Gojo Satoru's sealing hit so hard."]},
    {"title": "One Piece", "type": "manga",
     "hooks": ["One Piece hid its real meaning in plain sight for 25 years.",
               "The Ohara incident is the darkest arc in One Piece.",
               "Why Luffy's freedom means more than you think."]},
    {"title": "Attack on Titan", "type": "manga",
     "hooks": ["Attack on Titan's ending was planned from chapter one.",
               "Eren Yeager was the villain the whole time. The clues were there.",
               "The hidden symbolism in AoT nobody talks about."]},
]

# ── Pexels queries per mood ────────────────────────────────────────────────────
MANGA_VISUALS = {
    "action":    ["warrior silhouette dark", "sword fight dramatic", "explosion power energy",
                  "dark dungeon corridor", "battle dramatic sky"],
    "emotional": ["person alone rain", "sad silhouette sunset", "tears close up",
                  "empty road night", "hands reaching darkness"],
    "mystery":   ["dark forest fog", "shadow figure night", "ancient ruins mysterious",
                  "dark corridor light end", "shadow walking alone"],
    "power":     ["lightning storm dramatic", "energy surge abstract", "dark sky lightning",
                  "silhouette power dramatic", "glowing eyes dark"],
}

MANGA_SYSTEM_PROMPT = """You are a viral manga/manhwa narrator on YouTube Shorts.
You explain the MOST GRIPPING moment, arc, or hidden meaning from a series.
Your goal: make non-readers desperate to read it. Make readers feel seen.

STYLE: Dramatic narrator. Build tension like a movie trailer. Personal, passionate.

FORMAT (follow exactly):
- Line 1: HOOK — one line that makes them stop scrolling
- [blank line]
- Lines 2-3: SETUP — the situation, the stakes
- [blank line]
- Lines 4-5: THE MOMENT — the scene/twist/revelation that hits hardest
- [blank line]
- Lines 6-7: THE IMPACT — why this matters, what it means
- [blank line]
- Last line: CTA — "read it. you'll understand." or "follow for more."

STRICT RULES:
- Output ONLY spoken words
- Max 8 words per sentence
- ALWAYS complete all sections
- Sound like someone who genuinely loves this series
- Make them FEEL something
- Never spoil everything — leave them wanting more"""


def generate_manga_script(series: dict, hook: str) -> str:
    prompt = f"""Write a {config.SCRIPT_WORD_COUNT}-word viral YouTube Shorts script.
Series: "{series['title']}" ({series['type']})
Opening hook: "{hook}"
Pick the single most emotionally gripping or shocking moment/arc from this series.
Make non-readers want to read it immediately. Make readers feel understood.
COMPLETE all sections. Never stop early."""

    try:
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": MANGA_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=700,
            temperature=0.90,
        )
        script = r.choices[0].message.content.strip()
        logger.info(f"✅ Manga script: {len(script.split())} words")
        return script
    except Exception as e:
        logger.error(f"Groq error: {e}")
        return f"""{hook}

This series changes how you see everything.

The moment hits you like nothing else.

You won't see the twist coming.

It stays with you long after you finish.

This is why it's legendary.

Read it. You'll understand."""


def download_pexels_clip(query: str) -> str | None:
    key = config.PEXELS_API_KEY
    if not key or key.startswith("YOUR"):
        return None
    os.makedirs("assets/manga", exist_ok=True)
    try:
        r = requests.get("https://api.pexels.com/videos/search",
            headers={"Authorization": key},
            params={"query": query, "per_page": 8,
                    "orientation": "portrait", "size": "medium"},
            timeout=15)
        videos = r.json().get("videos", [])
        if not videos: return None
        video = random.choice(videos[:5])
        files = [f for f in video["video_files"] if f.get("width", 0) >= 720]
        if not files: files = video["video_files"]
        url = sorted(files, key=lambda x: x.get("width", 0))[-1]["link"]
        path = f"assets/manga/{video['id']}.mp4"
        if os.path.exists(path): return path
        resp = requests.get(url, stream=True, timeout=60)
        with open(path, "wb") as f:
            for chunk in resp.iter_content(65536): f.write(chunk)
        logger.info(f"✅ Manga clip: {path}")
        return path
    except Exception as e:
        logger.warning(f"Pexels: {e}")
        return None


_FC = {}
def gfont(size, bold=False):
    k = (size, bold)
    if k in _FC: return _FC[k]
    paths = [
        "C:/Windows/Fonts/Impact.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    f = ImageFont.load_default()
    for p in paths:
        if os.path.exists(p):
            try: f = ImageFont.truetype(p, size); break
            except: pass
    _FC[k] = f
    return f


async def _tts(text, path):
    import edge_tts
    await edge_tts.Communicate(text, "en-US-ChristopherNeural",
                                rate="-10%", pitch="-3Hz").save(path)

def gen_tts(text, path):
    asyncio.run(_tts(text, path))


def render_manga_frame(script_lines: list, progress: float,
                       series_title: str, bg_arr) -> np.ndarray:
    if bg_arr is not None:
        img = Image.fromarray(bg_arr).convert("RGBA")
    else:
        arr = np.zeros((H, W, 3), dtype=np.uint8)
        for y in range(H):
            v = int(5 + (y/H)*20)
            arr[y,:] = [v, v+5, v+15]
        img = Image.fromarray(arr).convert("RGBA")

    # Heavy dark overlay — manga aesthetic
    ov = Image.new("RGBA", (W, H), (0,0,0,0))
    od = ImageDraw.Draw(ov, "RGBA")
    for y in range(H):
        r = y/H
        a = int(100 + abs(r-0.5)*2*100)
        od.line([(0,y),(W,y)], fill=(0,0,0,a))
    img = Image.alpha_composite(img, ov)
    draw = ImageDraw.Draw(img, "RGBA")

    # Series title bar at top
    bar_h = 100
    draw.rectangle([(0,0),(W,bar_h)], fill=(0,0,0,200))
    tf = gfont(42, bold=True)
    tb = tf.getbbox(series_title)
    draw.text(((W-(tb[2]-tb[0]))//2, (bar_h-(tb[3]-tb[1]))//2),
              series_title, font=tf, fill=(255,200,0,230))

    # Accent line under title
    draw.rectangle([(0, bar_h),(W, bar_h+3)], fill=(255,200,0,180))

    # Script text — word by word stagger
    n = len(script_lines)
    start_y = H//2 - 80
    lsp = 115

    for i, line in enumerate(script_lines[:6]):
        threshold = i / (n+1)
        p = max(0.0, min(1.0, (progress - threshold) * (n+1) * 0.7))
        p = p*p*(3-2*p)  # ease
        if p < 0.01: continue

        alpha = int(p * 255)
        y_off = int((1-p)*25)
        y = start_y + i*lsp + y_off

        font = gfont(62 if i==0 else 52, bold=(i==0))
        color = (255,200,0) if i==0 else (240,240,240)

        bb = font.getbbox("A")
        cpl = max(5, (W-80)//(bb[2]-bb[0]))
        wrapped = textwrap.fill(line, width=cpl).split("\n")
        lh = (font.getbbox("Hg")[3]-font.getbbox("Hg")[1])+16

        for j, wl in enumerate(wrapped):
            lb = font.getbbox(wl)
            lw = lb[2]-lb[0]
            lx = (W-lw)//2
            ly = y+j*lh
            for ox,oy in [(-3,-3),(3,-3),(-3,3),(3,3)]:
                draw.text((lx+ox,ly+oy), wl, font=font, fill=(0,0,0,alpha))
            draw.text((lx,ly), wl, font=font, fill=(*color, alpha))

    # Bottom bar
    draw.rectangle([(0,H-80),(W,H)], fill=(0,0,0,200))
    if progress > 0.8:
        pa = int(min(1.0,(progress-0.8)*5)*180)
        draw.text((W//2-100, H-60), "follow for more", font=gfont(36),
                 fill=(180,180,180,pa))

    return np.array(img.convert("RGB"))


def build_manga_video(output_path: str) -> tuple[str, str, str]:
    series = random.choice(MANGA_SERIES)
    hook   = random.choice(series["hooks"])
    mood   = random.choice(list(MANGA_VISUALS.keys()))
    query  = random.choice(MANGA_VISUALS[mood])

    logger.info(f"📖 {series['title']} | {mood} | query: {query}")

    script = generate_manga_script(series, hook)
    script_lines = [l.strip() for l in script.split("\n") if l.strip()]

    bg_path = download_pexels_clip(query)
    total_dur = 30.0  # manga videos slightly longer — 30 sec
    n_frames = int(total_dur * FPS)

    bg_frames = None
    if bg_path:
        try:
            raw = mp.VideoFileClip(bg_path, audio=False)
            if raw.duration < total_dur:
                loops = math.ceil(total_dur / raw.duration)
                raw = mp.concatenate_videoclips([raw]*loops)
            raw = raw.subclip(0, total_dur)
            raw = raw.resize(height=H)
            if raw.w < W: raw = raw.resize(width=W)
            x_off = max(0, (raw.w-W)//2)
            y_off = max(0, (raw.h-H)//2)
            raw = raw.crop(x1=x_off, y1=y_off, x2=x_off+W, y2=y_off+H)
            bg_frames = []
            for fi in range(n_frames):
                try: bg_frames.append(raw.get_frame(fi/FPS))
                except: bg_frames.append(bg_frames[-1] if bg_frames else np.zeros((H,W,3),dtype=np.uint8))
            raw.close()
        except Exception as e:
            logger.warning(f"BG failed: {e}")

    rendered = []
    for fi in range(n_frames):
        frame = render_manga_frame(script_lines, fi/n_frames,
                                   series["title"],
                                   bg_frames[fi] if bg_frames else None)
        rendered.append(frame)

    final = mp.ImageSequenceClip(rendered, fps=FPS)
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    # TTS
    audio_path = output_path.replace(".mp4", "_audio.mp3")
    try:
        gen_tts(script, audio_path)
        ac = mp.AudioFileClip(audio_path)
        dur = max(total_dur, ac.duration + 1.0)
        if dur > total_dur: final = final.set_duration(dur)
        final = final.set_audio(ac)
        logger.info(f"🎤 Audio: {ac.duration:.1f}s")
    except Exception as e:
        logger.warning(f"TTS failed: {e}")

    final.write_videofile(output_path, fps=FPS, codec="libx264",
                          audio=True, audio_codec="aac",
                          verbose=False, logger=None,
                          ffmpeg_params=["-crf","16","-preset","slow"])
    final.close()
    if os.path.exists(audio_path): os.remove(audio_path)
    logger.info(f"✅ Manga video: {output_path}")

    caption = f"{hook}\n\n#{series['title'].replace(' ','')} #{series['type']} #anime #manga #fyp #viral #shorts"
    return hook, series["title"], caption


def make_and_post_manga():
    logger.info("━"*50)
    logger.info("📖 Manga pipeline starting…")
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = os.path.join(config.OUTPUT_DIR, f"manga_{ts}.mp4")
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    hook, title, caption = build_manga_video(out)

    from modules.uploader import upload_pov
    result = upload_pov(out, hook, title, vars(config))

    yt  = (result.get("youtube") or {}).get("url", "N/A")
    ig  = (result.get("instagram") or {}).get("url", "N/A")
    logger.info(f"🎉 Manga Done! YouTube: {yt} | Instagram: {ig}")

    if os.path.exists(out): os.remove(out)
    for f in os.listdir("assets/manga") if os.path.isdir("assets/manga") else []:
        fp = os.path.join("assets/manga", f)
        if os.path.isfile(fp): os.remove(fp)
    logger.info("━"*50)


def run_manga_scheduler():
    os.makedirs("logs", exist_ok=True)
    logger.info("="*50)
    logger.info("  MANGA BOT — 1 video/day → YouTube + Instagram")
    logger.info("="*50)

    schedule.every().day.at("13:00").do(make_and_post_manga)
    logger.info("⏰ Manga scheduled at 13:00")

    if "--now" in sys.argv:
        make_and_post_manga()

    logger.info("🤖 Manga Bot running.")
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    run_manga_scheduler()
