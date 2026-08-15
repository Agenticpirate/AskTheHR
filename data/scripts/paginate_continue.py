#!/usr/bin/env python3
"""Continue Himalayas + Arbeitnow raw pagination. Never clobber existing files."""
from __future__ import annotations

import json
import os
import random
import re
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

RAW = "/workspace/jobs/raw"
LOG = os.path.join(RAW, "paginate_log.txt")
UA = "Mozilla/5.0 (compatible; JobCollector/1.0)"
HIMALAYA_URL = "https://himalayas.app/jobs/api"
ARBEIT_URL = "https://www.arbeitnow.com/api/job-board-api"
LIMIT = 20
P_OFFSET_BASE = 300  # himalayas_p1.json == offset 300
# ~10 minute time box; leave a few seconds to flush
DEADLINE = time.time() + 580
SLEEP_MIN = 0.20
SLEEP_MAX = 0.40

stats = {
    "himalayas_new_pages": 0,
    "himalayas_new_jobs": 0,
    "himalayas_highest_page": None,
    "himalayas_highest_offset": None,
    "himalayas_totalCount": None,
    "himalayas_more": None,
    "arbeitnow_new_pages": 0,
    "arbeitnow_new_jobs": 0,
    "arbeitnow_highest_page": None,
    "arbeitnow_more": None,
    "errors": [],
    "stop_reason": None,
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_line(line: str) -> None:
    with open(LOG, "a") as f:
        f.write(line + "\n")
        f.flush()


def save_exclusive_raw(path: str, raw: bytes) -> bool:
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        return False
    try:
        os.write(fd, raw)
    finally:
        os.close(fd)
    return True


def existing_pages(prefix: str, pattern: str) -> list[int]:
    nums = []
    rx = re.compile(pattern)
    for fn in os.listdir(RAW):
        m = rx.fullmatch(fn)
        if m:
            nums.append(int(m.group(1)))
    return sorted(nums)


def next_himalayas_page() -> int:
    ps = existing_pages("himalayas_p", r"himalayas_p(\d+)\.json")
    return (max(ps) + 1) if ps else 1


def next_arbeitnow_page() -> int:
    ps = existing_pages("arbeitnow_p", r"arbeitnow_p(\d+)\.json")
    return (max(ps) + 1) if ps else 13


def page_to_offset(page: int) -> int:
    return P_OFFSET_BASE + (page - 1) * LIMIT


def fetch(url: str) -> tuple[int, bytes]:
    req = Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urlopen(req, timeout=30) as resp:
            return resp.getcode(), resp.read()
    except HTTPError as e:
        body = b""
        try:
            body = e.read()
        except Exception:
            pass
        return e.code, body
    except URLError as e:
        return 0, str(e).encode()
    except Exception as e:
        return 0, str(e).encode()


def polite_sleep() -> None:
    time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))


def fetch_with_retry(url: str) -> tuple[int, bytes, bool]:
    """Return (status, body, should_stop). Retry once on 429 after 3s. Stop on repeated 403/429."""
    status, body = fetch(url)
    if status in (403, 429):
        if status == 429:
            time.sleep(3)
        else:
            time.sleep(3)
        status2, body2 = fetch(url)
        if status2 in (403, 429):
            return status2, body2, True
        return status2, body2, False
    return status, body, False


def paginate_arbeitnow() -> bool:
    """Return False if we should abort the whole run (rate limited)."""
    page = next_arbeitnow_page()
    log_line(f"# continue-session {now_iso()} arbeitnow start_page={page}")
    empty_streak = 0
    while time.time() < DEADLINE:
        path = os.path.join(RAW, f"arbeitnow_p{page}.json")
        if os.path.exists(path):
            page += 1
            continue
        url = f"{ARBEIT_URL}?page={page}"
        status, body, stop = fetch_with_retry(url)
        if stop:
            stats["errors"].append(f"arbeitnow page={page} repeated {status}")
            stats["stop_reason"] = f"repeated {status} on arbeitnow page {page}"
            log_line(f"arbeitnow\t{page}\t{status}\t0\tSTOP repeated block url={url}")
            return False
        n = 0
        extra = f"url={url}"
        if status == 200:
            try:
                data = json.loads(body.decode("utf-8", errors="replace"))
                jobs = data.get("data") if isinstance(data, dict) else None
                if isinstance(jobs, list):
                    n = len(jobs)
                links = data.get("links") if isinstance(data, dict) else {}
                extra += f" next={links.get('next') if isinstance(links, dict) else None}"
            except Exception as e:
                stats["errors"].append(f"arbeitnow page={page} json parse: {e}")
                extra += " parse_error=1"
        else:
            stats["errors"].append(f"arbeitnow page={page} HTTP {status}")
            extra += " error=1"

        if status == 200:
            if not save_exclusive_raw(path, body):
                log_line(f"arbeitnow\t{page}\t{status}\t{n}\tskipped exists {extra}")
                page += 1
                polite_sleep()
                continue
            stats["arbeitnow_new_pages"] += 1
            stats["arbeitnow_new_jobs"] += n
            stats["arbeitnow_highest_page"] = page
            log_line(f"arbeitnow\t{page}\t{status}\t{n}\t{extra} file=arbeitnow_p{page}.json")
            if n == 0:
                empty_streak += 1
                stats["arbeitnow_more"] = False
                log_line(f"# arbeitnow empty page={page} stopping arbeitnow")
                break
            empty_streak = 0
            # stop if next is null and we got a short page
            try:
                data = json.loads(body.decode("utf-8", errors="replace"))
                nxt = (data.get("links") or {}).get("next")
                if not nxt:
                    stats["arbeitnow_more"] = False
                    log_line(f"# arbeitnow no next link page={page}")
                    break
                stats["arbeitnow_more"] = True
            except Exception:
                pass
        else:
            log_line(f"arbeitnow\t{page}\t{status}\t{n}\t{extra}")
            if status in (403, 429):
                stats["stop_reason"] = f"arbeitnow HTTP {status}"
                return False
            # other errors: stop arbeitnow, continue himalayas
            break
        page += 1
        polite_sleep()
    return True


