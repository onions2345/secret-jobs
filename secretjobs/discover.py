def _prompt(brief, location):
    return f"""You are an expert job-hunting agent with live Google Search. Find CURRENT job
openings that almost nobody sees because they are NOT on the big job boards — only on the
employer's own website, or on small niche, trade, community, or local sites.

Brief: {brief}
Location: {location}

Decide how to hunt: employer-careers pages ("join our team", "we're hiring", "current
vacancies"), trade/industry association job pages, local directories, specialist communities,
and any corner of the web where a small employer posts directly. Cast a wide net.

YOU decide what counts as a "big job board" and EXCLUDE it. Only return roles hosted on an
employer's own domain or a genuinely small/niche site.

Return ONLY a JSON array (no prose, no markdown). Each item:
{{
  "title": "...",
  "company": "...",
  "location": "{location}",
  "url": "https://exact-link-to-the-posting-or-careers-page",
  "source_domain": "the website's domain",
  "summary": "<=25 words IN YOUR OWN WORDS; never copy the listing text"
}}
Return as many credible, distinct roles as you can. If none, return []."""


def discover(gem, budget, brief, location, known_boards):
    if not budget.can_spend():
        return []
    text = gem.grounded(_prompt(brief, location))
    budget.record(1)
    items = gem.parse_json(text, [])
    out = []
    for it in items if isinstance(items, list) else []:
        url = (it.get("url") or "").strip()
        if not url.startswith("http"):
            continue
        if any(b in url for b in known_boards):
            continue
        out.append(it)
    return out
