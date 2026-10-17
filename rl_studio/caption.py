import random

from .common import lane_for

HOOK = {
    "Trust": "Trust is built in small moments.",
    "Listening": "Most people don't need advice. They need to be heard.",
    "Curiosity": "The best leaders stay curious about people.",
    "Vulnerability": "Going first makes it safe for everyone else.",
    "Accountability": "High standards and real care can live together.",
    "Presence": "Attention is the rarest gift a leader gives.",
    "Appreciation": "People do better work when they know it matters.",
    "Courageous Conversations": "Clarity is a form of kindness.",
    "Bold": "Bold is a decision, not a feeling.",
    "Empowered": "You have more say in your next step than you think.",
    "Doer": "Doers start before they feel ready.",
}


def attrib(post):
    if post.get('source') != 'verified':
        return ''
    return f"\n\u2014 {post['author']}, {post['source_title']}"


def build_caption(post, cfg):
    lane = lane_for(cfg, post["pillar"])
    h = lane["hashtags"]
    tags = list(h["core"]) + random.sample(h["rotating"], h["rotating_count"])
    return (
        f"{HOOK.get(post['pillar'], 'Relational leadership starts with people.')}\n\n"
        f"“{post['quote']}”{attrib(post)}\n\n"
        f"Try this today: {post['practice']}\n\n"
        f"{post['question']} Tell me in the comments.\n\n"
        f"Save this for your next 1:1 and send it to a leader you respect.\n"
        f"{lane['cta']}\n\n" + " ".join(tags)
    )