def paginate_himalayas() -> None:
    page = next_himalayas_page()
    log_line(
        f"# continue-session {now_iso()} himalayas start_page={page} "
        f"start_offset={page_to_offset(page)}"
    )
    while time.time() < DEADLINE:
        page = next_himalayas_page()  # always take current max+1 (other writers may race)
        path = os.path.join(RAW, f"himalayas_p{page}.json")
        if os.path.exists(path):
            continue
        offset = page_to_offset(page)
        url = f"{HIMALAYA_URL}?limit={LIMIT}&offset={offset}"
        status, body, stop = fetch_with_retry(url)
        if stop:
            stats["errors"].append(f"himalayas page={page} offset={offset} repeated {status}")
            stats["stop_reason"] = f"repeated {status} on himalayas page {page} offset {offset}"
            log_line(
                f"himalayas\t{page}\t{status}\t0\tSTOP repeated block offset={offset} url={url}"
            )
            return
        n = 0
        total = None
        extra = f"offset={offset} limit={LIMIT}"
        if status == 200:
            try:
                data = json.loads(body.decode("utf-8", errors="replace"))
                jobs = data.get("jobs") if isinstance(data, dict) else None
                if isinstance(jobs, list):
                    n = len(jobs)
                total = data.get("totalCount") if isinstance(data, dict) else None
                extra += f" totalCount={total}"
                stats["himalayas_totalCount"] = total
            except Exception as e:
                stats["errors"].append(f"himalayas page={page} json parse: {e}")
                extra += " parse_error=1"
        else:
            stats["errors"].append(f"himalayas page={page} offset={offset} HTTP {status}")
            extra += " error=1"

        if status == 200:
            if not save_exclusive_raw(path, body):
                log_line(f"himalayas\t{page}\t{status}\t{n}\tskipped exists {extra}")
                polite_sleep()
                continue
            stats["himalayas_new_pages"] += 1
            stats["himalayas_new_jobs"] += n
            stats["himalayas_highest_page"] = page
            stats["himalayas_highest_offset"] = offset
            log_line(f"himalayas\t{page}\t{status}\t{n}\t{extra} file=himalayas_p{page}.json")
            if n == 0:
                stats["himalayas_more"] = False
                stats["stop_reason"] = f"empty jobs at page {page} offset {offset}"
                log_line(f"# himalayas empty page={page} offset={offset} stopping")
                return
            if isinstance(total, int) and offset + n >= total:
                stats["himalayas_more"] = False
                stats["stop_reason"] = f"reached totalCount={total} at offset {offset}"
                log_line(f"# himalayas reached totalCount={total} offset={offset}")
                return
            stats["himalayas_more"] = True
        else:
            log_line(f"himalayas\t{page}\t{status}\t{n}\t{extra}")
            if status in (403, 429):
                stats["stop_reason"] = f"himalayas HTTP {status}"
                return
            # transient other error: retry next loop after sleep, but don't infinite-loop same page
            # skip this page number only if file was not written; try again once then move on
            polite_sleep()
            # try same page again later via next_himalayas_page
            continue
        polite_sleep()

    if stats["stop_reason"] is None:
        stats["stop_reason"] = "time-box reached"


def main() -> None:
    log_line(f"# paginate_continue start {now_iso()} deadline_s=580 ua={UA}")
    ok = paginate_arbeitnow()
    if ok and time.time() < DEADLINE:
        paginate_himalayas()
    elif not ok:
        pass
    else:
        stats["stop_reason"] = stats["stop_reason"] or "time-box reached after arbeitnow"

    # final snapshot of disk (includes other writers)
    ps = existing_pages("himalayas_p", r"himalayas_p(\d+)\.json")
    offs = existing_pages("himalayas_off", r"himalayas_off(\d+)\.json")
    aps = existing_pages("arbeitnow_p", r"arbeitnow_p(\d+)\.json")
    summary = {
        **stats,
        "disk_himalayas_p_max": max(ps) if ps else None,
        "disk_himalayas_p_count": len(ps),
        "disk_himalayas_off_max": max(offs) if offs else None,
        "disk_arbeitnow_p_max": max(aps) if aps else None,
        "finished_at": now_iso(),
    }
    log_line(f"# paginate_continue end {json.dumps(summary, separators=(',', ':'))}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
