# Relational Leadership Studio  (@doer_brands)

Generates original **relational leadership** posts (3-slide carousel: Quote -> Try this today -> Reflect),
writes the caption + hashtags, queues them for your approval, and posts to Instagram on a schedule.

## How it keeps posts genuine, accurate and valuable
| Goal | How |
|---|---|
| **Genuine** | `data/voice.md` holds YOUR voice + true stories. You approve every post (default). |
| **Accurate** | Only ORIGINAL lines. No attributed quotes (no misquotes), no statistics/"studies show". A code gate (`quality.py`) rejects violations. |
| **Valuable** | Every post has a quote AND a concrete action for today AND a reflection question. |
| **Engaging** | Carousel (drives saves/shares), comment-prompt question, save/share CTA, 8 rotating pillars, alternating dark/white design. |
| **No repeats** | Similarity check against all prior posts; pillars rotate evenly. |

Pillars: Trust, Listening, Curiosity, Vulnerability, Accountability, Presence, Appreciation, Courageous Conversations.
Edit them in `config.yaml`.

## Lanes (what gets posted)
| Lane | Share | Themes | Look |
|---|---|---|---|
| Relational Leadership | 60% | Trust, Listening, Curiosity, Vulnerability, Accountability, Presence, Appreciation, Courageous Conversations | gold accent (dark) |
| Doer Brands | 40% | Bold, Empowered, Doer (be bold, be empowered, be a doer; the Man in the Arena) | red accent |
Change shares and wording in `config.yaml` (`lanes:`). Add your real stories to `data/voice_doer.md` (training, leadership, building the brand):
the generator may mention personal experiences ONLY if they are written there.

## Attributed quotes (only when 100% verified)
Original lines are the default. Real-person quotes are allowed ONLY through a human-verified lane:
the AI never supplies them from memory, and the system will not post one until you confirm it against the PRIMARY source
(the book/speech/transcript itself; quote sites like BrainyQuote/Goodreads don't count and are blocked).
```
python -m rl_studio.cli addquote --quote "..." --author "..." --source-title "Book" --source-detail "p. 42, 2nd ed." \
  --pillar Trust --practice "..." --question "..."
python -m rl_studio.cli verifyquote 0 --by Jason    # you must type YES after checking the source
python -m rl_studio.cli quotes                      # POSTABLE vs BLOCKED
```
Via GitHub (no terminal): run workflow **4 - Add an attributed quote** (adds it BLOCKED), then **5 - Verify** after you check the primary source. See `data/QUOTES.md`.
Verified quotes mix in at `verified_ratio` (config.yaml, default 20%) and show the author and source on the slide and in the caption.
The publish step re-checks verification and refuses to post anything that fails.

## Quick start (5 minutes, no accounts needed)
```
pip install -r requirements.txt
python -m rl_studio.cli make --n 7     # builds a week of posts (starter bank of 24 vetted lines works offline)
python -m rl_studio.cli preview        # open queue/index.html to review images + captions
python -m rl_studio.cli approve --all  # or approve ID / reject ID
python -m rl_studio.cli publish --dry-run
```
Add `ANTHROPIC_API_KEY` to `.env` to get unlimited fresh AI-written lines (generate 5 candidates -> quality gate ->
editor pass picks the best). Without a key it uses `data/quote_bank.json`; add your own lines there anytime.

## Connect Instagram (one-time)
1. Make sure the account is **Professional** (Instagram app: Settings > Account type and tools > Switch to professional; Creator or Business).
2. Create a Meta developer app (developers.facebook.com) with Instagram API / Instagram Graph API and the
   `instagram_business_basic` and `instagram_business_content_publish` permissions (Instagram Login method). For your own account you can stay in development mode as app admin.
3. Generate a long-lived access token and find your Instagram User ID (Graph API Explorer or the Instagram API setup page).
   Dashboard tokens last 60 days: run `python -m rl_studio.cli refresh-token` about every 50 days and update your secret.
4. Put `IG_USER_ID`, `IG_ACCESS_TOKEN` in `.env`. If you use Instagram Login tokens set `IG_API_HOST=graph.instagram.com`.
5. Instagram must fetch the image from a public URL. Easiest: push this folder to a public GitHub repo and set
   `PUBLIC_BASE_URL=https://raw.githubusercontent.com/<you>/<repo>/main/queue`.
6. Test: `python -m rl_studio.cli publish` (posts the next approved item).

Meta changes the developer UI/permissions often; check Meta's current "Content Publishing" docs if a step differs.
Limit: 100 API-published posts per 24h (you will use 1).

## Full automation (see SETUP_GITHUB.md for the no-Python route)
`.github/workflows/daily-post.yml` runs daily: tops up the queue, pushes images, publishes the next APPROVED post.
Add repo secrets `IG_USER_ID`, `IG_ACCESS_TOKEN`, `ANTHROPIC_API_KEY`.
Recommended routine: 10 minutes every Sunday: `make`, `preview`, `approve`. Once you fully trust it, set `AUTO_APPROVE=1`
for hands-off posting (posts then go live without review).

## Adding platforms later
`publish.py` is the only Instagram-specific piece. Add `publish_linkedin.py` / `publish_facebook.py` with the same
`publish(image_urls, caption)` shape and call it from `cmd_publish`. Slides are already 4:5 (works for LinkedIn/Facebook too).

## Files
`config.yaml` brand/pillars/hashtags | `data/voice.md` your voice | `data/quote_bank.json` vetted lines
`rl_studio/` generate, quality, render, caption, publish, cli | `queue/` generated posts | `tests/`
