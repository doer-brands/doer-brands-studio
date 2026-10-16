"""rl: relational-leadership post studio.

  python -m rl_studio.cli make --n 7      generate + render posts into queue/ (status: pending)
  python -m rl_studio.cli preview         build queue/index.html contact sheet to review
  python -m rl_studio.cli list            show the queue
  python -m rl_studio.cli approve ID|--all
  python -m rl_studio.cli reject ID
  python -m rl_studio.cli publish [--dry-run]   post the next approved item
  python -m rl_studio.cli daily           top up queue if low, then publish next approved
"""
import argparse
import hashlib
import html
import os
import sys
from datetime import datetime, timezone

from . import publish as ig
from .caption import build_caption
from .common import QUEUE, ROOT, load_config, load_env, read_json, write_json
from .generate import make_posts
from .quality import check_verified
from .common import DATA
from .render import render_post


def _items():
    return sorted((read_json(p, None) for p in QUEUE.glob("*/post.json")), key=lambda x: x["id"])


def _save(item):
    write_json(QUEUE / item["id"] / "post.json", item)


def cmd_make(cfg, n):
    existing = len(_items())
    for i, post in enumerate(make_posts(cfg, n)):
        pid = datetime.now(timezone.utc).strftime("%Y%m%d") + "-" + hashlib.sha1(post["quote"].encode()).hexdigest()[:6]
        alt = cfg["brand"]["alternate_themes"]
        theme = ["dark", "white"][(existing + i) % 2] if alt else cfg["brand"]["default_theme"]
        slides = render_post(post, cfg, theme, QUEUE / pid)
        item = dict(id=pid, status="pending", theme=theme, post=post,
                    caption=build_caption(post, cfg), slides=[s.name for s in slides],
                    created=datetime.now(timezone.utc).isoformat())
        _save(item)
        print(f"made {pid} [{post['pillar']}] ({post['source']}): {post['quote']}")
    cmd_preview()


def cmd_preview():
    rows = []
    for it in _items():
        imgs = "".join(f'<img src="{it["id"]}/{s}" width="220">' for s in it["slides"])
        rows.append(f'<div style="margin:24px 0"><b>{it["id"]}</b> &middot; {it["status"]} &middot; {html.escape(it["post"]["pillar"])}<br>{imgs}'
                    f'<pre style="white-space:pre-wrap;font:14px sans-serif;max-width:700px">{html.escape(it["caption"])}</pre></div>')
    md = ["# Review queue\n", "Pending = needs your approval. Approved = will post. Use the **Approve posts** action.\n"]
    order = {"pending": 0, "approved": 1, "posted": 2, "rejected": 3}
    for it in sorted(_items(), key=lambda x: (order.get(x["status"], 9), x["id"])):
        if it["status"] in ("posted", "rejected"):
            continue
        imgs = " ".join(f'<img src="{it["id"]}/{sl}" width="240">' for sl in it["slides"])
        cap = "\n".join("> " + ln for ln in it["caption"].splitlines())
        md.append(f"## {it['status'].upper()} | `{it['id']}` | {it['post']['pillar']}\n\n{imgs}\n\n{cap}\n")
    (QUEUE / "REVIEW.md").write_text("\n".join(md))
    (QUEUE / "index.html").write_text("<body style='font-family:sans-serif;padding:24px'><h2>Review queue</h2>" + "".join(rows))
    print(f"preview: {QUEUE / 'index.html'}")


def cmd_list():
    for it in _items():
        print(f"{it['id']}  {it['status']:9}  {it['post']['pillar']:24}  {it['post']['quote'][:60]}")


def cmd_set(ident, status, all_=False):
    for it in _items():
        if all_ and it["status"] == "pending" or it["id"] == ident:
            it["status"] = status
            _save(it)
            print(f"{it['id']} -> {status}")


def cmd_publish(dry):
    auto = os.environ.get("AUTO_APPROVE") == "1"
    ok = {"approved"} | ({"pending"} if auto else set())
    nxt = next((i for i in _items() if i["status"] in ok), None)
    if not nxt:
        print("nothing approved to publish. Run `preview`, then `approve`.")
        return 4
    if nxt["post"].get("source") == "verified" and check_verified(nxt["post"]):
        print("BLOCKED: attributed quote failed verification:", check_verified(nxt["post"]))
        return 3
    base = os.environ.get("PUBLIC_BASE_URL", "https://example.invalid/queue").rstrip("/")
    urls = [f"{base}/{nxt['id']}/{s}" for s in nxt["slides"]]
    if dry:
        print("DRY RUN would publish:", *urls, "\n--- caption ---\n" + nxt["caption"], sep="\n")
        return 0
    miss = ig.missing_config()
    if miss:
        print("missing config:", ", ".join(miss), "(see README)")
        return 2
    try:
        media_id = ig.publish(urls, nxt["caption"])
    except ig.PublishError as e:
        print(f"publish failed: {e}")
        return 1
    nxt.update(status="posted", media_id=media_id, posted=datetime.now(timezone.utc).isoformat())
    _save(nxt)
    print(f"posted {nxt['id']} -> instagram media {media_id}")
    return 0


