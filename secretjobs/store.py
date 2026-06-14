import json, hashlib, datetime
from pathlib import Path

STATE_DIR = Path("state")
JOBS_FILE = STATE_DIR / "jobs.json"


def _id(url):
    return hashlib.sha1(url.strip().lower().encode()).hexdigest()[:12]


def _today():
    return datetime.date.today().isoformat()


def load():
    STATE_DIR.mkdir(exist_ok=True)
    return json.loads(JOBS_FILE.read_text()) if JOBS_FILE.exists() else {}


def save(jobs):
    JOBS_FILE.write_text(json.dumps(jobs, indent=2, ensure_ascii=False))


def upsert(jobs, job, evidence_url):
    jid = _id(job["url"])
    today = _today()
    if jid in jobs:
        jobs[jid]["last_seen"] = today
        return jobs[jid], False
    rec = {
        "id": jid,
        "title": job.get("title", "").strip(),
        "company": job.get("company", "").strip(),
        "category": job.get("category", "").strip(),
        "location": job.get("location", "").strip(),
        "url": job["url"].strip(),
        "source_domain": job.get("source_domain", "").strip(),
        "summary": job.get("summary", "").strip(),
        "verified_unlisted": True,
        "checked_against": [],     # set by caller
        "evidence_url": evidence_url,
        "first_seen": today,
        "last_seen": today,
    }
    jobs[jid] = rec
    return rec, True


# ── per-country page blurbs (written by Gemini, persisted between runs) ──────
PAGES_FILE = STATE_DIR / "pages.json"


def load_pages():
    STATE_DIR.mkdir(exist_ok=True)
    return json.loads(PAGES_FILE.read_text()) if PAGES_FILE.exists() else {}


def save_pages(pages):
    PAGES_FILE.write_text(json.dumps(pages, indent=2, ensure_ascii=False))


# ── country -> continent cache (filled by geo.resolve) ──────────────────────
GEO_FILE = STATE_DIR / "geo.json"


def load_geo():
    STATE_DIR.mkdir(exist_ok=True)
    return json.loads(GEO_FILE.read_text()) if GEO_FILE.exists() else {}


def save_geo(geo):
    GEO_FILE.write_text(json.dumps(geo, indent=2, ensure_ascii=False))
