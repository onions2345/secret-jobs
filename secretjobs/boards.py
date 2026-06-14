"""Weekly auto-update of the job-board exclusion list.
Your hand-written core list (config: known_boards) is ALWAYS kept and never
removed. About once a week the AI suggests big boards/aggregators for the
countries you currently cover, and any new ones are merged into a discovered
list (persisted in state). Core + discovered together drive the search filters."""
import datetime


def _today():
    return datetime.date.today()


def effective(core, discovered):
    """Core list (locked) + AI-discovered list, de-duplicated."""
    seen, out = set(), []
    for b in list(core) + list(discovered or []):
        b = (b or "").strip().lower()
        if b and b not in seen:
            seen.add(b); out.append(b)
    return out


def _prompt(countries):
    where = ", ".join(sorted(c for c in countries if c)) or "English-speaking countries"
    return (f"List the domain names of MAJOR job boards and large job aggregator websites "
            f"used in: {where}. Only big mainstream boards (the kind an employer posts to for "
            f"mass reach), not company career pages or niche/community sites. "
            f'Return ONLY a JSON array of bare domains, e.g. ["seek.com.au","indeed.com"].')


def maybe_update(gem, budget, countries, meta, refresh_days=7):
    """If it's been >= refresh_days since the last refresh, run ONE grounded search
    and merge any new domains into meta['discovered_boards']. Returns meta."""
    meta = meta or {}
    last = meta.get("boards_updated")
    if last:
        try:
            if (_today() - datetime.date.fromisoformat(last)).days < refresh_days:
                return meta                       # too soon, skip
        except ValueError:
            pass
    if not budget.can_spend():
        return meta                               # respect budget cap
    found = gem.parse_json(gem.grounded(_prompt(countries)), [])
    budget.record(1)
    disc = set(meta.get("discovered_boards", []))
    added = 0
    for d in found if isinstance(found, list) else []:
        d = (d or "").strip().lower().lstrip("www.")
        if "." in d and " " not in d and d not in disc:
            disc.add(d); added += 1
    meta["discovered_boards"] = sorted(disc)
    meta["boards_updated"] = _today().isoformat()
    print(f"  boards refreshed: +{added} new (now {len(disc)} discovered + core list)")
    return meta