def main(argv=None):
    load_env()
    cfg = load_config()
    ap = argparse.ArgumentParser(prog="rl")
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make"); m.add_argument("--n", type=int, default=cfg["posting"]["queue_target"])
    sub.add_parser("preview"); sub.add_parser("list")
    a = sub.add_parser("approve"); a.add_argument("id", nargs="?"); a.add_argument("--all", action="store_true")
    r = sub.add_parser("reject"); r.add_argument("id")
    p = sub.add_parser("publish"); p.add_argument("--dry-run", action="store_true")
    sub.add_parser("daily"); sub.add_parser("topup"); sub.add_parser("check"); sub.add_parser("quotes");
    aq = sub.add_parser("addquote")
    for f in ("quote", "author", "source_title", "source_detail", "pillar", "practice", "question"):
        aq.add_argument(f"--{f.replace('_','-')}", required=True)
    aq.add_argument("--source-url", default="")
    vq = sub.add_parser("verifyquote"); vq.add_argument("index", type=int); vq.add_argument("--by", required=True)
    sub.add_parser("refresh-token")
    args = ap.parse_args(argv)
    QUEUE.mkdir(exist_ok=True)
    if args.cmd == "make": cmd_make(cfg, args.n)
    elif args.cmd == "preview": cmd_preview()
    elif args.cmd == "list": cmd_list()
    elif args.cmd == "approve": cmd_set(args.id, "approved", args.all)
    elif args.cmd == "reject": cmd_set(args.id, "rejected")
    elif args.cmd == "publish": return cmd_publish(args.dry_run)
    elif args.cmd == "addquote":
        vf = DATA / "verified_quotes.json"
        items = read_json(vf, [])
        items.append(dict(quote=args.quote, author=args.author, source_title=args.source_title,
                          source_detail=args.source_detail, source_url=args.source_url, pillar=args.pillar,
                          practice=args.practice, question=args.question, verified=False,
                          verified_primary_source=False, verified_by="", verified_date=""))
        write_json(vf, items)
        print(f"added as #{len(items)-1}, NOT postable until you run: verifyquote {len(items)-1} --by YOURNAME")
    elif args.cmd == "quotes":
        for i, v in enumerate(read_json(DATA / "verified_quotes.json", [])):
            probs = check_verified(v)
            print(f"#{i} {'POSTABLE' if not probs else 'BLOCKED '} {v['author']}: {v['quote'][:60]}  {probs or ''}")
    elif args.cmd == "verifyquote":
        vf = DATA / "verified_quotes.json"
        items = read_json(vf, [])
        v = items[args.index]
        print(f"QUOTE : {v['quote']}\nAUTHOR: {v['author']}\nSOURCE: {v['source_title']} ({v['source_detail']}) {v.get('source_url','')}")
        ans = input("Type YES only if you read this EXACT wording in the primary source (the book/speech/transcript itself, not a quote site): ")
        if ans.strip() == "YES":
            from datetime import date
            v.update(verified=True, verified_primary_source=True, verified_by=args.by, verified_date=str(date.today()))
            write_json(vf, items)
            print("verified:", check_verified(v) or "OK, postable")
        else:
            print("not verified")
    elif args.cmd == "check":
        miss = ig.missing_config()
        print("missing:", miss or "none")
        if not miss or miss == ["PUBLIC_BASE_URL"]:
            import requests
            h = os.environ.get("IG_API_HOST", "graph.facebook.com")
            r = requests.get(f"https://{h}/{os.environ.get('GRAPH_VERSION','v23.0')}/me",
                             params={"fields": "user_id,username", "access_token": os.environ["IG_ACCESS_TOKEN"]}, timeout=30)
            print("token check:", r.json().get("username") or r.json())
    elif args.cmd == "refresh-token":
        tok, exp = ig.refresh_token()
        print(f"NEW TOKEN (valid ~{int(exp)//86400} days). Put it in .env / GitHub secret IG_ACCESS_TOKEN:\n{tok}")
    elif args.cmd == "topup":
        ready = [i for i in _items() if i["status"] in ("pending", "approved")]
        need = cfg["posting"]["queue_target"] - len(ready)
        if need > 0:
            cmd_make(cfg, need)
    elif args.cmd == "daily":
        ready = [i for i in _items() if i["status"] in ("pending", "approved")]
        if len(ready) < cfg["posting"]["queue_target"]:
            cmd_make(cfg, cfg["posting"]["queue_target"] - len(ready))
        return cmd_publish(False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
