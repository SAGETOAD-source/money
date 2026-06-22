"""
trend_finder.py  —  VIRAL topic edition
Picks topics that have proven viral potential, not just random trending searches.
"""

import random
import logging
from config import NICHES, TRENDS_REGION

logger = logging.getLogger(__name__)

# ── Viral topic formulas ──────────────────────────────────────────────────────
# These patterns consistently get millions of views on Shorts/Reels
VIRAL_FORMULAS = [
    "The {subject} secret nobody talks about",
    "Why you've been doing {subject} wrong your whole life",
    "Scientists just discovered this about {subject}",
    "{subject} fact that will change how you see everything",
    "The real reason {subject} works the way it does",
    "What happens to your {subject} after {event}",
    "This {subject} trick changed everything for me",
    "Nobody tells you this about {subject}",
    "The shocking truth about {subject}",
    "{number} things about {subject} that will blow your mind",
]

# ── High-performing niche subjects ───────────────────────────────────────────
NICHE_SUBJECTS = {
    "relatable": [
        ("being tired all the time", "doing nothing"),
        ("overthinking at 3am", "trying to sleep"),
        ("losing motivation", "starting something new"),
        ("feeling behind in life", "comparing yourself to others"),
        ("your phone", "destroying your attention span"),
        ("Sunday anxiety", "hitting before Monday"),
        ("not replying to texts", "even when you want to"),
        ("feeling empty", "having everything you wanted"),
        ("caring too much", "what others think"),
        ("self-sabotage", "when things are going well"),
        ("people pleasing", "making you miserable"),
        ("the 3pm energy crash", "hitting every day"),
    ],
    "psychology": [
        ("dark psychology", "being used on you daily"),
        ("manipulation tactics", "most people never notice"),
        ("your ego", "destroying your relationships"),
        ("gaslighting", "making you question reality"),
        ("the silent treatment", "being a form of abuse"),
        ("narcissists", "targeting empaths specifically"),
        ("your subconscious mind", "making 95% of your decisions"),
        ("trauma bonding", "feeling like love"),
        ("cognitive dissonance", "keeping you stuck"),
        ("the psychology of loneliness", "being an epidemic"),
        ("mirroring", "making anyone like you instantly"),
        ("confirmation bias", "controlling what you believe"),
    ],
    "relationships": [
        ("red flags", "people ignore because they're in love"),
        ("attachment styles", "ruining your relationships"),
        ("why people leave", "even good relationships"),
        ("love bombing", "being a manipulation tactic"),
        ("emotional unavailability", "being mistaken for mystery"),
        ("why you attract toxic people", "every time"),
        ("the anxious-avoidant trap", "keeping couples stuck"),
        ("why arguing about small things", "is never about small things"),
        ("breadcrumbing", "keeping you hooked"),
        ("why people cheat", "even when they're happy"),
        ("the pursuer-distancer dynamic", "destroying relationships"),
        ("why people stay", "in relationships that hurt them"),
    ],
    "mystery": [
        ("what governments hide", "in classified documents"),
        ("ancient civilizations", "being more advanced than us"),
        ("the Mandela Effect", "being something stranger than memory"),
        ("things that disappear", "in the Bermuda Triangle"),
        ("what happens to your consciousness", "when you die"),
        ("the simulation theory", "having real evidence"),
        ("secret societies", "still running the world"),
        ("ancient Egypt", "having technology we still can't explain"),
        ("the dark web", "containing things that will disturb you"),
        ("what NASA found on Mars", "and never told us"),
        ("sleep paralysis", "being more than just a dream"),
        ("the human brain", "having abilities we never use"),
    ],
    "movies": [
        ("Interstellar", "being about grief not space"),
        ("Joker", "showing what society does to broken people"),
        ("Shutter Island", "having an ending nobody talks about"),
        ("Inception", "having a detail that changes everything"),
        ("The Dark Knight", "having a hidden message about chaos"),
        ("Get Out", "being a metaphor most people missed"),
        ("Parasite", "having a second meaning hiding in plain sight"),
        ("Fight Club", "having a twist hiding in the first scene"),
        ("Midsommar", "actually being about a toxic relationship"),
        ("Us", "having a deeper meaning nobody explains"),
        ("Hereditary", "having hidden symbols in every scene"),
        ("Black Swan", "being about perfectionism destroying people"),
    ],
    "football": [
        ("Ronaldo's mental strength", "making him unstoppable"),
        ("Messi's brain", "processing football differently from everyone"),
        ("Neymar's dribbling technique", "being impossible to defend"),
        ("prime Ronaldo", "having an inhuman work ethic"),
        ("Messi's left foot", "being the most lethal weapon in football"),
        ("how Ronaldo trains", "while everyone else sleeps"),
        ("the psychology of penalty kicks", "breaking players mentally"),
        ("why prime Ronaldo was feared", "by every defender on earth"),
        ("Messi's vision", "seeing the game 3 seconds ahead"),
        ("the dark side of football", "nobody talks about"),
        ("how top footballers recover mentally", "after a loss"),
        ("the secret training habits", "of the world's best footballers"),
    ],
    "facts": [
        ("the human brain", "sleeping"),
        ("the ocean", "going 10km deep"),
        ("your heart", "beating 3 billion times in your life"),
        ("time", "passing faster at higher altitudes"),
        ("your body", "replacing itself every 7 years"),
    ],
}


