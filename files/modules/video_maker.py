"""
video_maker.py — ANIMATED STOCK VIDEO EDITION
• Downloads relevant HD stock video from Pexels (free API)
• Animated text: slides in word by word
• Smooth fade/zoom transitions between scenes
• YouTube-style subscribe button animation at end
• Falls back to animated gradient if Pexels fails
"""

import asyncio, os, textwrap, tempfile, logging, requests, math, random, time
import numpy as np
import edge_tts
import moviepy.editor as mp
from PIL import Image, ImageDraw, ImageFont

# Pillow 10+ removed ANTIALIAS — patch for MoviePy compatibility
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.LANCZOS

logger = logging.getLogger(__name__)
W, H = 1080, 1920
FPS  = 30

# ── Niche → Pexels search terms ───────────────────────────────────────────────
NICHE_KEYWORDS = {
    "facts":       ["mind blowing", "universe space", "deep ocean", "microscope science"],
    "relatable":   ["tired person", "stressed person", "phone scrolling", "insomnia night"],
    "psychology":  ["brain mind", "shadow dark", "eye contact", "manipulation chess"],
    "relationships":["couple silhouette", "heartbreak alone", "red flag warning", "walking away"],
    "mystery":     ["dark secret", "conspiracy shadow", "hidden truth", "ancient mystery"],
    "horror":      ["dark forest night", "abandoned building", "shadow horror", "dark corridor creepy"],
    "movies":      ["cinema film reel", "dramatic silhouette", "emotional face close", "dark dramatic light"],
    "football":    ["football stadium crowd", "soccer player running", "football training", "stadium lights night", "football goal celebration"],
    "tech":        ["technology abstract", "artificial intelligence", "futuristic city", "digital data"],
    "science":     ["science laboratory", "space galaxy", "dna biology", "brain neuron"],
    "motivation":  ["mountain sunrise", "running athletics", "success winner", "city skyline"],
    "default":     ["abstract particles", "light bokeh", "nature timelapse", "city night"],
}

# ── Color palettes ────────────────────────────────────────────────────────────
PALETTES = {
    "facts":        {"accent": (155,80,255),  "accent2": (200,140,255)},
    "relatable":    {"accent": (255,100,80),  "accent2": (255,160,120)},
    "psychology":   {"accent": (180,0,255),   "accent2": (220,80,255)},
    "relationships":{"accent": (255,60,100),  "accent2": (255,120,150)},
    "mystery":      {"accent": (60,180,255),  "accent2": (120,210,255)},
    "horror":       {"accent": (180,0,0),     "accent2": (255,60,60)},
    "movies":       {"accent": (255,200,0),   "accent2": (255,230,80)},
    "football":     {"accent": (0,200,80),    "accent2": (80,255,140)},
    "tech":         {"accent": (0,210,255),   "accent2": (80,240,255)},
    "motivation":   {"accent": (255,70,90),   "accent2": (255,130,150)},
    "default":      {"accent": (140,80,255),  "accent2": (190,130,255)},
}

