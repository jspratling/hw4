"""Search themes and chat personas (Problem 10).

When a shopper searches for a sport ("hockey hoodie") or a field of study ("School of
Management"), the website switches to a matching theme (banner art, colors, headline) and the
chat assistant talks like someone from that world: a coach for sports, a professional for a
school or major. Themes are detected from the shopper's words first, then from the search tags
of the products the agent showed.
"""

import json
import re
import sqlite3

from pydantic import BaseModel


class Theme(BaseModel):
    key: str            # e.g. "hockey", "management"
    kind: str           # "sport" or "field"
    label: str          # banner title, e.g. "Yale Hockey"
    persona: str        # who the chat sounds like, e.g. "Coach Riley"
    persona_role: str   # e.g. "hockey coach"
    voice: str          # one line telling the agent how to sound
    tagline: str        # banner line on the page
    scene: str          # which illustration the website draws


SPORTS: list[tuple[str, list[str], str, str]] = [
    # key, keywords, label, tagline
    ("football", ["football", "the game", "yale bowl", "gridiron", "harvard-yale", "harvard yale", "yale-harvard", "beat harvard"], "Yale Football",
     "Saturdays at the Bowl. Wear the blue."),
    ("hockey", ["hockey", "ice hockey", "rink"], "Yale Hockey", "Ingalls Rink energy, all season long."),
    ("field-hockey", ["field hockey"], "Yale Field Hockey", "Sticks up, Bulldogs."),
    ("basketball", ["basketball", "hoops"], "Yale Basketball", "Court-side ready."),
    ("baseball", ["baseball", "softball"], "Yale Baseball", "Spring days, big swings."),
    ("soccer", ["soccer"], "Yale Soccer", "On the pitch with the Bulldogs."),
    ("tennis", ["tennis"], "Yale Tennis", "Game, set, Yale."),
    ("squash", ["squash"], "Yale Squash", "A Yale tradition on the courts."),
    ("lacrosse", ["lacrosse"], "Yale Lacrosse", "Fast sticks, true blue."),
    ("crew", ["yale crew", "rowing", "regatta", "rower"], "Yale Crew", "Row hard. Row blue."),
    ("sailing", ["sailing", "sail"], "Yale Sailing", "Fair winds from New Haven."),
    ("swimming", ["swimming", "swim", "diving", "dive"], "Yale Swimming & Diving", "Make a splash for Yale."),
    ("track", ["track", "cross country", "running"], "Yale Track & Field", "Run with the Bulldogs."),
    ("volleyball", ["volleyball"], "Yale Volleyball", "Serve it up, Yale."),
    ("fencing", ["fencing"], "Yale Fencing", "En garde, Bulldogs."),
    ("golf", ["golf"], "Yale Golf", "Fairways in Yale blue."),
]

