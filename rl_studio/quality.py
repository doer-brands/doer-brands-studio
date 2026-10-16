"""Quality gate. Everything must pass before a post enters the review queue.

Why these rules exist (genuine + accurate):
- No attributions: we only publish ORIGINAL lines, so there is no risk of
  misquoting or misattributing a famous person (a very common problem).
- No statistics/studies: invented numbers destroy credibility.
- No cliches/hype: keeps the voice real.
- Similarity check: no repeats or near-duplicates.
"""
import re
from difflib import SequenceMatcher

BANNED_PHRASES = [
    "hustle", "grindset", "crush it", "10x", "game changer", "game-changer",
    "synergy", "at the end of the day", "think outside the box", "unlock your potential",
    "journey of a thousand", "leaders are made", "be the change", "successful people",
    "studies show", "research shows", "science says", "according to",
]
ATTRIBUTION = re.compile(r"(^|\s)[-–—]\s*[A-Z][a-z]+(\s+[A-Z][a-z]+)?\s*$|\b(once said|famously said|wrote|as .{3,25} put it)\b", re.I)


def _norm(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower())


def check(post, history_quotes, similarity_limit=0.55):
    """Return a list of problems (empty list = pass)."""
    problems = []
    q = (post.get("quote") or "").strip()
    words = len(q.split())
    if not 5 <= words <= 30:
        problems.append(f"quote length {words} words (want 5-30)")
    if re.search(r"\d|%|#|@|http", q):
        problems.append("quote contains digits/hashtags/handles/links (no stats or clutter)")
    low = q.lower()
    for b in BANNED_PHRASES:
        if b in low:
            problems.append(f"banned phrase: {b}")
    if ATTRIBUTION.search(q):
        problems.append("looks attributed to someone; only original lines are allowed")
    if q.count("—") > 1:
        problems.append("too many em dashes")
    for field, lo, hi in (("practice", 8, 60), ("question", 4, 25)):
        n = len((post.get(field) or "").split())
        if not lo <= n <= hi:
            problems.append(f"{field} length {n} words (want {lo}-{hi})")
    if re.search(r"\d+\s?%|\b\d{2,}\s+(percent|times|studies)\b", post.get("practice", ""), re.I):
        problems.append("practice contains a statistic")
    for h in history_quotes:
        if SequenceMatcher(None, _norm(q), _norm(h)).ratio() >= similarity_limit:
            problems.append(f"too similar to existing quote: {h[:50]}...")
            break
    return problems


# ---- Verified attributed quotes -------------------------------------------------
# An attributed quote may ONLY post if a human checked it against a PRIMARY source
# (the book/speech/transcript itself) and recorded exactly where. The AI never
# supplies attributed quotes from memory.
AGGREGATORS = ("brainyquote", "goodreads.com/quotes", "azquotes", "quotefancy", "quotes.net",
               "wikiquote", "pinterest", "quotery", "inspirationalstories", "pinterest", "izquotes")
REQUIRED = ("quote", "author", "source_title", "source_detail", "pillar", "practice", "question",
            "verified_by", "verified_date")


def check_verified(v):
    """Return problems (empty = this attributed quote may be posted)."""
    problems = [f"missing {k}" for k in REQUIRED if not str(v.get(k) or "").strip()]
    if v.get("verified") is not True:
        problems.append("verified is not true")
    if v.get("verified_primary_source") is not True:
        problems.append("not confirmed against the primary source (verified_primary_source)")
    url = (v.get("source_url") or "").lower()
    if any(a in url for a in AGGREGATORS):
        problems.append("source_url is a quote aggregator, not a primary source")
    if len((v.get("quote") or "").split()) > 40:
        problems.append("quote too long (keep attributed quotes short, max 40 words)")
    return problems
