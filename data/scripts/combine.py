#!/usr/bin/env python3
"""Combine normalized/*.jsonl into the site-ingest job files.

Idempotent: re-running overwrites outputs from a fresh glob of source JSONL.
Does not fetch APIs. Skips all.jsonl (output) and any non-jsonl files.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

ROOT = Path("/workspace/jobs")
NORMALIZED = ROOT / "normalized"
COMBINED_PATH = ROOT / "remote-aug2026.jsonl"
SUMMARY_PATH = ROOT / "summary.json"
ALL_PATH = NORMALIZED / "all.jsonl"
STATS_PATH = NORMALIZED / "stats.json"

SCHEMA_KEYS = (
    "id",
    "title",
    "company",
    "country",
    "state",
    "city",
    "remote",
    "url",
    "posted_at",
    "source",
    "description",
)

COUNTRY_ORDER = (
    "USA",
    "India",
    "Canada",
    "UK",
    "Australia",
    "Germany",
    "Netherlands",
    "Ireland",
    "Singapore",
    "France",
)


def canon_url(url: str) -> str:
    """Lowercase host, strip trailing slash, drop utm_* query params."""
    raw = (url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    host = parsed.netloc.lower()
    query = urlencode(
        [
            (k, v)
            for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if not k.lower().startswith("utm_")
        ]
    )
    path = parsed.path.rstrip("/")
    return urlunparse((parsed.scheme, host, path, parsed.params, query, parsed.fragment))


def as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def as_remote(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "remote", "y"}


def project(row: dict[str, Any]) -> dict[str, Any]:
    posted = row.get("posted_at")
    if posted is not None and not isinstance(posted, str):
        posted = str(posted)
    return {
        "id": as_str(row.get("id")),
        "title": as_str(row.get("title")),
        "company": as_str(row.get("company")),
        "country": as_str(row.get("country")),
        "state": as_str(row.get("state")),
        "city": as_str(row.get("city")),
        "remote": as_remote(row.get("remote")),
        "url": as_str(row.get("url")).strip(),
        "posted_at": posted if posted is not None else "",
        "source": as_str(row.get("source")),
        "description": as_str(row.get("description")),
    }


def source_files() -> list[Path]:
    files = sorted(
        p
        for p in NORMALIZED.glob("*.jsonl")
        if p.name != "all.jsonl" and p.is_file()
    )
    return files


def load_unique(files: list[Path]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    seen: dict[str, int] = {}
    jobs: list[dict[str, Any]] = []
    skipped_files: list[str] = []
    per_file: dict[str, dict[str, int]] = {}
    bad_lines = 0
    missing_url = 0
    dups = 0

    for path in files:
        stats = {"read": 0, "kept": 0, "dups": 0, "bad": 0, "no_url": 0}
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as exc:
            skipped_files.append(f"{path.name}: {exc}")
            continue
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                stats["bad"] += 1
                bad_lines += 1
                continue
            if not isinstance(obj, dict):
                stats["bad"] += 1
                bad_lines += 1
                continue
            stats["read"] += 1
            row = project(obj)
            key = canon_url(row["url"])
            if not key:
                stats["no_url"] += 1
                missing_url += 1
                continue
            if key in seen:
                stats["dups"] += 1
                dups += 1
                continue
            seen[key] = len(jobs)
            jobs.append(row)
            stats["kept"] += 1
        per_file[path.name] = stats

    meta = {
        "skipped_files": skipped_files,
        "per_file": per_file,
        "bad_lines": bad_lines,
        "missing_url": missing_url,
        "duplicates_dropped": dups,
        "input_files": [p.name for p in files],
    }
    return jobs, meta


def country_counts(jobs: list[dict[str, Any]]) -> dict[str, int]:
    raw = Counter(j["country"] for j in jobs)
    out: dict[str, int] = {}
    for name in COUNTRY_ORDER:
        if name in raw:
            out[name] = raw[name]
    extras = sorted(k for k in raw if k not in COUNTRY_ORDER and k != "")
    for name in extras:
        out[name] = raw[name]
    if "" in raw:
        out[""] = raw[""]
    return out


def write_jsonl(path: Path, jobs: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for job in jobs:
            fh.write(json.dumps(job, ensure_ascii=False, separators=(",", ":")))
            fh.write("\n")
    tmp.replace(path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    files = source_files()
    jobs, meta = load_unique(files)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    by_source = dict(sorted(Counter(j["source"] or "unknown" for j in jobs).items()))
    by_country = country_counts(jobs)
    remote_n = sum(1 for j in jobs if j["remote"])
    onsite_n = len(jobs) - remote_n
    by_remote = {"remote": remote_n, "onsite": onsite_n}

    summary = {
        "total": len(jobs),
        "by_source": by_source,
        "by_country": by_country,
        "by_remote": by_remote,
        "updated_at": now,
    }

    write_jsonl(COMBINED_PATH, jobs)
    write_jsonl(ALL_PATH, jobs)
    write_json(SUMMARY_PATH, summary)

    stats = {
        **summary,
        "input_files": meta["input_files"],
        "skipped_files": meta["skipped_files"],
        "per_file": meta["per_file"],
        "bad_lines": meta["bad_lines"],
        "missing_url": meta["missing_url"],
        "duplicates_dropped": meta["duplicates_dropped"],
        "outputs": {
            "combined": str(COMBINED_PATH),
            "all": str(ALL_PATH),
            "summary": str(SUMMARY_PATH),
        },
    }
    write_json(STATS_PATH, stats)

    print(f"total {summary['total']}")
    print("by_source", json.dumps(by_source, ensure_ascii=False))
    print("by_country", json.dumps(by_country, ensure_ascii=False))
    print("by_remote", json.dumps(by_remote, ensure_ascii=False))
    if meta["skipped_files"]:
        print("skipped", json.dumps(meta["skipped_files"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