FIELDS: list[tuple[str, list[str], str, str, str, str, str]] = [
    # key, keywords, label, persona, role, voice, tagline
    ("management", ["school of management", "som", "business", "mba", "finance", "consulting", "management"],
     "Yale School of Management", "Morgan", "SOM alum and consultant",
     "Sound like a sharp, upbeat business professional: crisp, confident, a little boardroom polish "
     "(\"great investment piece\", \"interview-ready\").",
     "From the classroom to the boardroom."),
    ("law", ["law school", "yale law", "lawyer", "attorney", "legal"], "Yale Law School", "Jordan",
     "attorney and Yale Law alum",
     "Sound like a friendly attorney: precise and persuasive (\"the evidence is clear: this one's a keeper\").",
     "Make your case in Yale blue."),
    ("medicine", ["school of medicine", "medical", "medicine", "doctor", "pre-med", "premed", "physician"],
     "Yale School of Medicine", "Dr. Patel", "physician and Yale Med alum",
     "Sound like a warm, reassuring doctor: calm and caring, with a light touch of bedside manner.",
     "Comfort for long rounds and late labs."),
    ("nursing", ["nursing", "nurse"], "Yale School of Nursing", "Alex", "nurse practitioner",
     "Sound like a kind, practical nurse: caring and down-to-earth.",
     "Care runs in the family."),
    ("public-health", ["public health"], "Yale School of Public Health", "Sam", "public health researcher",
     "Sound like an encouraging public health researcher: community-minded and data-savvy.",
     "Healthier communities, one Bulldog at a time."),
    ("engineering", ["engineering", "engineer"], "Yale School of Engineering", "Taylor", "engineer",
     "Sound like an enthusiastic engineer: practical, precise, a little nerdy in a fun way.",
     "Built to last, designed in New Haven."),
    ("architecture", ["architecture", "architect"], "Yale School of Architecture", "Rowan", "architect",
     "Sound like a thoughtful architect: talk about lines, structure and craftsmanship.",
     "Structure, style and a little Gothic inspiration."),
    ("art", ["school of art", "art school", "artist", "painting"], "Yale School of Art", "Avery", "painter",
     "Sound like a creative artist: expressive, visual, loves color and texture.",
     "Wear your masterpiece."),
    ("music", ["school of music", "music", "musician", "orchestra"], "Yale School of Music", "Maestro Lee",
     "conductor", "Sound like a cheerful conductor: musical turns of phrase, upbeat tempo.",
     "In perfect harmony with Yale."),
    ("divinity", ["divinity"], "Yale Divinity School", "Reverend Hale", "chaplain",
     "Sound like a gentle, welcoming chaplain: warm, kind and thoughtful.", "Peace, quiet and Yale blue."),
    ("environment", ["forest school", "forestry", "environment", "environmental"], "The Forest School at Yale",
     "Robin", "forester and ecologist",
     "Sound like an outdoorsy forester: calm, nature-loving, a little poetic about trees.",
     "Rooted in New Haven since 1900."),
]

SPORT_VOICE = ("Sound like an encouraging Yale {role}: energetic, team-first, short pep-talk lines "
               "(\"let's get you game-ready\"), but still clear and helpful.")
COACH_NAMES = ["Coach Riley", "Coach Casey", "Coach Jamie", "Coach Drew"]


def _themes() -> list[tuple[list[str], Theme]]:
    found = []
    for i, (key, words, label, tagline) in enumerate(SPORTS):
        role = f"{label.replace('Yale ', '').lower()} coach"
        found.append((words, Theme(key=key, kind="sport", label=label, persona=COACH_NAMES[i % len(COACH_NAMES)],
                                   persona_role=role, voice=SPORT_VOICE.format(role=role),
                                   tagline=tagline, scene=f"sport-{key}")))
    for key, words, label, persona, role, voice, tagline in FIELDS:
        found.append((words, Theme(key=key, kind="field", label=label, persona=persona, persona_role=role,
                                   voice=voice, tagline=tagline, scene=f"field-{key}")))
    return found


ALL_THEMES = _themes()
THEMES_BY_KEY = {t.key: t for _, t in ALL_THEMES}


def _match_text(text: str) -> Theme | None:
    """Longest keyword wins, so "field hockey" beats "hockey" and "school of art" beats "art"."""
    text = f" {text.lower()} "
    best: tuple[int, Theme] | None = None
    for words, theme in ALL_THEMES:
        for w in words:
            if re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", text) and (best is None or len(w) > best[0]):
                best = (len(w), theme)
    return best[1] if best else None


def detect_theme(message: str, product_ids: list[str] | None = None,
                 conn: sqlite3.Connection | None = None) -> Theme | None:
    """Theme for a chat message: from the shopper's words, else from what most of the shown
    products have in common (their names and search tags)."""
    theme = _match_text(message)
    if theme or not product_ids or conn is None:
        return theme
    votes: dict[str, int] = {}
    for pid in product_ids:
        row = conn.execute("SELECT name, search_tags FROM catalogue WHERE product_id = ?", (pid,)).fetchone()
        if not row:
            continue
        t = _match_text(f"{row[0]} {' '.join(json.loads(row[1]))}")
        if t:
            votes[t.key] = votes.get(t.key, 0) + 1
    if votes:
        key, n = max(votes.items(), key=lambda kv: kv[1])
        if n * 2 >= len(product_ids):  # most of the cards share the theme
            return THEMES_BY_KEY[key]
    return None
