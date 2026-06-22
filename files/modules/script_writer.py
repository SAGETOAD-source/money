"""
script_writer.py  —  GROQ edition (completely FREE)
Uses Groq's free API with Llama 3.3 70B model.
"""

import logging
import random
from groq import Groq
from config import GROQ_API_KEY, SCRIPT_WORD_COUNT

logger = logging.getLogger(__name__)
client = Groq(api_key=GROQ_API_KEY)

HOOK_TEMPLATES = [
    "This {topic} story will keep you up tonight.",
    "Nobody survived to tell this {topic} story. Almost.",
    "The {topic} truth is darker than you think.",
    "This {topic} fact will disturb you.",
    "What they found about {topic} was never made public.",
    "The real story behind {topic} will horrify you.",
    "You need to know what {topic} actually means.",
    "This is the {topic} secret they buried.",
    "Most people never recover after learning this about {topic}.",
    "The psychology behind {topic} is terrifying.",
]

SYSTEM_PROMPT = """You are the world's best viral short-form video script writer.
You write for these niches: horror true stories, dark psychology, relatable feelings, relationships, mystery.

NICHE-SPECIFIC STYLE:

FOR HORROR:
- Tell a TRUE-SOUNDING story with a real person, real place, real date
- Build dread slowly — end with something that makes them feel unsafe RIGHT NOW
- Example: "In 2019, a woman in Ohio heard knocking. It was 3am. Her husband was asleep."

FOR PSYCHOLOGY/RELATABLE:
- Make them feel seen and slightly uncomfortable. Use "you" constantly.

FOR MYSTERY:
- Make them feel like they know something others don't

FORMAT (follow exactly):
- Line 1: HOOK — one sentence that stops the scroll cold
- [blank line]
- Lines 2-3: TENSION — slow burn, build unease
- [blank line]
- Lines 4-5: REVEAL — the twist, the thing they can't unsee
- [blank line]
- Lines 6-7: IMPLICATION — make it personal, make it linger
- [blank line]
- Last line: CTA — "follow if this kept you up" or "like if you felt that"

STRICT RULES:
- Output ONLY spoken words, nothing else
- ALWAYS write the COMPLETE script — never stop early
- Max 8 words per sentence
- For horror: ALWAYS include a specific name, date, or location
- Sound like someone whispering in the dark
- Never say "fascinating" or "interesting" """


MOVIE_SYSTEM_PROMPT = """You are a cinematic narrator for viral YouTube Shorts about movies.
Your scripts explain the HIDDEN MEANING or PSYCHOLOGICAL DEPTH of famous films.
NOT a plot summary — the deeper truth most viewers missed.

STYLE: Dramatic, building like a movie trailer. Deep voice energy. Cinematic.

FORMAT (follow exactly):
- Line 1: HOOK — "Most people watched [movie] and missed everything."
- [blank line]
- Lines 2-3: SETUP — what everyone thinks the movie is about
- [blank line]
- Lines 4-5: THE REAL MEANING — the hidden theme, symbol, or psychological truth
- [blank line]
- Lines 6-7: THE PROOF — specific scene or detail that proves it
- [blank line]
- Last line: CTA — "watch it again. you'll never see it the same way."

STRICT RULES:
- Output ONLY spoken words, nothing else
- Max 8 words per sentence — punchy, cinematic
- ALWAYS complete all 8 sections — never stop early
- Never mention actual movie clips — describe emotions and themes only"""


def _write_movie_script(topic: str) -> str:
    prompt = f"""Write a {SCRIPT_WORD_COUNT}-word cinematic YouTube Shorts script.
Movie/Topic: "{topic}"
Explain the hidden meaning most people missed.
IMPORTANT: Write the COMPLETE script with ALL sections. Never stop early."""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": MOVIE_SYSTEM_PROMPT},
                {"role": "user",   "content": prompt}
            ],
            max_tokens=700,
            temperature=0.92,
        )
        script = response.choices[0].message.content.strip()
        logger.info(f"🎬 Movie script written ({len(script.split())} words)")
        return script
    except Exception as e:
        logger.error(f"❌ Groq error: {e}")
        return """Most people watched this film and missed everything.

They thought it was just a story.

It wasn't. It was a mirror.

Every scene hides a psychological truth.

The director buried it in plain sight.

Watch it again with this in mind.

Everything changes.

Follow for more hidden film meanings."""


def write_script(topic: str, niche: str) -> str:
    if niche == "movies":
        return _write_movie_script(topic)

    hook = random.choice(HOOK_TEMPLATES).replace("{topic}", topic)

    prompt = f"""Write a {SCRIPT_WORD_COUNT}-word viral YouTube Shorts script.
Topic: "{topic}"
Niche: {niche}
Opening hook: "{hook}"
{"This is a HORROR story — include a real-sounding name, specific date, and location. Make it genuinely terrifying." if niche == "horror" else "Make it so shocking viewers cannot stop watching."}
IMPORTANT: Write the COMPLETE script with ALL sections. Never stop early."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt}
            ],
            max_tokens=700,
            temperature=0.95 if niche == "horror" else 0.85,
        )
        script = response.choices[0].message.content.strip()
        logger.info(f"✅ Script written ({len(script.split())} words)")
        return script
    except Exception as e:
        logger.error(f"❌ Groq error: {e}")
        return """Nobody talks about this, but it will shock you.

Most people have no idea this is happening.

The truth they never taught you is disturbing.

94 percent of people get this completely wrong.

Here is what they buried from you.

This changes how you see everything forever.

Follow if this kept you up tonight."""


def write_title(topic: str) -> str:
    templates = [
        f"This {topic} will keep you up tonight",
        f"Nobody survived to explain {topic}. Almost.",
        f"The {topic} secret they buried",
        f"Most people don't know this about {topic}",
        f"{topic.title()} — the truth nobody tells you",
        f"The dark side of {topic} nobody talks about",
        f"What {topic} does to your mind is terrifying",
        f"This {topic} changed everything. Here's why.",
    ]
    return random.choice(templates)[:100]


def write_description(topic: str, hashtags: str) -> str:
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content":
                f"""Write a 2-sentence YouTube description for "{topic}".
First: what the video reveals (create curiosity).
Second: why they should subscribe.
End with: {hashtags}
Plain text only."""}],
            max_tokens=120,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return f"The shocking truth about {topic} nobody talks about. Subscribe for daily mind-blowing facts! {hashtags}"