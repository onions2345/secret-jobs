"""Occasionally re-check saved jobs and drop ones that are gone.
Cheap first: a plain HTTP fetch (free) removes dead 404/unreachable links.
Then, only for pages that still load, a cheap NON-grounded AI check asks
whether the role is still open. Bounded to a small batch per run so it
never stalls or runs up cost."""
import re, datetime, urllib.request, urllib.error

_UA = {"User-Agent": "Mozilla/5.0 (compatible; SecretJobsBot/1.0)"}
_TAGS = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
_STRIP = re.compile(r"<[^>]+>")
_CLOSED = re.compile(
    r"(position|vacancy|role|job|listing)\s+(has\s+)?(been\s+)?"
    r"(filled|closed|expired|no longer (available|accepting)|removed)"
    r"|applications? (are )?closed|this (job|position) is no longer",
    re.I)


def _today():
    return datetime.date.today().isoformat()


def _fetch(url, timeout=12):
    """Return (ok, text). ok=False means the link is dead/unreachable."""
    try:
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            if r.status >= 400:
                return False, ""
            raw = r.read(200_000).decode("utf-8", "ignore")
        clean = _STRIP.sub(" ", _TAGS.sub(" ", raw))
        return True, re.sub(r"\s+", " ", clean)[:4000]
    except (urllib.error.HTTPError, urllib.error.URLError, ValueError, OSError, Exception):
        return False, ""


def _ai_still_open(gem, job, text):
    """Cheap non-grounded check. Returns True (open), False (closed), or None (unsure)."""
    prompt = (f'A job page for "{job.get("title")}" at "{job.get("company")}". '
              f'Based ONLY on this page text, is this job vacancy STILL OPEN for applications?\n\n'
              f'PAGE:\n{text[:3500]}\n\n'
              f'Reply ONLY JSON: {{"open": true_or_false}}')
    res = gem.parse_json(gem.plain(prompt), {"open": None})
    return res.get("open")


def check(gem, jobs, batch=15, use_ai=True):
    """Re-check up to `batch` least-recently-checked jobs. Remove dead/closed.
    Returns (checked_count, removed_count)."""
    if not jobs:
        return 0, 0
    order = sorted(jobs.values(), key=lambda j: (j.get("last_checked") or "", j.get("first_seen") or ""))
    removed = 0
    checked = 0
    for job in order[:batch]:
        checked += 1
        ok, text = _fetch(job["url"])
        dead = False
        if not ok:
            dead = True                                  # 404 / unreachable (free)
        elif _CLOSED.search(text or ""):
            dead = True                                  # obvious "filled/closed" wording (free)
        elif use_ai and text:
            verdict = _ai_still_open(gem, job, text)     # cheap non-grounded AI check
            if verdict is False:
                dead = True
        if dead:
            jobs.pop(job["id"], None)
            removed += 1
        else:
            job["last_checked"] = _today()
    return checked, removed
