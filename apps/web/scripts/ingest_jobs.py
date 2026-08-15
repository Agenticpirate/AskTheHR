#!/usr/bin/env python3
"""Convert remote-aug2026.jsonl into chunked public jobs JSON."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse

MASTER = Path("/workspace/jobs/remote-aug2026.jsonl")
NORM = Path("/workspace/jobs/normalized")
SUMMARY = Path("/workspace/jobs/summary.json")
OUT_DIR = Path("/workspace/seeker-board/public")
PRIMARY_CAP = 3000
TARGET = {
    "USA", "India", "Canada", "UK", "Australia",
    "Germany", "Netherlands", "Ireland", "Singapore", "France",
}


def norm_url(url: str) -> str:
    # Master file is already unique by URL. Only light-normalize.
    return (url or "").strip().rstrip("/")


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def richer(a: dict, b: dict) -> dict:
    def score(o: dict) -> tuple:
        desc = o.get("description") or ""
        return (
            1 if o.get("posted_at") else 0,
            1 if o.get("country") in TARGET else 0,
            1 if o.get("remote") else 0,
            len(desc),
            1 if o.get("city") else 0,
        )
    return a if score(a) >= score(b) else b


def clean(o: dict) -> dict | None:
    url = (o.get("url") or "").strip()
    title = (o.get("title") or "").strip()
    if not url or not title:
        return None
    country = (o.get("country") or "").strip()
    if country and country not in TARGET:
        country = ""
    posted = o.get("posted_at")
    if posted is not None:
        posted = str(posted).strip() or None
    desc = o.get("description") or ""
    if isinstance(desc, str):
        desc = " ".join(desc.split())
        if len(desc) > 900:
            desc = desc[:897].rstrip() + "..."
    else:
        desc = ""
    jid = str(o.get("id") or "").strip() or f"url:{abs(hash(url))}"
    return {
        "id": jid,
        "title": title[:200],
        "company": (o.get("company") or "").strip()[:120] or "Unknown company",
        "country": country,
        "state": (o.get("state") or "").strip()[:80],
        "city": (o.get("city") or "").strip()[:80],
        "remote": bool(o.get("remote")),
        "url": url,
        "posted_at": posted,
        "source": (o.get("source") or "unknown").strip()[:40],
        "description": desc,
    }


def rank(o: dict) -> tuple:
    posted = o.get("posted_at") or ""
    aug = 1 if str(posted).startswith("2026-08") else 0
    return (
        1 if o["remote"] else 0,
        aug,
        1 if o["country"] else 0,
        posted or "",
        1 if o["description"] else 0,
    )


def main() -> None:
    seen: dict[str, dict] = {}
    raw_n = 0
    paths: list[Path] = []
    if MASTER.exists():
        paths.append(MASTER)
    else:
        paths.extend(sorted(NORM.glob("*.jsonl")))
    for path in paths:
        for row in load_jsonl(path):
            raw_n += 1
            c = clean(row)
            if not c:
                continue
            key = norm_url(c["url"])
            if not key:
                continue
            seen[key] = richer(seen[key], c) if key in seen else c
    unique = list(seen.values())
    unique.sort(key=rank, reverse=True)
    primary = unique[:PRIMARY_CAP]
    rest = unique[PRIMARY_CAP:]
    summary = {}
    if SUMMARY.exists():
        try:
            summary = json.loads(SUMMARY.read_text())
        except json.JSONDecodeError:
            summary = {}
    total = int(summary.get("total") or len(unique))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    meta = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "month": "2026-08",
        "total": total,
        "shown": len(unique),
        "primary": len(primary),
        "more": len(rest) > 0,
        "more_count": len(rest),
        "by_remote": summary.get("by_remote"),
        "by_country": summary.get("by_country"),
        "by_source": summary.get("by_source"),
    }
    payload = {**meta, "jobs": primary}
    (OUT_DIR / "jobs.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    )
    if rest:
        (OUT_DIR / "jobs-more.json").write_text(
            json.dumps({"jobs": rest}, ensure_ascii=False, separators=(",", ":"))
        )
    remote = sum(1 for j in unique if j["remote"])
    print(f"raw={raw_n} unique={len(unique)} primary={len(primary)} more={len(rest)} remote={remote}")
    print("jobs.json", (OUT_DIR / "jobs.json").stat().st_size)
    more_p = OUT_DIR / "jobs-more.json"
    if more_p.exists():
        print("jobs-more.json", more_p.stat().st_size)

if __name__ == "__main__":
    main()
