"""Render 1080x1350 (4:5) Instagram carousel slides with Pillow.
Two themes: dark (bold) and white (clean / ink-friendly)."""
import glob
from pathlib import Path

from .common import lane_for
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
PAD = 100
THEMES = {
    "dark": dict(bg=(11, 11, 12), fg=(255, 255, 255), muted=(176, 176, 182), accent=(255, 196, 0)),
    "white": dict(bg=(255, 255, 255), fg=(12, 12, 14), muted=(88, 88, 96), accent=(196, 30, 30)),
}


def _font(patterns, size):
    for pat in patterns:
        for p in glob.glob(f"/usr/share/fonts/**/{pat}", recursive=True) + glob.glob(f"/usr/local/share/fonts/**/{pat}", recursive=True):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


SERIF = ["LiberationSerif-Bold.ttf", "DejaVuSerif-Bold.ttf", "*Serif*Bold*.ttf"]
SANS_B = ["LiberationSans-Bold.ttf", "DejaVuSans-Bold.ttf", "*Sans*Bold*.ttf"]
SANS = ["LiberationSans-Regular.ttf", "DejaVuSans.ttf", "*Sans*.ttf"]


def _wrap(d, text, font, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = f"{cur} {w}".strip()
        if d.textlength(t, font=font) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def _fit(d, text, patterns, max_size, min_size, box_w, box_h, spacing=1.25):
    for size in range(max_size, min_size - 1, -2):
        f = _font(patterns, size)
        lines = _wrap(d, text, f, box_w)
        if len(lines) * size * spacing <= box_h:
            return f, lines, size
    f = _font(patterns, min_size)
    return f, _wrap(d, text, f, box_w), min_size


def _frame(theme, label, idx, total, handle, accent=None):
    t = dict(THEMES[theme])
    if accent and theme == "dark":
        t["accent"] = tuple(accent)
    im = Image.new("RGB", (W, H), t["bg"])
    d = ImageDraw.Draw(im)
    d.rectangle([PAD, 96, PAD + 90, 104], fill=t["accent"])
    d.text((PAD, 124), label.upper(), font=_font(SANS_B, 34), fill=t["muted"])
    d.text((PAD, H - 120), handle, font=_font(SANS_B, 34), fill=t["fg"])
    if total > 1:  # progress dots
        for i in range(total):
            x = W - PAD - (total - i) * 34
            d.ellipse([x, H - 112, x + 16, H - 96], fill=t["accent"] if i == idx else t["muted"])
    return im, d, t


def _block(d, t, text, patterns, max_size, min_size, top, bottom, color=None, align_mid=True):
    box_w, box_h = W - 2 * PAD, bottom - top
    f, lines, size = _fit(d, text, patterns, max_size, min_size, box_w, box_h)
    lh = int(size * 1.25)
    y = top + (box_h - lh * len(lines)) // 2 if align_mid else top
    for ln in lines:
        d.text((PAD, y), ln, font=f, fill=color or t["fg"])
        y += lh


def render_post(post, cfg, theme, outdir):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    lane = lane_for(cfg, post["pillar"])
    handle, series, accent = cfg["brand"]["handle"], lane["series"], lane.get("accent_dark")
    carousel = cfg["posting"]["carousel"]
    total = 3 if carousel else 1
    paths = []

    im, d, t = _frame(theme, f"{series}  |  {post['pillar']}", 0, total, handle, accent)
    q = f"“{post['quote']}”"
    attr = post.get("source") == "verified"
    _block(d, t, q, SERIF, 100, 52, 220, H - 430 if attr else H - 220)
    if attr:
        d.text((PAD, H - 400), f"\u2014 {post['author']}", font=_font(SANS_B, 46), fill=t["accent"])
        d.text((PAD, H - 340), post["source_title"], font=_font(SANS, 34), fill=t["muted"])
    if carousel:
        d.text((W - PAD - 400, H - 200), "Swipe for the practice", font=_font(SANS_B, 36), fill=t["muted"])
    p = outdir / "slide_1.png"
    im.save(p)
    paths.append(p)

    if carousel:
        im, d, t = _frame(theme, f"{series}  |  Try this today", 1, total, handle, accent)
        _block(d, t, post["practice"], SANS_B, 58, 36, 220, H - 220)
        p = outdir / "slide_2.png"
        im.save(p)
        paths.append(p)

        im, d, t = _frame(theme, f"{series}  |  Reflect", 2, total, handle, accent)
        _block(d, t, post["question"], SERIF, 76, 44, 220, 820)
        d.text((PAD, 880), "Answer in the comments.", font=_font(SANS_B, 38), fill=t["accent"])
        ff = _font(SANS, 36)
        y2 = 940
        for ln in _wrap(d, lane.get("slide_footer", "Save this. Share it with someone who needs it."), ff, W - 2 * PAD):
            d.text((PAD, y2), ln, font=ff, fill=t["muted"])
            y2 += 48
        p = outdir / "slide_3.png"
        im.save(p)
        paths.append(p)
    return paths
