"""Quote generation: Claude (if API key present) + critic pass + quality gate,
with the vetted quote bank as an always-available fallback."""
import json
import os
import random
import re
from collections import Counter

from .common import DATA, lane_for, read_json, write_json
from .quality import check, check_verified

SYSTEM = """You write short, original relational-leadership posts for Instagram for Jason, \
the founder of a leadership speaking & coaching practice.

NON-NEGOTIABLE RULES
1. ORIGINAL lines only. Never quote, paraphrase, or attribute to any real person or book.
2. No statistics, studies, percentages, or claims of 'research shows'. No invented facts.
3. Practical and human: every post must contain something a reader can DO today.
4. Plain, warm, direct language. No hype, no hustle talk, no guru voice, no cliches.
5. Quote: 8-24 words, one idea, memorable rhythm, no hashtags/emojis.
6. NEVER write a quote attributed to a real person. Attributed quotes come only from a human-verified file.
6b. Practice: 1-3 sentences, a concrete action for today. Question: one short reflective question.
7. Follow the lane description given in the request (relational leadership OR the Doer Brands mission: be bold, be empowered, be a doer).
8. Personal experience: mention Jason's own training, business or life experiences ONLY if they appear in the voice notes. Otherwise write in a universal second-person voice. Never invent personal facts, results, or credentials.
Return ONLY valid JSON."""


def _client():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        import anthropic
        return anthropic.Anthropic(api_key=key)
    except Exception:
        return None


def _ask(client, system, user, max_tokens=2000):
    r = client.messages.create(
        model=os.environ.get("RL_MODEL", "claude-sonnet-5-5"),
        max_tokens=max_tokens, system=system,
        messages=[{"role": "user", "content": user}])
    text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
    m = re.search(r"(\[.*\]|\{.*\})", text, re.S)
    return json.loads(m.group(1))


def llm_candidates(client, pillar, recent, voice, lane_desc="", k=5):
    user = f"""Lane: {lane_desc}
Pillar: {pillar['name']} ({pillar['idea']})

Jason's voice and true stories (use only as flavor; never invent new personal facts):
{voice}

Recent posts to avoid echoing:
{json.dumps(recent[-15:])}

Write {k} distinct candidates. JSON array of objects with keys: quote, practice, question."""
    items = _ask(client, SYSTEM, user)
    for it in items:
        it["pillar"] = pillar["name"]
        it["source"] = "llm"
    return items


def llm_critic(client, cands):
    """Pick the best candidate on accuracy, originality, usefulness, engagement."""
    prompt = ("Pick the single best candidate for a relational-leadership Instagram post. Judge: "
              "truthful and defensible advice (no overclaiming), original (not a known quote), "
              "specific and useful, emotionally resonant, and not clichéd. "
              "Reply JSON: {\"index\": <int>, \"reason\": \"...\"}\n" + json.dumps(cands))
    try:
        r = _ask(client, "You are a rigorous editor of leadership content.", prompt, 500)
        return cands[int(r["index"])]
    except Exception:
        return cands[0]


def pick_pillars(cfg, history, n):
    """Balance lanes by their weights, then rotate evenly through each lane's pillars."""
    pil = {p["name"]: p.get("lane", "relational") for p in cfg["pillars"]}
    counts = Counter(h.get("pillar") for h in history)
    lane_counts = Counter(pil.get(h.get("pillar"), "relational") for h in history)
    out = []
    for i in range(n):
        total = sum(lane_counts.values()) + 1
        lane = max(cfg["lanes"], key=lambda l: cfg["lanes"][l]["weight"] * total - lane_counts[l] + random.random() * 0.01)
        names = [p for p, l in pil.items() if l == lane]
        pick = min(names, key=lambda x: (counts[x], random.random()))
        out.append(pick)
        counts[pick] += 1
        lane_counts[lane] += 1
    return out


def make_posts(cfg, n, source="auto"):
    history = read_json(DATA / "history.json", [])
    bank = read_json(DATA / "quote_bank.json", [])
    voice = "\n".join((DATA / f).read_text() for f in ("voice.md", "voice_doer.md") if (DATA / f).exists())
    used = [h["quote"] for h in history]
    limit = cfg["posting"]["similarity_limit"]
    client = _client() if source in ("auto", "llm") else None
    pillars = {p["name"]: p for p in cfg["pillars"]}
    out = []
    ratio = cfg["posting"].get("verified_ratio", 0.2)
    ver = [v for v in read_json(DATA / "verified_quotes.json", []) if not check_verified(v)]
    for name in pick_pillars(cfg, history, n):
        post = None
        fresh = [v for v in ver if v["quote"] not in used]
        if fresh and source != "bank-only" and random.random() < ratio:
            same = [v for v in fresh if v["pillar"] == name] or fresh
            v = random.choice(same)
            post = dict(v, source="verified", attribution=f"{v['author']}")
            name = v["pillar"]
        if post is None and client:
            try:
                good = [c for c in llm_candidates(client, pillars[name], used, voice, lane_for(cfg, name)["description"])
                        if not check(c, used, limit)]
                if good:
                    post = llm_critic(client, good)
            except Exception as e:  # network/parse problems: fall back, never crash
                print(f"[generate] LLM failed for {name}: {e}")
        if post is None and source != "llm":
            pool = [b for b in bank if b["pillar"] == name and not check(b, used, limit)]
            if not pool:
                pool = [b for b in bank if not check(b, used, limit)]
            if pool:
                post = dict(random.choice(pool), source="bank")
        if post is None:
            print(f"[generate] no fresh post for pillar {name}; add to data/quote_bank.json")
            continue
        used.append(post["quote"])
        history.append({"quote": post["quote"], "pillar": post["pillar"]})
        out.append(post)
    write_json(DATA / "history.json", history)
    return out
