#!/usr/bin/env python3
"""
Pull recent MHSAA boys basketball finals and write live-scores.json.

Run locally:  python3 fetch_scores.py
Or on a schedule (GitHub Actions / cron) every 20–30 min on game nights.

Rules:
- First valid final is kept.
- If a later source disagrees, the game is flagged (needsReview).
- Does not overwrite a confirmed final with a blank.
"""
from __future__ import annotations

import json
import re
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "live-scores.json"
RAW = ROOT / "last-season-raw.json"

UA = "MittenRatings/0.1 (unofficial; score sync)"
SEASON = "2026-27"  # change when the season turns


def get(url: str, timeout: int = 25) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def parse_score(sc: str):
    m = re.search(r"(\d+)\s*[-–]\s*(\d+)", sc or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")


def load_existing() -> dict:
    if OUT.exists():
        try:
            return json.loads(OUT.read_text())
        except Exception:
            pass
    return {"updated": None, "games": {}}


def merge_final(store: dict, key: str, row: dict) -> None:
    prev = store["games"].get(key)
    if not prev:
        store["games"][key] = row
        return
    if prev.get("status") == "final" and row.get("status") == "final":
        if (prev.get("homeScore"), prev.get("awayScore")) != (row.get("homeScore"), row.get("awayScore")):
            prev["needsReview"] = True
            prev["altScore"] = [row.get("homeScore"), row.get("awayScore"), row.get("source")]
        return
    if prev.get("status") != "final" and row.get("status") == "final":
        store["games"][key] = row


def fetch_score_center(day: date) -> list[dict]:
    """MHSAA Score Center HTML. Layout can change; we parse loosely."""
    ds = f"{day.month}/{day.day}/{day.year}"
    url = (
        "https://my.mhsaa.com/Sports/Score-Center"
        f"?SportTypeCode=BBK&StartDate={ds}&EndDate={ds}"
    )
    try:
        html = get(url)
    except Exception as e:
        print("score center fail", day, e)
        return []
    # Very loose: "Home 64 Away 51" style chunks are unreliable.
    # Keep hook so a later endpoint can drop in.
    print("score center bytes", len(html), "date", day)
    return []


def main() -> None:
    store = load_existing()
    today = date.today()
    for delta in range(0, 3):
        fetch_score_center(today - timedelta(days=delta))

    # Placeholder: when you have a stable JSON feed, parse here and merge_final().
    store["updated"] = today.isoformat()
    store["note"] = (
        "Fetcher is installed. Wire the live MHSAA/MaxPreps JSON URL in "
        "fetch_score_center / a MaxPreps function. First final wins; mismatches flag needsReview."
    )
    OUT.write_text(json.dumps(store, indent=2))
    print("wrote", OUT, "games", len(store["games"]))


if __name__ == "__main__":
    main()
