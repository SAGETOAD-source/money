"""
ai_visual_maker.py — AI Slideshow Video Generator
"What If" science/nature/body facts → Groq script → ComfyUI AI images + Pexels clips
→ Ken Burns → Christopher voice → mood music → YouTube + Instagram
"""

import os, sys, random, logging, math, time, requests, json, asyncio, textwrap
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
              logging.FileHandler("logs/ai_visual_bot.log", encoding="utf-8")])
logger = logging.getLogger(__name__)

client   = Groq(api_key=config.GROQ_API_KEY)
W, H, FPS = 1080, 1920, 30
COMFY_URL  = "http://127.0.0.1:8188"
CHECKPOINT = "sd15.safetensors"
PEXELS_KEY = config.PEXELS_API_KEY

os.makedirs("assets/ai_frames", exist_ok=True)
os.makedirs("assets/ai_videos", exist_ok=True)
os.makedirs("assets/music",     exist_ok=True)
os.makedirs("logs",             exist_ok=True)

# ── Viral "What If" / Science / Nature topic pool ────────────────────────────
TOPIC_POOL = [
    # What If scenarios
    "what if a human body grew 1 inch every second",
    "what if a snake bit a horse and how antivenom actually works",
    "what if you fell into a black hole right now",
    "what if the moon disappeared tonight",
    "what if humans never slept again",
    "what if you swallowed a tiny black hole",
    "what if all insects on earth vanished tomorrow",
    "what if your heart stopped for just 10 seconds",
    "what if you drank ocean water to survive",
    "what if gravity reversed for 5 minutes",
    "what if a wolf pack attacked a lion",
    "what if a crocodile fought a great white shark",
    "what if you were struck by lightning and survived",
    "what if you stopped eating for 30 days",
    "what if the sun turned off for one week",
    # Animal facts
    "how a mantis shrimp punch destroys its prey in milliseconds",
    "why bullet ants have the most painful sting on earth",
    "how a tardigrade survives in outer space with no protection",
    "why pistol shrimp can boil water with their claws",
    "how a blue ringed octopus kills with a bite you cannot feel",
    "why a hippopotamus is more dangerous than a lion",
    "how army ants build a living bridge with their own bodies",
    "why a platypus has venom powerful enough to cripple a human",
    # Human body facts
    "what happens to your body when you hold your breath too long",
    "why your brain keeps working for minutes after death",
    "what happens inside your body during a panic attack",
    "why some people can feel no pain and why it kills them",
    "what happens to your body in complete darkness for a week",
    "how the human body can survive without food for 70 days",
    # Science / space
    "why diamonds rain on Neptune and Uranus every day",
    "how a neutron star is so dense one teaspoon weighs a billion tons",
    "why time actually moves faster for people at higher altitudes",
    "how sound can literally kill a human being",
    "why water memory might be real and what it means",
    # Dark history / mystery
    "the real reason ancient egyptians used to remove the brain through the nose",
    "what happened to the crew of the Mary Celeste ghost ship",
    "why the Dyatlov Pass hikers died in the most mysterious way",
    "the dark truth about the Tunguska explosion that flattened 800 square miles",
    # Football / Cricket
    "the science behind why Ronaldo bicycle kick is physically impossible for normal humans",
    "what happens to a cricket ball at 160kmh that makes it nearly impossible to hit",
    "why IPL pitches are prepared 3 weeks in advance and what secret goes into them",
]

# ── Cinematic style per topic category ───────────────────────────────────────
def get_style(topic: str) -> str:
    t = topic.lower()
    if any(x in t for x in ["snake","shark","wolf","lion","crocodile","ant","octopus","mantis","shrimp","hippo","platypus","tardigrade"]):
        return "ultra detailed wildlife photography, dramatic lighting, macro lens, National Geographic style, 8k"
    if any(x in t for x in ["human body","heart","brain","panic","sleep","pain","breath","death"]):
        return "cinematic medical visualization, glowing anatomy, dark background, dramatic blue light, 8k"
    if any(x in t for x in ["space","black hole","moon","sun","neutron","neptune","galaxy","universe"]):
        return "deep space photography, dramatic cosmic lighting, nebula colors, ultra detailed 8k, NASA style"
    if any(x in t for x in ["history","egypt","ghost","dyatlov","tunguska","mary celeste"]):
        return "dark historical cinematic scene, dramatic shadows, moody atmosphere, period accurate, 8k"
    if any(x in t for x in ["football","ronaldo","cricket","ipl","pitch"]):
        return "epic sports photography, dramatic stadium lighting, crowd atmosphere, cinematic 8k"
    return "cinematic dramatic scene, ultra detailed, dramatic lighting, photorealistic, 8k"

