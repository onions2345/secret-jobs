import datetime
from collections import Counter


def country_of(location):
    parts = [p.strip() for p in (location or "").split(",") if p.strip()]
    return parts[-1] if parts else "Other"


def _prompt(country, titles, cats):
    cat_list = ", ".join(cats) if cats else "various fields"
    sample = "; ".join(titles[:8])
    return f"""Write a fresh 2-3 sentence intro for a web page that lists UNLISTED job openings in
{country} — roles found on employers' own websites and small niche sites, NOT on the big job
boards. It currently spans categories like {cat_list}. Example roles right now: {sample}.
Tone: plain, useful, a little bit insider; not salesy, no emojis, no markdown. Plain text only."""


def update_blurbs(gem, jobs, countries_touched, pages):
    """Rewrite the intro for each country the crawler covered this run. Non-grounded,
    so it never touches the grounding budget."""
    today = datetime.date.today().isoformat()
    by_country = {}
    for j in jobs.values():
        by_country.setdefault(country_of(j.get("location")), []).append(j)

    for country in countries_touched:
        rows = by_country.get(country, [])
        if not rows:
            continue
        titles = [r.get("title", "") for r in rows]
        cats = [c for c, _ in Counter(r.get("category", "") for r in rows).most_common(5) if c]
        try:
            text = gem.plain(_prompt(country, titles, cats)).strip()
        except Exception:
            text = pages.get(country, {}).get("blurb", "")
        if text:
            pages[country] = {"blurb": text, "updated": today}
    return pages
