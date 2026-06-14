import os, sys, yaml, datetime
from pathlib import Path
from secretjobs.llm import Gemini
from secretjobs.budget import Budget
from secretjobs import discover as D, store as S, render as R, locations as L, pages as P, geo as G
from secretjobs import boards as B, freshness as F


def _read_key():
    key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not key:
        p = Path("key.txt")
        if p.exists():
            key = p.read_text().strip()
    if not key or key.upper().startswith("PASTE"):
        print("ERROR: set GEMINI_API_KEY (GitHub secret) or put your key in key.txt.")
        sys.exit(1)
    return key


def _rotate(items, by):
    if not items:
        return items
    return items[by % len(items):] + items[:by % len(items)]


def main():
    cfg = yaml.safe_load(open("config.yaml"))
    gem = Gemini(_read_key(), cfg["model"], cfg.get("temperature", 0.2))
    budget = Budget(cfg["max_grounded_calls_per_month"], cfg["max_grounded_calls_per_run"])
    boards = cfg.get("known_boards", [])
    jobs = S.load(); page_blurbs = S.load_pages(); geo = S.load_geo(); meta = S.load_meta()
    eff_boards = B.effective(boards, meta.get("discovered_boards", []))
    print(f"Grounded calls this month: {budget.data['grounded_calls']}/"
          f"{budget.max_per_month}  ({budget.remaining_month()} left)")

    places = L.expand(gem, cfg["start_location"], cfg.get("max_locations_per_run", 1))
    day = datetime.date.today().toordinal()
    cats = _rotate(cfg["categories"], day)[: cfg.get("max_categories_per_run", 10)]
    print("This run:", " | ".join(c["name"] for c in cats), "@", " -> ".join(places))

    # DISCOVER — one search per (category, place); big boards excluded by the search itself.
    added = 0
    for place in places:
        for cat in cats:
            if not budget.can_spend():
                print("Budget cap reached — stopping early."); break
            found = D.discover(gem, budget, cat["brief"], place, eff_boards)
            print(f"  {cat['name']} @ {place} -> {len(found)} found")
            city = place.split(",")[0].strip()
            for f in found:
                f["category"] = cat["name"]
                f["city"] = city
                rec, is_new = S.upsert(jobs, f, None)
                rec["category"] = cat["name"]
                rec["city"] = city
                rec["checked_against"] = ["excluded from major boards via search"]
                added += int(is_new)
        else:
            continue
        break

    # Gemini refreshes each covered country's intro (free, non-grounded)
    countries = {P.country_of(p) for p in places}
    page_blurbs = P.update_blurbs(gem, jobs, countries, page_blurbs)
    geo = G.resolve(gem, {P.country_of(j.get("location")) for j in jobs.values()}, geo)

    # Weekly: let the AI suggest new job boards to exclude (core list stays locked)
    meta = B.maybe_update(gem, budget, countries, meta,
                          cfg.get("boards_refresh_days", 7))

    # Occasionally re-check saved jobs; drop dead links / filled roles
    checked, removed = F.check(gem, jobs,
                               cfg.get("max_freshness_checks_per_run", 15),
                               cfg.get("freshness_ai", True))
    if checked:
        print(f"  freshness: re-checked {checked}, removed {removed} dead/closed")

    S.save(jobs); S.save_pages(page_blurbs); S.save_geo(geo); S.save_meta(meta)
    R.render(cfg, jobs, page_blurbs, geo)
    print(f"\nDone. +{added} new | -{removed} gone | {len(jobs)} total | "
          f"{budget.run_calls} searches this run.")


if __name__ == "__main__":
    main()