# ── Pexels video download ─────────────────────────────────────────────────────
def download_pexels_clip(query: str, save_dir: str = "assets/ai_videos") -> str | None:
    os.makedirs(save_dir, exist_ok=True)
    try:
        r = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": PEXELS_KEY},
            params={"query": query, "per_page": 8, "orientation": "portrait"},
            timeout=15
        )
        vids = r.json().get("videos", [])
        random.shuffle(vids)
        for v in vids:
            files = sorted(v.get("video_files", []),
                           key=lambda x: x.get("width", 0), reverse=True)
            for f in files:
                if f.get("width", 0) >= 720:
                    url  = f["link"]
                    path = os.path.join(save_dir, f"{v['id']}.mp4")
                    if os.path.exists(path):
                        return path
                    resp = requests.get(url, timeout=30, stream=True)
                    if resp.status_code == 200:
                        with open(path, "wb") as out:
                            for chunk in resp.iter_content(65536):
                                out.write(chunk)
                        logger.info(f"🎥 Pexels clip: {path}")
                        return path
    except Exception as e:
        logger.warning(f"Pexels failed ({query}): {e}")
    return None

# ── ComfyUI image generation ──────────────────────────────────────────────────
def generate_image_comfyui(prompt: str, style: str, idx: int, output_dir: str) -> str | None:
    full_prompt = (
        f"{prompt}, {style}, masterpiece, best quality, ultra detailed, "
        "dramatic lighting, cinematic composition, photorealistic"
    )
    neg = ("blurry, low quality, cartoon, anime, text, watermark, "
           "ugly, deformed, duplicate, bad anatomy, worst quality")

    workflow = {
        "3": {"class_type": "KSampler", "inputs": {
            "seed": random.randint(1, 999999999), "steps": 28,
            "cfg": 7.5, "sampler_name": "euler_ancestral", "scheduler": "karras",
            "denoise": 1.0, "model": ["4",0], "positive": ["6",0],
            "negative": ["7",0], "latent_image": ["5",0]
        }},
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CHECKPOINT}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 512, "height": 912, "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": full_prompt, "clip": ["4",1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": neg, "clip": ["4",1]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3",0], "vae": ["4",2]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8",0], "filename_prefix": f"aiv_{idx:02d}"}}
    }

    try:
        r = requests.post(f"{COMFY_URL}/prompt", json={"prompt": workflow}, timeout=10)
        if r.status_code != 200:
            return None
        pid = r.json()["prompt_id"]
        logger.info(f"🎨 ComfyUI queued scene {idx+1} [{pid[:8]}]")

        for _ in range(200):
            time.sleep(1)
            hist = requests.get(f"{COMFY_URL}/history/{pid}", timeout=5).json()
            if pid in hist:
                for node_out in hist[pid].get("outputs", {}).values():
                    for img_info in node_out.get("images", []):
                        img_url = (f"{COMFY_URL}/view?filename={img_info['filename']}"
                                   f"&subfolder={img_info.get('subfolder','')}"
                                   f"&type={img_info.get('type','output')}")
                        img_r = requests.get(img_url, timeout=15)
                        if img_r.status_code == 200:
                            save_path = os.path.join(output_dir, f"scene_{idx:02d}.png")
                            with open(save_path, "wb") as f:
                                f.write(img_r.content)
                            logger.info(f"✅ AI image scene {idx+1} saved")
                            # Auto-delete from ComfyUI output
                            try:
                                comfy_out = os.path.join(
                                    "C:\\Users\\b2hkr\\OneDrive\\Desktop\\stable-diffusion"
                                    "\\stable-diffusion-webui-master\\stable-diffusion-webui-master"
                                    "\\ComfyUI\\output", img_info["filename"]
                                )
                                if os.path.exists(comfy_out):
                                    os.remove(comfy_out)
                            except: pass
                            return save_path
        logger.warning(f"⏱️  ComfyUI timeout scene {idx+1}")
        return None
    except Exception as e:
        logger.error(f"ComfyUI error: {e}")
        return None

