def _prompt(niche, city, region, country, signals, boards):
    sig = ", ".join(f'"{s}"' for s in signals)
    bad = ", ".join(boards)
    return f"""You are a job-hunting researcher. Use Google Search to find CURRENT openings
for "{niche}" in {city}, {region}, {country}.

Only return jobs posted on the EMPLOYER'S OWN website or a small niche/industry site
(pages that read like {sig}). STRICTLY EXCLUDE anything hosted on these aggregator or
job-board domains: {bad}. Never include a job whose link points to one of those domains.

Return ONLY a JSON array (no prose, no markdown fences). Each item:
{{
  "title": "...",
  "company": "...",
  "location": "{city}, {region}",
  "url": "https://exact-link-to-the-posting-or-careers-page",
  "source_domain": "the website's domain",
  "summary": "<=25 words IN YOUR OWN WORDS; do not copy the listing text"
}}
If nothing credible is found, return []."""


def discover(gem, budget, niche, loc, signals, boards):
    if not budget.can_spend():
        return []
    text = gem.grounded(_prompt(niche, loc["city"], loc["region"],
                                loc["country"], signals, boards))
    budget.record(1)
    items = gem.parse_json(text, [])
    out = []
    for it in items if isinstance(items, list) else []:
        url = (it.get("url") or "").strip()
        if not url.startswith("http"):
            continue
        if any(b in url for b in boards):   # belt and suspenders
            continue
        out.append(it)
    return out
