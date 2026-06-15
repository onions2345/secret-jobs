# Big boards to exclude with negative search filters (Google strips them BEFORE
# results reach the model — so no second "verify" search is needed).
def _neg_filters(boards):
    return " ".join(f"-site:{b}" for b in boards)


def _prompt(brief, location, boards):
    neg = _neg_filters(boards)
    return f"""You are a job-hunting agent with live Google Search. Find CURRENT job openings
for: {brief}
Location: {location}

Run searches that EXCLUDE the big job boards using negative site filters, e.g.:
  "we are hiring" OR "careers" OR "current vacancies" {brief} {location} {neg}
Strongly prefer roles POSTED OR UPDATED IN THE LAST 14 DAYS — fresh, currently-open vacancies.
Only keep roles hosted on an employer's OWN website or a small niche/trade/community site.
Because the big boards are filtered out of the search itself, everything you find is
already off-market — no need to second-guess it.

Return ONLY a JSON array (no prose, no markdown). Each item:
{{
  "title": "...",
  "company": "...",
  "location": "{location}",
  "url": "https://direct-link-to-the-posting-or-careers-page",
  "source_domain": "the website's domain",
  "summary": "<=25 words IN YOUR OWN WORDS; never copy the listing text"
}}
Aim to return as MANY genuinely off-market roles as you can find — up to 20 per search.
Only include a job if you are confident the URL is real. If none, return []."""


def discover(gem, budget, brief, location, boards):
    """One grounded search per (category, location). No per-job verification."""
    if not budget.can_spend():
        return []
    text = gem.grounded(_prompt(brief, location, boards))
    budget.record(1)
    items = gem.parse_json(text, [])
    out = []
    for it in items if isinstance(items, list) else []:
        url = (it.get("url") or "").strip()
        if not url.startswith("http"):
            continue
        if any(b in url for b in boards):     # safety net: drop any board URL that slipped through
            continue
        out.append(it)
    return out