# ── Ken Burns zoom ────────────────────────────────────────────────────────────
def apply_ken_burns(img_path: str, duration: float, zoom_in: bool = True) -> list:
    img = Image.open(img_path).convert("RGB")
    img = img.resize((W + 220, H + 320), Image.LANCZOS)
    iw, ih = img.size
    n = int(duration * FPS)
    frames = []
    for i in range(n):
        p    = i / n
        ease = p * p * (3 - 2 * p)
        zoom = (1.0 + 0.18 * ease) if zoom_in else (1.18 - 0.18 * ease)
        cw   = int(W / zoom)
        ch   = int(H / zoom)
        cx   = int((iw - cw) * 0.3 * (ease if zoom_in else 1 - ease))
        cy   = int((ih - ch) * 0.3 * (ease if zoom_in else 1 - ease))
        cx   = max(0, min(cx, iw - cw))
        cy   = max(0, min(cy, ih - ch))
        frames.append(np.array(img.crop((cx, cy, cx+cw, cy+ch)).resize((W, H), Image.LANCZOS)))
    return frames

# ── Pexels clip → frames ──────────────────────────────────────────────────────
def pexels_to_frames(clip_path: str, duration: float) -> list:
    """Convert a Pexels video clip to numpy frames for given duration."""
    try:
        raw = mp.VideoFileClip(clip_path, audio=False)
        if raw.duration < duration:
            loops = math.ceil(duration / raw.duration)
            raw   = mp.concatenate_videoclips([raw] * loops)
        raw  = raw.subclip(0, duration).resize(height=H)
        if raw.w < W:
            raw = raw.resize(width=W)
        xoff = max(0, (raw.w - W) // 2)
        yoff = max(0, (raw.h - H) // 2)
        raw  = raw.crop(x1=xoff, y1=yoff, x2=xoff+W, y2=yoff+H)
        n    = int(duration * FPS)
        frames = []
        for fi in range(n):
            try:
                frames.append(raw.get_frame(fi / FPS))
            except:
                frames.append(frames[-1] if frames else np.zeros((H,W,3), dtype=np.uint8))
        raw.close()
        return frames
    except Exception as e:
        logger.warning(f"Pexels→frames failed: {e}")
        return []

# ── Text overlay ──────────────────────────────────────────────────────────────
_FC = {}
def gfont(size, bold=False):
    k = (size, bold)
    if k in _FC: return _FC[k]
    paths = [
        "C:/Windows/Fonts/Impact.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    f = ImageFont.load_default()
    for p in paths:
        if os.path.exists(p):
            try: f = ImageFont.truetype(p, size); break
            except: pass
    _FC[k] = f
    return f

def overlay_text(frames: list, text: str,
                  is_hook: bool = False,
                  accent: tuple = (255, 220, 50)) -> list:
    result  = []
    n       = len(frames)
    font_h  = gfont(68, bold=True)
    font_b  = gfont(54, bold=True)
    font_sm = gfont(46, bold=False)
    text_up = text.upper()
    wrapped = textwrap.fill(text_up, width=20).split("\n")

    for i, frame in enumerate(frames):
        alpha = int(min(1.0, (i / n) * 4) * 255)
        img   = Image.fromarray(frame).convert("RGBA")
        draw  = ImageDraw.Draw(img, "RGBA")

        # Bottom gradient
        for y in range(H - 700, H):
            r = (y - (H - 700)) / 700
            draw.line([(0,y),(W,y)], fill=(0,0,0,int(r*r*220)))

        # Top gradient (for hook label)
        if is_hook:
            for y in range(0, 200):
                draw.line([(0,y),(W,y)], fill=(0,0,0,int((1-y/200)*160)))
            # HOOK badge
            badge_font = gfont(36, bold=True)
            badge_text = "⚡ WHAT IF..."
            bb = badge_font.getbbox(badge_text)
            bw = bb[2]-bb[0]
            bx = (W-bw)//2
            draw.rectangle([(bx-20,45),(bx+bw+20,95)], fill=(*accent,min(255,alpha)))
            for ox,oy in [(-2,-2),(2,-2),(-2,2),(2,2)]:
                draw.text((bx+ox,50+oy), badge_text, font=badge_font, fill=(0,0,0,min(255,alpha)))
            draw.text((bx,50), badge_text, font=badge_font, fill=(10,10,10,min(255,alpha)))

        # Accent bar
        bar_w = int(W * 0.12)
        bar_x = (W - bar_w) // 2
        lh    = 80
        total_h = len(wrapped) * lh
        start_y = H - total_h - 150
        draw.rectangle([(bar_x, start_y-22),(bar_x+bar_w, start_y-16)],
                        fill=(*accent, int(alpha*0.9)))

        for j, line in enumerate(wrapped):
            font  = font_h if j == 0 else (font_b if j == 1 else font_sm)
            color = accent if j == 0 else (255,255,255)
            bb    = font.getbbox(line)
            lw    = bb[2]-bb[0]
            lx    = (W-lw)//2
            ly    = start_y + j*lh
            for ox,oy in [(-4,-4),(4,-4),(-4,4),(4,4),(-5,0),(5,0),(0,-5),(0,5)]:
                draw.text((lx+ox,ly+oy), line, font=font, fill=(0,0,0,min(255,alpha)))
            draw.text((lx,ly), line, font=font, fill=(*color,alpha))

        # Watermark
        wm = gfont(30, bold=False)
        draw.text((W-330, H-85), "@anime_community447",
                  font=wm, fill=(200,200,200,int(alpha*0.45)))

        result.append(np.array(img.convert("RGB")))
    return result

# ── TTS ───────────────────────────────────────────────────────────────────────
async def _tts(text, path):
    import edge_tts
    await edge_tts.Communicate(text, "en-US-ChristopherNeural", rate="-8%").save(path)

def gen_tts(text, path):
    asyncio.run(_tts(text, path))

# ── Music ─────────────────────────────────────────────────────────────────────
MOOD_MUSIC = {
    "epic":        ["https://archive.org/download/epic-cinematic-music/epic_01.mp3"],
    "mysterious":  ["https://archive.org/download/mysterious-ambient/mysterious_01.mp3"],
    "dramatic":    ["https://archive.org/download/dramatic-tension/dramatic_01.mp3"],
    "nature":      ["https://archive.org/download/nature-ambient/nature_ambient.mp3"],
}

def download_music(mood: str) -> str | None:
    """Generate mood-matched music using pure Python numpy — always works."""
    import numpy as np
    import wave, subprocess
    os.makedirs("assets/music", exist_ok=True)
    wav_path = f"assets/music/{mood}_ai_ambient.wav"
    mp3_path = f"assets/music/{mood}_ai_ambient.mp3"

    if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 10000:
        logger.info(f"🎵 Music cached: {mp3_path}")
        return mp3_path

    logger.info(f"🎵 Generating {mood} music (numpy)...")

    SR  = 44100
    DUR = 65

    CHORDS = {
        "epic":          [130.8, 164.8, 196.0, 261.6],
        "mysterious":    [174.6, 207.7, 261.6, 349.2],
        "dramatic":      [146.8, 174.6, 220.0, 293.7],
        "inspirational": [261.6, 329.6, 392.0, 523.3],
        "nature":        [196.0, 246.9, 293.7, 392.0],
    }
    ECHO = {
        "epic":          (0.07, 0.42, 0.16, 0.22),
        "mysterious":    (0.12, 0.52, 0.24, 0.30),
        "dramatic":      (0.09, 0.48, 0.20, 0.26),
        "inspirational": (0.06, 0.38, 0.14, 0.20),
        "nature":        (0.10, 0.45, 0.22, 0.28),
    }

    freqs   = CHORDS.get(mood, CHORDS["epic"])
    weights = [0.50, 0.32, 0.22, 0.15]
    e1d, e1v, e2d, e2v = ECHO.get(mood, (0.08, 0.45, 0.18, 0.25))

    try:
        t = np.linspace(0, DUR, SR * DUR, endpoint=False)
        audio = np.zeros(len(t))
        for freq, w in zip(freqs, weights):
            audio += w * np.sin(2 * np.pi * freq * t)
            audio += (w * 0.08) * np.sin(2 * np.pi * (freq * 1.004) * t)
            audio += (w * 0.05) * np.sin(2 * np.pi * (freq * 0.997) * t)

        d1 = int(SR * e1d)
        e1 = np.zeros(len(audio)); e1[d1:] = audio[:-d1] * e1v
        audio = audio + e1

        d2 = int(SR * e2d)
        e2 = np.zeros(len(audio)); e2[d2:] = audio[:-d2] * e2v
        audio = audio + e2

        fi = int(SR * 5); fo = int(SR * 5)
        audio[:fi]  *= np.linspace(0, 1, fi)
        audio[-fo:] *= np.linspace(1, 0, fo)

        audio = audio / np.max(np.abs(audio)) * 0.80
        audio_int = (audio * 32767).astype(np.int16)

        with wave.open(wav_path, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SR)
            wf.writeframes(audio_int.tobytes())

        subprocess.run([
            "ffmpeg", "-i", wav_path, "-codec:a", "libmp3lame",
            "-qscale:a", "2", mp3_path, "-y", "-loglevel", "error"
        ], capture_output=True, timeout=30)

        try: os.remove(wav_path)
        except: pass

        if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 10000:
            logger.info(f"🎵 Music ready: {mp3_path} ({os.path.getsize(mp3_path)//1024}KB)")
            return mp3_path

        if os.path.exists(wav_path):
            return wav_path

    except Exception as e:
        logger.warning(f"Music generation failed: {e}")
    return None


# ── Groq: generate topic script ───────────────────────────────────────────────
def get_script(topic: str) -> dict:
    try:
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{
                "role": "system",
                "content": "You are a viral YouTube Shorts scriptwriter. Respond ONLY with valid JSON, no markdown."
            },{
                "role": "user",
                "content": f"""Write a VIRAL YouTube Shorts script about: "{topic}"

Make it sound like a mind-blowing documentary. Use specific real numbers, science, and facts.
Each scene should make the viewer MORE curious than the last.
Scene 3 = THE shocking revelation. Scene 5 = emotional/philosophical closer.

Return ONLY this JSON:
{{
  "title": "Viral title with shocking hook — max 60 chars",
  "hook": "Opening line that stops scrolling — max 12 words, start with 'What if' or shocking fact",
  "mood": "epic OR mysterious OR dramatic OR nature",
  "scenes": [
    {{"narration": "Specific shocking fact or 'what if' setup. Max 15 words.", "pexels_query": "relevant nature/science/animal video query", "ai_image_prompt": "ultra cinematic specific visual — what camera would actually see"}},
    {{"narration": "Build tension — add real number or comparison. Max 15 words.", "pexels_query": "...", "ai_image_prompt": "..."}},
    {{"narration": "THE REVELATION — mind-blowing specific fact. Max 15 words.", "pexels_query": "...", "ai_image_prompt": "..."}},
    {{"narration": "Unexpected twist or consequence. Max 15 words.", "pexels_query": "...", "ai_image_prompt": "..."}},
    {{"narration": "Philosophical closer — makes them think for hours. Max 15 words.", "pexels_query": "...", "ai_image_prompt": "..."}}
  ],
  "cta": "Ask their opinion OR challenge them. Max 10 words.",
  "hashtags": "#whatif #science #facts #nature #viral #shorts #mindblowing #biology #space #didyouknow"
}}"""
            }],
            max_tokens=900, temperature=0.95
        )
        raw = r.choices[0].message.content.strip().replace("```json","").replace("```","").strip()
        data = json.loads(raw)
        logger.info(f"✅ Script: {data.get('title')}")
        return data
    except Exception as e:
        logger.error(f"Groq script failed: {e}")
        return {
            "title": topic[:60],
            "hook": f"What if {topic}?",
            "mood": "epic",
            "scenes": [{"narration": topic, "pexels_query": topic, "ai_image_prompt": f"cinematic {topic}"}]*5,
            "cta": "Comment what you think below!",
            "hashtags": "#whatif #viral #shorts #science #facts"
        }

# ── Main builder ──────────────────────────────────────────────────────────────
def build_ai_visual_video(output_path: str, topic: str = None) -> tuple:
    if topic is None:
        topic = random.choice(TOPIC_POOL)
    logger.info(f"🎬 Topic: {topic}")

    script   = get_script(topic)
    title    = script["title"]
    hook     = script["hook"]
    scenes   = script["scenes"][:5]
    cta      = script.get("cta", "Follow for more!")
    mood     = script.get("mood", "epic")
    hashtags = script.get("hashtags", "#viral #shorts #whatif #science")
    style    = get_style(topic)

    frame_dir = f"assets/ai_frames/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(frame_dir, exist_ok=True)

    SCENE_DUR = 5.0   # 5 seconds per scene — more breathing room
    all_frames = []

    # ── Hook (AI image, 3s) ───────────────────────────────────────────────────
    logger.info("🎨 Generating hook AI image...")
    hook_img = generate_image_comfyui(scenes[0]["ai_image_prompt"], style, 0, frame_dir)
    if hook_img:
        frames = apply_ken_burns(hook_img, 3.0, zoom_in=True)
    else:
        clip = download_pexels_clip(scenes[0]["pexels_query"])
        frames = pexels_to_frames(clip, 3.0) if clip else _fallback_frames(hook, 3.0)
    all_frames.extend(overlay_text(frames, hook, is_hook=True))

    # ── Scenes — alternate AI image + Pexels clip ────────────────────────────
    for i, scene in enumerate(scenes):
        logger.info(f"🎬 Scene {i+1}/5: {scene['narration'][:50]}")
        use_ai = (i % 2 == 0)   # even scenes = AI image, odd = Pexels clip

        if use_ai:
            logger.info(f"  🎨 AI image...")
            img_path = generate_image_comfyui(scene["ai_image_prompt"], style, i+1, frame_dir)
            if img_path:
                frames = apply_ken_burns(img_path, SCENE_DUR, zoom_in=(i%4==0))
            else:
                clip = download_pexels_clip(scene["pexels_query"])
                frames = pexels_to_frames(clip, SCENE_DUR) if clip else _fallback_frames(scene["narration"], SCENE_DUR)
        else:
            logger.info(f"  🎥 Pexels clip: {scene['pexels_query']}")
            clip = download_pexels_clip(scene["pexels_query"])
            if clip:
                frames = pexels_to_frames(clip, SCENE_DUR)
            else:
                img_path = generate_image_comfyui(scene["ai_image_prompt"], style, i+1, frame_dir)
                frames = apply_ken_burns(img_path, SCENE_DUR) if img_path else _fallback_frames(scene["narration"], SCENE_DUR)

        if not frames:
            frames = _fallback_frames(scene["narration"], SCENE_DUR)
        all_frames.extend(overlay_text(frames, scene["narration"]))

    # ── CTA (Pexels clip, 2.5s) ───────────────────────────────────────────────
    cta_clip = download_pexels_clip(scenes[-1]["pexels_query"])
    cta_frames = pexels_to_frames(cta_clip, 2.5) if cta_clip else _fallback_frames(cta, 2.5)
    all_frames.extend(overlay_text(cta_frames, cta))

    # ── Build video ───────────────────────────────────────────────────────────
    logger.info(f"🎞️  Building video ({len(all_frames)} frames, {len(all_frames)/FPS:.1f}s)...")
    final = mp.ImageSequenceClip(all_frames, fps=FPS)

    # ── Voice ─────────────────────────────────────────────────────────────────
    script_text = f"{hook}. " + " ".join(s["narration"] for s in scenes) + f" {cta}"
    voice_path  = output_path.replace(".mp4", "_voice.mp3")
    try:
        gen_tts(script_text, voice_path)
        voice = mp.AudioFileClip(voice_path)
        logger.info(f"🎤 Voice: {voice.duration:.1f}s")

        # ── Music ─────────────────────────────────────────────────────────────
        music_file = download_music(mood)
        if music_file:
            music = mp.AudioFileClip(music_file)
            if music.duration < voice.duration:
                loops = math.ceil(voice.duration / music.duration)
                music = mp.concatenate_audioclips([music]*loops)
            music = music.subclip(0, voice.duration).audio_fadein(1.5).audio_fadeout(2.0).volumex(0.18)
            mixed = mp.CompositeAudioClip([music, voice])
            mixed_path = output_path.replace(".mp4","_audio.mp3")
            mixed.write_audiofile(mixed_path, fps=44100, verbose=False, logger=None)
            audio_clip = mp.AudioFileClip(mixed_path)
        else:
            audio_clip = voice

        vid_dur = audio_clip.duration + 0.5
        final   = final.set_duration(vid_dur) if final.duration < vid_dur else final.subclip(0, vid_dur)
        final   = final.set_audio(audio_clip)
    except Exception as e:
        logger.warning(f"Audio failed: {e}")

    # ── Export ────────────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    final.write_videofile(output_path, fps=FPS, codec="libx264",
                          audio=True, audio_codec="aac",
                          verbose=False, logger=None,
                          ffmpeg_params=["-crf","18","-preset","fast"])
    final.close()
    import gc; gc.collect(); time.sleep(2)
    for suf in ["_voice.mp3","_audio.mp3"]:
        try:
            f = output_path.replace(".mp4",suf)
            if os.path.exists(f): os.remove(f)
        except: pass
    # Cleanup ai_frames folder
    try:
        import shutil
        shutil.rmtree(frame_dir, ignore_errors=True)
    except: pass

    logger.info(f"✅ AI Visual saved: {output_path}")
    caption = f"{title}\n\n{hashtags}\n\n#shorts #viral #trending #youtube"
    return title, title, caption