_FC = {}
def gfont(size, bold=False):
    k = (size, bold)
    if k in _FC: return _FC[k]
    paths = [
        "Montserrat-ExtraBold.ttf", "Montserrat-Bold.ttf",
        "C:/Windows/Fonts/Impact.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    f = ImageFont.load_default()
    for p in paths:
        if os.path.exists(p):
            try: f = ImageFont.truetype(p, size); break
            except: pass
    _FC[k] = f; return f

# ── Pexels video downloader ───────────────────────────────────────────────────

def download_pixabay_video(query: str, pixabay_key: str,
                           cache_dir: str = "assets/videos") -> str | None:
    """Fallback video source when Pexels has no good match."""
    if not pixabay_key or pixabay_key.startswith("YOUR"):
        return None
    os.makedirs(cache_dir, exist_ok=True)
    try:
        r = requests.get("https://pixabay.com/api/videos/",
            params={"key": pixabay_key, "q": query, "per_page": 10,
                    "video_type": "film", "orientation": "vertical"},
            timeout=10)
        hits = r.json().get("hits", [])
        if not hits: return None
        video = random.choice(hits[:5])
        # Pick medium quality
        videos = video.get("videos", {})
        url = (videos.get("medium") or videos.get("small") or {}).get("url")
        if not url: return None
        vid_id = video["id"]
        path = f"{cache_dir}/px_{vid_id}.mp4"
        if os.path.exists(path): return path
        resp = requests.get(url, stream=True, timeout=30)
        with open(path, "wb") as f:
            for chunk in resp.iter_content(65536): f.write(chunk)
        logger.info(f"✅ Pixabay clip: {path}")
        return path
    except Exception as e:
        logger.warning(f"Pixabay error: {e}")
        return None


def extract_video_query(topic: str, niche: str) -> str:
    """Extract the best search query from the topic for Pexels."""
    topic_lower = topic.lower()
    
    # Direct keyword mapping for common topics
    keyword_map = {
        "ocean": "ocean waves underwater",
        "space": "space galaxy stars",
        "brain": "brain neuron mind",
        "sleep": "sleeping night peaceful",
        "dream": "dream surreal abstract",
        "memory": "memory mind brain",
        "dna": "dna science microscope",
        "heart": "heart pulse medical",
        "time": "time clock timelapse",
        "money": "money finance success",
        "food": "food cooking delicious",
        "exercise": "workout gym fitness",
        "music": "music concert sound",
        "technology": "technology futuristic digital",
        "ai": "artificial intelligence robot",
        "phone": "smartphone technology",
        "earth": "earth planet nature",
        "sun": "sunrise sunset golden",
        "water": "water flow liquid",
        "fire": "fire flame energy",
        "ancient": "ancient ruins history",
        "history": "historical architecture old",
        "city": "city skyline urban",
        "nature": "nature landscape forest",
        "animal": "wildlife animals nature",
        "human": "person silhouette people",
        "success": "success winner achievement",
        "habit": "morning routine productivity",
        "reading": "reading books library",
        "running": "running athlete sport",
        "meditation": "meditation peaceful calm",
    }
    
    # Check if any keyword matches the topic
    for kw, query in keyword_map.items():
        if kw in topic_lower:
            return query
    
    # Extract meaningful words from topic (skip common words)
    skip = {"the","a","an","is","are","was","were","be","been","have","has",
            "do","does","did","will","would","could","should","may","might",
            "this","that","these","those","for","with","from","about","into",
            "your","you","they","them","their","our","we","i","my","me",
            "how","why","what","when","where","who","which","if","but","and",
            "or","not","no","never","ever","just","only","also","than","then",
            "fact","facts","secret","truth","trick","hack","way","thing","things"}
    
    words = [w.strip(".,!?") for w in topic_lower.split() if w not in skip and len(w) > 3]
    query = " ".join(words[:3]) if words else niche
    
    # Fallback to niche if query is too short
    if len(query) < 4:
        query = random.choice(NICHE_KEYWORDS.get(niche, NICHE_KEYWORDS["default"]))
    
    return query


def download_pexels_video(topic: str, niche: str, pexels_key: str,
                        cache_dir: str = "assets/videos",
                        prebuilt_query: str = None) -> str | None:
    if not pexels_key or pexels_key.startswith("YOUR"):
        return None

    os.makedirs(cache_dir, exist_ok=True)
    query = prebuilt_query if prebuilt_query else extract_video_query(topic, niche)

    try:
        headers  = {"Authorization": pexels_key}
        r = requests.get("https://api.pexels.com/videos/search",
                        headers=headers,
                        params={"query": query, "per_page": 8,
                                "orientation": "portrait", "size": "medium"},
                        timeout=10)
        videos = r.json().get("videos", [])
        if not videos:
            return None

        video = random.choice(videos[:5])
        # Pick best portrait file
        best = None
        for vf in video.get("video_files", []):
            if vf.get("width", 0) < vf.get("height", 1):
                if best is None or vf.get("width", 0) > best.get("width", 0):
                    best = vf
        if not best:
            best = video["video_files"][0]

        url   = best["link"]
        fname = os.path.join(cache_dir, f"{video['id']}.mp4")

        if os.path.exists(fname):
            logger.info(f"📦 Using cached video: {fname}")
            return fname

        logger.info(f"⬇️  Downloading Pexels video: {query}")
        r2 = requests.get(url, timeout=30, stream=True)
        with open(fname, "wb") as f:
            for chunk in r2.iter_content(chunk_size=65536):
                f.write(chunk)
        logger.info(f"✅ Downloaded: {fname}")
        return fname

    except Exception as e:
        logger.warning(f"⚠️  Pexels failed: {e}")
        return None

# ── Animated gradient fallback ────────────────────────────────────────────────
def make_animated_bg_frame(t: float, niche: str) -> np.ndarray:
    """Animated gradient with floating particles — fallback if no Pexels."""
    pal   = PALETTES.get(niche, PALETTES["default"])
    acc   = pal["accent"]
    phase = t * 0.3

    img_arr = np.zeros((H, W, 3), dtype=np.uint8)
    ratios = np.linspace(0, 1, H)
    waves  = np.sin(ratios * math.pi * 3 + phase) * 0.08
    r_col  = np.clip(8  + ratios*18 + waves*30, 0, 255).astype(np.uint8)
    g_col  = np.clip(8  + ratios*8  + waves*15, 0, 255).astype(np.uint8)
    b_col  = np.clip(28 + ratios*40 + waves*40, 0, 255).astype(np.uint8)
    img_arr[:, :, 0] = r_col[:, None]
    img_arr[:, :, 1] = g_col[:, None]
    img_arr[:, :, 2] = b_col[:, None]
    img = Image.fromarray(img_arr, "RGB")
    draw = ImageDraw.Draw(img)

    # Floating particles
    rng = random.Random(42)
    for i in range(40):
        px = rng.randint(0, W)
        py = int((rng.randint(0, H) - t * 60 * rng.uniform(0.3,1.0)) % H)
        size = rng.randint(2, 8)
        alpha = int(abs(math.sin(t * rng.uniform(0.5,2) + i)) * 120 + 20)
        draw.ellipse([(px-size,py-size),(px+size,py+size)],
                    fill=(*acc, alpha))

    return np.array(img)

# ── Text rendering with animation ────────────────────────────────────────────
def draw_text_animated(img: Image.Image, text: str, progress: float,
                    y_center: int, acc: tuple, size: int = 85,
                    style: str = "slide"):
    """Word-by-word pop-in with scale + fade effect."""
    font = gfont(size, bold=True)

    aw = font.getbbox("A")
    cpl = max(5, (W-100) // max(1, aw[2]-aw[0]))
    lines = textwrap.fill(text, width=cpl).split("\n")
    bb = font.getbbox("Hg")
    lh = bb[3]-bb[1]+24
    total_h = lh * len(lines)
    y0 = y_center - total_h // 2

    words_per_line = [line.split() for line in lines]
    total_words = max(1, sum(len(wl) for wl in words_per_line))

    word_idx = 0
    y = y0
    for wl in words_per_line:
        # measure full line width for centering
        line_str = " ".join(wl)
        lb = font.getbbox(line_str)
        lw = lb[2] - lb[0]
        x = (W - lw) // 2

        for w in wl:
            # each word pops in at its own threshold
            threshold = word_idx / total_words
            local_p = max(0.0, min(1.0, (progress - threshold) * total_words * 0.6))
            word_idx += 1

            alpha = int(min(1.0, local_p * 2) * 255)
            if alpha == 0:
                wb = font.getbbox(w + " ")
                x += wb[2] - wb[0]
                continue

            # scale: starts at 1.4x, settles to 1.0
            scale = 1.0 + 0.4 * max(0.0, 1.0 - local_p * 2)
            render_size = max(10, int(size * scale))
            rfont = gfont(render_size, bold=True)

            wb_r = rfont.getbbox(w)
            rw = wb_r[2] - wb_r[0]
            rh = wb_r[3] - wb_r[1]

            # normal word advance uses base font
            wb_base = font.getbbox(w + " ")
            advance = wb_base[2] - wb_base[0]

            # center the scaled word on its normal position
            rx = x + (advance - rw) // 2
            ry = y + (lh - rh) // 2 - 4

            for ox, oy in [(-4,-4),(4,-4),(-4,4),(4,4),(0,-4),(0,4),(-4,0),(4,0)]:
                img_draw = ImageDraw.Draw(img, "RGBA")
                img_draw.text((rx+ox, ry+oy), w, font=rfont, fill=(0,0,0,alpha))
            ImageDraw.Draw(img, "RGBA").text((rx, ry), w, font=rfont, fill=(255,255,255,alpha))

            x += advance
        y += lh


def draw_subscribe_overlay(img: Image.Image, progress: float, acc: tuple):
    """Animated subscribe button that pulses in."""
    draw = ImageDraw.Draw(img, "RGBA")

    scale = min(1.0, progress * 2.5)
    alpha = int(scale * 255)

    # Background blur-like dark panel
    draw.rounded_rectangle([(60,H//2-280),(W-60,H//2+320)],
                        radius=40, fill=(0,0,0,int(alpha*0.7)))

    # 🔥 emoji
    ef = gfont(180, bold=True)
    eb = ef.getbbox("🔥")
    ew = eb[2]-eb[0]
    draw.text(((W-ew)//2, H//2-260), "🔥", font=ef, fill=(255,255,255,alpha))

    # SUBSCRIBE text
    sf = gfont(115, bold=True)
    sub = "SUBSCRIBE!"
    sb = sf.getbbox(sub)
    sw = sb[2]-sb[0]
    # Pulsing scale effect
    pulse = 1 + math.sin(progress * math.pi * 4) * 0.05 * scale
    draw.text(((W-sw)//2, H//2-20), sub, font=sf, fill=(*acc, alpha))

    # Red YT-style button
    btn_y1, btn_y2 = H//2+120, H//2+230
    draw.rounded_rectangle([(130,btn_y1),(W-130,btn_y2)],
                        radius=50, fill=(255,0,0,alpha))
    bf = gfont(58, bold=True)
    bt = "▶  TAP TO SUBSCRIBE"
    bb2 = bf.getbbox(bt)
    bw = bb2[2]-bb2[0]
    draw.text(((W-bw)//2, btn_y1+20), bt, font=bf, fill=(255,255,255,alpha))

    # Like + bell row
    lf = gfont(55, bold=True)
    lt = "👍 LIKE    🔔 BELL    ↗ SHARE"
    lb = lf.getbbox(lt)
    lw = lb[2]-lb[0]
    draw.text(((W-lw)//2, H//2+260), lt, font=lf, fill=(255,255,255,alpha))


def draw_top_bar(img: Image.Image, topic: str, acc: tuple, acc2: tuple):
    draw = ImageDraw.Draw(img, "RGBA")
    # Gradient top bar
    for y in range(100):
        a = int((1 - y/100) * 220)
        draw.line([(0,y),(W,y)], fill=(0,0,0,a))
    # Accent line
    draw.rectangle([(0,0),(W,6)], fill=acc)
    # Channel name
    wf = gfont(36, bold=True)
    draw.text((40, 16), "⚡ DAILY FACTS", font=wf, fill=(*acc2, 230))


def draw_bottom_bar(img: Image.Image, progress: float, acc: tuple, acc2: tuple):
    draw = ImageDraw.Draw(img, "RGBA")
    # Dark fade at bottom
    for y in range(160):
        a = int((y/160) * 200)
        draw.line([(0, H-160+y),(W, H-160+y)], fill=(0,0,0,a))
    # Progress bar
    draw.rectangle([(0,H-14),(W,H)], fill=(30,30,40))
    for x in range(int(W*progress)):
        t2 = x/W
        r = int(acc[0]+(acc2[0]-acc[0])*t2)
        g = int(acc[1]+(acc2[1]-acc[1])*t2)
        b = int(acc[2]+(acc2[2]-acc[2])*t2)
        draw.line([(x,H-14),(x,H)], fill=(r,g,b))

# ── TTS ───────────────────────────────────────────────────────────────────────
async def _tts(text, path, voice):
    await edge_tts.Communicate(text, voice, rate="+25%").save(path)

def gen_tts(text, path, voice="en-US-AriaNeural"):
    asyncio.run(_tts(text, path, voice))

# ── Main build ────────────────────────────────────────────────────────────────
def build_video(topic: str, script: str, niche: str,
                output_path: str, voice: str = "en-US-AriaNeural",
                pexels_key: str = "") -> str:

    logger.info(f"🎬 Building animated video: {topic}")
    pal  = PALETTES.get(niche, PALETTES["default"])
    acc  = pal["accent"]
    acc2 = pal["accent2"]

    # 1. TTS audio
    af = tempfile.mktemp(suffix=".mp3")
    gen_tts(script, af, voice)
    audio_clip = mp.AudioFileClip(af)
    total_dur  = audio_clip.duration
    audio_clip.close()
    logger.info(f"🎤 Audio: {total_dur:.1f}s")

    # 2. Parse script into scenes
    secs = [s.strip() for s in script.strip().split("\n\n") if s.strip()]
    if len(secs) < 2:
        secs = [s.strip() for s in script.strip().split("\n") if s.strip()]
    if not secs: secs = [script]

    n_secs    = len(secs)
    total_chars = max(1, sum(len(s) for s in secs))
    dur_per_sec = [(len(s)/total_chars)*total_dur for s in secs]
    dur_per_sec = [max(3.0, d) for d in dur_per_sec]

    # CTA gets extra 4 seconds
    if n_secs > 1:
        dur_per_sec[-1] = max(4.0, dur_per_sec[-1])

    # 3. Build each scene
    scene_clips = []
    cumulative  = 0.0

    for i, (text, dur) in enumerate(zip(secs, dur_per_sec)):
        is_hook = (i == 0)
        is_cta  = (i == n_secs - 1)
        scene_progress = (i + 1) / n_secs

        # Per-scene: pick background video matched to this scene's text
        scene_query = extract_video_query(text, niche)
        bg_path = download_pexels_video(topic, niche, pexels_key, prebuilt_query=scene_query) if pexels_key else None
        # Fallback to Pixabay if Pexels returned nothing
        if not bg_path:
            pixabay_key = getattr(__import__("config"), "PIXABAY_API_KEY", None)
            if pixabay_key:
                bg_path = download_pixabay_video(scene_query, pixabay_key)
        logger.info(f"🎥 Scene {i+1} bg: '{scene_query}'")

        use_bg = bool(bg_path)
        scene  = None

        if use_bg:
            # ── Stock video background ──────────────────────────────────────
            try:
                raw_bg = mp.VideoFileClip(bg_path, audio=False)
                # Loop if needed
                if raw_bg.duration < dur:
                    loops = math.ceil(dur / raw_bg.duration)
                    raw_bg = mp.concatenate_videoclips([raw_bg]*loops)
                raw_bg = raw_bg.subclip(0, dur)
                # Resize to fill 1080x1920
                raw_bg = raw_bg.resize(height=H)
                if raw_bg.w < W:
                    raw_bg = raw_bg.resize(width=W)
                # Center crop
                x_off = max(0, (raw_bg.w - W) // 2)
                y_off = max(0, (raw_bg.h - H) // 2)
                raw_bg = raw_bg.crop(x1=x_off, y1=y_off,
                                    x2=x_off+W, y2=y_off+H)

                # Dark overlay for text readability
                overlay_arr = np.zeros((H, W, 4), dtype=np.uint8)
                overlay_arr[:,:,3] = 160  # semi-transparent black
                overlay_clip = (mp.ImageClip(overlay_arr, ismask=False)
                                .set_duration(dur))

                # Animated text overlay (PIL frame by frame)
                n_frames = int(dur * FPS)
                text_frames = []
                for fi in range(n_frames):
                    ft = fi / n_frames
                    frame_img = Image.new("RGBA", (W, H), (0,0,0,0))

                    if is_cta:
                        y_pos = H//2 + 40
                        draw_text_animated(frame_img, text, ft, y_pos, acc, size=88)
                    else:
                        y_pos = H//2 if is_hook else H//2 + 40
                        draw_text_animated(frame_img, text, ft, y_pos, acc,
                                        size=105 if is_hook else 88)

                    text_frames.append(np.array(frame_img))

                text_arr = np.array(text_frames)
                text_clip = (mp.ImageSequenceClip(list(text_arr), fps=FPS)
                            .set_duration(dur))

                scene = mp.CompositeVideoClip([raw_bg, overlay_clip, text_clip],
                                            size=(W, H))
                raw_bg.close()

            except Exception as e:
                logger.warning(f"Scene {i+1} composite failed: {e}, using gradient fallback for this scene")
                use_bg = False  # only this scene falls back; bg_path stays intact for next scenes

        if not use_bg:
            # ── Animated gradient fallback ──────────────────────────────────
            n_frames = int(dur * FPS)
            frames   = []
            for fi in range(n_frames):
                ft = fi / FPS
                prog_in = fi / n_frames

                # Animated bg
                bg_arr = make_animated_bg_frame(ft, niche)
                img    = Image.fromarray(bg_arr).convert("RGBA")

                if is_cta:
                        y_pos = H//2 + 40
                        draw_text_animated(img, text, prog_in, y_pos, acc, size=88)
                else:
                    y_pos = H//2 if is_hook else H//2 + 40
                    draw_text_animated(img, text, prog_in, y_pos, acc,
                                      size=105 if is_hook else 88)

                frames.append(np.array(img.convert("RGB")))

            scene = (mp.ImageSequenceClip(frames, fps=FPS)
                     .set_duration(dur))

        # Cross-fade transition
        if i > 0:
            scene = scene.crossfadein(0.4)

        scene_clips.append(scene)
        cumulative += dur

    # 5. Concatenate scenes
    logger.info("🎞️  Concatenating scenes…")
    video = mp.concatenate_videoclips(scene_clips, method="compose")

    # 6. Add audio
    audio = mp.AudioFileClip(af)
    end   = min(video.duration, audio.duration)
    final = video.subclip(0, end).set_audio(audio.subclip(0, end))

    # 7. Export
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    logger.info("💾 Rendering final video…")
    final.write_videofile(
        output_path, fps=FPS, codec="libx264", audio_codec="aac",
        temp_audiofile=af.replace(".mp3","_tmp.m4a"),
        remove_temp=True, logger=None, threads=4,
        ffmpeg_params=["-crf","16","-preset","slow"]
    )

    try: os.unlink(af)
    except: pass

    logger.info(f"✅ Done → {output_path}")
    return output_path