def _build_topic(niche: str) -> str:
    """Build a viral-formula topic for a given niche."""
    subjects = NICHE_SUBJECTS.get(niche, NICHE_SUBJECTS["facts"])
    subject, context = random.choice(subjects)
    formula = random.choice(VIRAL_FORMULAS)

    # Fill formula
    topic = formula.format(
        subject=subject,
        event=context,
        number=random.choice([3, 5, 7, 10]),
    )
    return topic


def get_trending_topics(count: int = 5) -> list:
    """Return `count` viral-ready topic strings."""
    topics = []

    # Try real trends via Groq web search
    try:
        from groq import Groq
        from config import GROQ_API_KEY
        import json

        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{
                "role": "user",
                "content": (
                    "List 3 real trending topics RIGHT NOW on YouTube Shorts and Instagram Reels "
                    "in these niches: psychology, relationships, mystery, horror, movies, football. "
                    "Reply with ONLY a JSON array of 3 short topic strings, no explanation. "
                    "Example: [\"topic one\", \"topic two\", \"topic three\"]"
                )
            }],
            max_tokens=120,
            temperature=0.7,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown fences if present
        raw = raw.replace("```json", "").replace("```", "").strip()
        real = json.loads(raw)
        for trend in real[:2]:
            formula = random.choice(VIRAL_FORMULAS)
            topic = formula.format(subject=trend, event="going viral", number=5)
            topics.append(topic)
        logger.info(f"✅ Got real trends via Groq: {real[:2]}")
    except Exception as e:
        logger.warning(f"⚠️  Groq trend fetch failed: {e}")

    # Fill rest with formula-based viral topics
    while len(topics) < count:
        niche = random.choice(NICHES)
        topic = _build_topic(niche)
        if topic not in topics:
            topics.append(topic)

    return topics[:count]


def pick_niche_for_topic(topic: str) -> str:
    """Detect the best niche for a topic string."""
    t = topic.lower()
    keyword_map = {
        "relatable":     ["tired", "overthink", "anxious", "motivation", "phone", "attention", "empty", "behind", "people pleasing", "self-sabotage"],
        "psychology":    ["psychology", "manipulation", "narcissist", "gaslighting", "ego", "subconscious", "trauma", "cognitive", "bias", "mirror"],
        "relationships": ["relationship", "red flag", "attachment", "love", "leave", "cheat", "toxic", "partner", "dating", "breakup"],
        "mystery":       ["secret", "hidden", "government", "ancient", "conspiracy", "simulation", "paranormal", "bermuda", "nasa", "mystery"],
        "facts":         ["brain", "ocean", "heart", "body", "space", "time", "dna"],
        "football":      ["football", "ronaldo", "messi", "neymar", "soccer", "striker", "penalty", "footballer", "premier", "champions"],
    }
    for niche, keywords in keyword_map.items():
        if any(k in t for k in keywords):
            return niche
    return random.choice(NICHES)