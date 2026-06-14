# Secret Jobs

Finds job openings posted on **employers' own websites and small niche sites**, then
**verifies each one is _not_ also listed on a major board** (Seek, Indeed, Jora, LinkedIn,
Gumtree, etc.) before publishing it. One API key (Google AI Studio / Gemini), one static
site, designed to stay under ~US$10/month.

It starts with **Adelaide** and expands by editing one config file.

## How it works

Gemini can't crawl the web by itself — but with **Google Search grounding** it runs real
searches and reasons over the results. The pipeline uses that twice:

1. **Discover** — grounded search for `<niche>` jobs in `<city>`, instructed to return only
   roles on the employer's own site and to ignore the big boards.
2. **Verify** — for each candidate, a second grounded search checks the big boards for the
   same role at the same company. Found there → dropped. Not found → kept.
3. **Publish** — kept roles are written to `state/jobs.json` and rendered into
   `site/index.html`, deployed free on GitHub Pages.

## Cost (the only thing that costs money is grounding)

- Gemini Flash tokens are ~US$0.10–0.40 per **million** — negligible here.
- **Google Search grounding** is the lever: ~**5,000 free grounded prompts/month** on the
  Gemini 3.x family, then ~US$14 per 1,000.
- Each kept job ≈ 1 discovery call (returns several candidates) + 1 verify call each.
- `config.yaml` caps usage: `max_grounded_calls_per_month: 5500` ≈ stays under ~US$10.
  Lower it to be safe. The guard in `state/budget.json` stops the run when you hit the cap.

> Use a **Gemini 3.x Flash** model in `config.yaml` to qualify for the free grounding quota.
> Confirm the exact current model id in Google AI Studio.

## Run it locally

```bash
pip install -r requirements.txt
export GEMINI_API_KEY="your_key_from_aistudio.google.com"
python -m secretjobs.main
# open site/index.html
```

## Deploy (auto-building public index)

1. Push this folder to a new GitHub repo.
2. Repo **Settings → Secrets and variables → Actions** → add `GEMINI_API_KEY`.
3. Repo **Settings → Pages** → Source = **GitHub Actions**.
4. The workflow in `.github/workflows/build.yml` runs daily (and on demand), updates
   `state/jobs.json`, and publishes `site/` to `https://<you>.github.io/<repo>`.

## Expand coverage

Edit `config.yaml`:
- Add cities under `locations:` (then other countries — just add `city/region/country`).
- Change `niches:` to go beyond cars to any field.
- Add domains to `major_boards:` for other countries (e.g. `seek.co.nz`, `reed.co.uk`).

## Please keep it clean (legal / ethical notes)

- The pipeline reads **Google's search results via grounding** — it does not scrape Seek or
  Indeed directly (their terms forbid that). The "is it on a board?" check only reads public
  search results.
- It stores only a short, model-written summary plus a **link to the original** — it does not
  republish full listing text. Keep it that way (it's both safer and the right thing).
- If you later add direct page fetching to enrich listings, **respect robots.txt** and rate
  limits, and keep linking back to the source.
- Verification is best-effort: grounding can miss or misjudge. Treat "unlisted" as "not
  found on the boards we checked," not a guarantee.
