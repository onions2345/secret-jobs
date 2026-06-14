import os, sys, yaml, datetime
from pathlib import Path
from secretjobs.llm import Gemini
from secretjobs.budget import Budget
from secretjobs import discover as D, verify as V, store as S, render as R, locations as L, pages as P, geo as G


def _read_key():
    key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not key:
        p = Path("key.txt")
        if p.exists():
            key = p.read_text().strip()
    if not key or key.upper().startswith("PASTE"):
        print("ERROR: open key.txt and paste your Google AI key into it "
              "(replace the placeholder text), then run this again.")
        sys.exit(1)
    return key


def _rotate(items, by):
    """Rotate a list so coverage is fair across runs (different start each day)."""
    if not items:
        return items
    k = by % len(items)
    return items[k:] + items[:k]


def main():
    cfg = yaml.safe_load(open("config.yaml"))
    key = _read_key()

    gem = Gemini(key, cfg["model"], cfg.get("temperature", 0.3))
    budget = Budget(cfg["max_grounded_calls_per_month"], cfg["max_grounded_calls_per_run"])
    known = cfg.get("known_boards", [])
    jobs = S.load()
    page_blurbs = S.load_pages()
    geo = S.load_geo()
    print(f"Grounded calls this month: {budget.data['grounded_calls']}/"
          f"{budget.max_per_month}  ({budget.remaining_month()} left)")

    # AI decides which places to cover, outward from the start.
    places = L.expand(gem, cfg["start_location"], cfg.get("max_locations_per_run", 1))

    # Rotate categories by day so all get covered over time within budget.
    day = datetime.date.today().toordinal()
    cats = _rotate(cfg["categories"], day)[: cfg.get("max_categories_per_run", 4)]
    print("Coverage this run:", " | ".join(c["name"] for c in cats),
          "@", " -> ".join(places))

    # 1) DISCOVER (AI casts a wide net per category; AI excludes the big boards)
    candidates = []
    for place in places:
        for cat in cats:
            if not budget.can_spend():
                print("Budget cap reached during discovery — stopping early.")
                break
            found = D.discover(gem, budget, cat["brief"], place, known)
            for f in found:
                f["category"] = cat["name"]
            print(f"  discover [{cat['name']} @ {place}] -> {len(found)}")
            candidates.extend(found)
        else:
            continue
        break

    # de-dupe by url; skip already-stored
    seen, queue = set(), []
    for c in candidates:
        u = (c.get("url") or "").strip().lower()
        if u and u not in seen:
            seen.add(u)
            queue.append(c)
    queue = queue[: cfg["max_candidates_to_verify_per_run"]]

    # 2) VERIFY (AI judges whether each is on a mainstream board)
    added = 0
    for c in queue:
        if not budget.can_spend():
            print("Budget cap reached during verification — stopping early.")
            break
        secret, board, evidence = V.is_secret(gem, budget, c)
        if secret is None:
            break
        if secret:
            rec, is_new = S.upsert(jobs, c, evidence)
            rec["checked_against"] = ["mainstream job boards (AI-judged)"]
            added += int(is_new)
            print(f"    KEEP  [{c.get('category')}] {c.get('title')} @ {c.get('company')}")
        else:
            print(f"    DROP  {c.get('title')} @ {c.get('company')}  (on {board or 'a board'})")

    # 3) Gemini refreshes the intro for each country covered this run (free / non-grounded)
    countries = {P.country_of(p) for p in places}
    page_blurbs = P.update_blurbs(gem, jobs, countries, page_blurbs)

    # resolve continents for every country we have (cached; non-grounded)
    all_countries = {P.country_of(j.get("location")) for j in jobs.values()}
    geo = G.resolve(gem, all_countries, geo)

    # 4) SAVE + RENDER (continent menu -> continent pages -> country pages)
    S.save(jobs)
    S.save_pages(page_blurbs)
    S.save_geo(geo)
    R.render(cfg, jobs, page_blurbs, geo)
    print(f"\nDone. +{added} new unlisted | {len(jobs)} total | "
          f"refreshed: {', '.join(sorted(countries))} | "
          f"{budget.run_calls} grounded calls this run.")


if __name__ == "__main__":
    main()