def _fallback_frames(text: str, duration: float) -> list:
    n = int(duration * FPS)
    font = gfont(52, bold=True)
    frames = []
    for _ in range(n):
        img  = Image.new("RGB", (W,H), (8,8,18))
        draw = ImageDraw.Draw(img)
        for j, line in enumerate(textwrap.fill(text, width=26).split("\n")):
            bb = font.getbbox(line)
            lw = bb[2]-bb[0]
            draw.text(((W-lw)//2, H//2 - 60 + j*75), line, font=font, fill=(220,220,220))
        frames.append(np.array(img))
    return frames

# ── Scheduler ─────────────────────────────────────────────────────────────────
def make_and_post_ai_visual():
    import schedule
    logger.info("━"*50)
    logger.info("🤖 AI Visual pipeline starting...")
    topic = random.choice(TOPIC_POOL)
    ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
    out   = os.path.join(config.OUTPUT_DIR, f"ai_visual_{ts}.mp4")
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    title, body, caption = build_ai_visual_video(out, topic)
    from modules.uploader import upload_pov
    result = upload_pov(out, title, body, vars(config))
    yt  = (result.get("youtube") or {}).get("url","N/A")
    ig  = (result.get("instagram") or {}).get("url","N/A")
    logger.info(f"🎉 Done! YouTube: {yt} | Instagram: {ig}")
    try:
        if os.path.exists(out): os.remove(out)
    except: pass
    import gc; gc.collect()
    logger.info("━"*50)

def run_ai_visual_scheduler():
    import schedule
    os.makedirs("logs", exist_ok=True)
    logger.info("="*50)
    logger.info("  AI VISUAL BOT — 2 videos/day")
    logger.info("="*50)
    for t in ["11:00","18:00"]:
        schedule.every().day.at(t).do(make_and_post_ai_visual)
        logger.info(f"⏰ Scheduled at {t}")
    if "--now" in sys.argv:
        make_and_post_ai_visual()
    logger.info("🤖 AI Visual Bot running.")
    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    run_ai_visual_scheduler()