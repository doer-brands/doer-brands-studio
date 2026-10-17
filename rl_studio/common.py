import json
import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
QUEUE = ROOT / "queue"


def load_env():
    """Minimal .env loader (no extra dependency)."""
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def load_config():
    return yaml.safe_load((ROOT / "config.yaml").read_text())


def read_json(path, default):
    path = Path(path)
    return json.loads(path.read_text()) if path.exists() else default


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False))


def lane_for(cfg, pillar):
    """Return the lane settings (series, cta, hashtags, ...) for a pillar name."""
    name = next((p.get("lane", "relational") for p in cfg["pillars"] if p["name"] == pillar), "relational")
    lane = dict(cfg["lanes"][name])
    lane["name"] = name
    return lane
