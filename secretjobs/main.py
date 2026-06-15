import os, sys, yaml, datetime
from pathlib import Path
from secretjobs.llm import Gemini
from secretjobs.budget import Budget
from secretjobs import discover as D, store as S, render as R, locations as L, pages as P, geo as G
from secretjobs import boards as B, freshness as F, verify as V


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
    # ROTATE cities: cover only a few per run so each refreshes every few days
    per_run = cfg.get("cities_per_run", len(places))
    rot = meta.get("city_rotation", 0)
    if per_run < len(places):
        order = places[rot % len(places):] + places[:rot % len(places)]
        places = order[:per_run]
        meta["city_rotation"] = (rot + per_run) % max(1, len(order))
    day = datetime.date.today().toordinal()
    cats = _rotate(cfg["categories"], day)[: cfg.get("max_categories_per_run", 10)]
    print("This run:", " | ".join(c["name"] for c in cats), "@", " -> ".join(places))

    # SKIP combos searched within the last `search_cooldown_days`
    cooldown = cfg.get("search_cooldown_days", 5)
    today_iso = datetime.date.today().isoformat()
    last_searched = meta.get("last_searched", {})  # {"city|category": "YYYY-MM-DD"}

    def _recently_done(city, catname):
        d = last_searched.get(f"{city}|{catname}")
        if not d:
            return False
        try:
            return (datetime.date.today() - datetime.date.fromisoformat(d)).days < cooldown
        except ValueError:
            return False

    # DISCOVER — one search per (category, place); big boards excluded by the search itself.
    # Then a SECOND search per NEW job classifies it: secret / on-board / unchecked.
    added = onboard = unsure = skipped = 0
    for place in places:
        for cat in cats:
            if not budget.can_spend():
                print("Budget cap reached — stopping early."); break
            city = place.split(",")[0].strip()
            if _recently_done(city, cat["name"]):     # searched recently -> skip, save money
                skipped += 1
                continue
            found = D.discover(gem, budget, cat["brief"], place, eff_boards)
            last_searched[f"{city}|{cat['name']}"] = today_iso
            kept_here = 0
            for f in found:
                jid = S._id(f["url"])
                if jid in jobs:                      # already known — refresh, no re-verify
                    S.upsert(jobs, f, None)
                    continue
                res = V.check_one(gem, budget, f, eff_boards)   # second check (new jobs only)
                on_board = res.get("on_board") if isinstance(res, dict) else None
                f["category"] = cat["name"]; f["city"] = city
                rec, is_new = S.upsert(jobs, f, (res or {}).get("evidence_url"))
                rec["category"] = cat["name"]; rec["city"] = city
                if on_board is True:                 # also on a big board -> "Not a secret"
                    rec["status"] = "on_board"
                    rec["board_checked"] = True
                    rec["verified_unlisted"] = False
                    rec["board_name"] = (res or {}).get("board") or ""
                    rec["checked_against"] = ["also listed on a major board"]
                    onboard += 1
                elif on_board is False:              # confirmed NOT on boards -> secret
                    rec["status"] = "secret"
                    rec["board_checked"] = True
                    rec["verified_unlisted"] = True
                    rec["checked_against"] = ["confirmed not on major boards"]
                else:                                # couldn't confirm -> not yet checked
                    rec["status"] = "unchecked"
                    rec["board_checked"] = False
                    rec["verified_unlisted"] = False
                    rec["checked_against"] = ["search-filtered, not yet cross-checked"]
                    unsure += 1
                added += int(is_new); kept_here += 1
            print(f"  {cat['name']} @ {place} -> {len(found)} found, {kept_here} kept")
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

    meta["last_searched"] = last_searched
    S.save(jobs); S.save_pages(page_blurbs); S.save_geo(geo); S.save_meta(meta)
    R.render(cfg, jobs, page_blurbs, geo)
    print(f"\nDone. +{added} new (secret + {onboard} on-board + {unsure} unchecked) | "
          f"{skipped} skipped (cooldown) | -{removed} gone | {len(jobs)} total | "
          f"{budget.run_calls} searches this run.")


if __name__ == "__main__":
    main()
