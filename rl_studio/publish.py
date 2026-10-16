"""Publish to Instagram via the official Instagram Graph API (Content Publishing).
Requires an Instagram Professional (Business/Creator) account. Images must be at
a public URL (PUBLIC_BASE_URL)."""
import os
import time

import requests


class PublishError(Exception):
    pass


def _base():
    host = os.environ.get("IG_API_HOST", "graph.facebook.com")
    return f"https://{host}/{os.environ.get('GRAPH_VERSION', 'v23.0')}"


def _call(method, path, **params):
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    r = requests.request(method, f"{_base()}/{path}", data=params if method == "POST" else None,
                         params=params if method == "GET" else None, timeout=60)
    try:
        j = r.json()
    except Exception:
        raise PublishError(f"HTTP {r.status_code}: {r.text[:300]}")
    if r.status_code >= 400 or "error" in j:
        raise PublishError(j.get("error", {}).get("message", str(j)))
    return j


def _wait(container_id, tries=30):
    for _ in range(tries):
        s = _call("GET", container_id, fields="status_code").get("status_code")
        if s == "FINISHED":
            return
        if s in ("ERROR", "EXPIRED"):
            raise PublishError(f"container {container_id} status {s}")
        time.sleep(3)
    raise PublishError(f"container {container_id} not ready in time")


def missing_config():
    return [k for k in ("IG_USER_ID", "IG_ACCESS_TOKEN", "PUBLIC_BASE_URL") if not os.environ.get(k)]


def publish(image_urls, caption):
    uid = os.environ["IG_USER_ID"]
    if len(image_urls) == 1:
        c = _call("POST", f"{uid}/media", image_url=image_urls[0], caption=caption)["id"]
    else:
        kids = []
        for u in image_urls:
            k = _call("POST", f"{uid}/media", image_url=u, is_carousel_item="true")["id"]
            _wait(k)
            kids.append(k)
        c = _call("POST", f"{uid}/media", media_type="CAROUSEL", children=",".join(kids), caption=caption)["id"]
    _wait(c)
    return _call("POST", f"{uid}/media_publish", creation_id=c)["id"]


def refresh_token():
    """Extend a long-lived Instagram-Login token by another 60 days (token must be >24h old, not expired)."""
    r = requests.get("https://graph.instagram.com/refresh_access_token",
                     params={"grant_type": "ig_refresh_token", "access_token": os.environ["IG_ACCESS_TOKEN"]}, timeout=60)
    j = r.json()
    if r.status_code >= 400 or "error" in j:
        raise PublishError(j.get("error", {}).get("message", str(j)))
    return j["access_token"], j.get("expires_in")
