import json, html, re, datetime
from pathlib import Path
from secretjobs.pages import country_of
from secretjobs.geo import CONTINENTS, continent_of

SITE_DIR = Path("site")


def _esc(s):
    return html.escape(str(s or ""))


def _slug(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", (s or "other").lower())).strip("-") or "other"


def _city_of(loc):
    parts = [p.strip() for p in (loc or "").split(",") if p.strip()]
    return parts[0] if parts else "—"


def _order_cats(cats, promoted):
    promoted = [c for c in promoted if c in cats]
    return promoted + sorted(c for c in cats if c not in promoted)


def _stamp(j):
    b = j.get("checked_against") or []
    if len(b) == 1 and " " in b[0]:
        return _esc(b[0])
    out = " · ".join(x.split(".")[0].upper() for x in b[:3])
    return out + (f" +{len(b) - 3}" if len(b) > 3 else "")


def _card(j, cont):
    city = j.get("city") or _city_of(j.get("location"))
    return f"""
  <article class="card" data-cat="{_esc(j.get('category') or 'Other')}"
           data-country="{_esc(country_of(j.get('location')))}"
           data-city="{_esc(city)}">
    <div class="card-top">
      <div>
        <span class="cat">{_esc(j.get('category') or 'Other')}</span>
        <h2 class="title"><a href="{_esc(j['url'])}" target="_blank" rel="noopener">{_esc(j['title'])}</a></h2>
      </div>
      <span class="found">found {_esc(j.get('first_seen'))}</span>
    </div>
    <p class="meta">{_esc(j.get('company'))} <span class="dot">•</span> {_esc(j.get('location'))}</p>
    <p class="summary">{_esc(j.get('summary'))}</p>
    <div class="card-bottom">
      <span class="stamp">✓ OFF-MARKET <span class="stamp-sub">major boards excluded{(' · link checked ' + _esc(j.get('last_checked'))) if j.get('last_checked') else ''}</span></span>
      <span class="src">{_esc(j.get('source_domain') or j['url'].split('/')[2])}</span>
      <a class="open" href="{_esc(j['url'])}" target="_blank" rel="noopener">Open original ↗</a>
    </div>
  </article>"""


def _shell(title, desc, body):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(title)}</title>
<meta name="description" content="{_esc(desc)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="style.css">
</head>
<body>
{body}
</body>
</html>"""


def _crumb(trail):
    parts = " <span>/</span> ".join(
        f'<a href="{_esc(href)}">{_esc(name)}</a>' if href else f"<span>{_esc(name)}</span>"
        for name, href in trail)
    return f'<nav class="crumb">{parts}</nav>'


def _header(eyebrow, h1, tag, count, label, crumb=""):
    return f"""<header>
  <div class="scan"></div>
  <div class="wrap hd">
    {crumb}
    <div class="eyebrow">{_esc(eyebrow)}</div>
    <h1>{_esc(h1)}</h1>
    {f'<p class="tag">{_esc(tag)}</p>' if tag else ''}
    <div class="count"><b id="n">{count}</b><span>{_esc(label)}</span></div>
  </div>
</header>"""


def _footer():
    u = datetime.datetime.utcnow().strftime("%d %b %Y, %H:%M UTC")
    return (f'<footer>Updated {u} · Every role checked against major boards and not found '
            f'on them · <a href="index.html">All continents</a> · <a href="jobs.json">jobs.json</a></footer>')


def _listing(rows, promoted, sec_attr, sec_label, sec_values, cont_map):
    cats = _order_cats(sorted({r.get("category", "Other") for r in rows}), promoted)
    chips = '<button class="chip on" data-f="all">All categories</button>' + "".join(
        f'<button class="chip" data-f="{_esc(c)}">{_esc(c)}</button>' for c in cats)
    sec = ""
    if sec_attr:
        opts = f'<option value="all">{_esc(sec_label[1])}</option>' + "".join(
            f'<option value="{_esc(v)}">{_esc(v)}</option>' for v in sec_values)
        sec = (f'<div class="loc-row"><label for="sec">{_esc(sec_label[0])}</label>'
               f'<select id="sec" data-attr="{sec_attr}">{opts}</select></div>')
    cards = "\n".join(_card(j, cont_map) for j in rows) or \
        '<p class="empty">Nothing here yet — the crawler fills this in.</p>'
    return f"""
  <div class="controls"><div class="chips" id="cats">{chips}</div>{sec}</div>
  <main id="list">{cards}</main>
<script>
  const cats=document.getElementById('cats'),sel=document.getElementById('sec');
  let fc='all',fs='all',sa=sel?sel.dataset.attr:null;
  function apply(){{let n=0;document.querySelectorAll('.card').forEach(c=>{{
    const okc=fc==='all'||c.dataset.cat===fc;
    const oks=fs==='all'||!sa||c.dataset[sa]===fs;
    const s=okc&&oks;c.style.display=s?'':'none';if(s)n++;}});
    document.getElementById('n').textContent=n;}}
  cats.addEventListener('click',e=>{{const b=e.target.closest('.chip');if(!b)return;
    [...cats.children].forEach(x=>x.classList.remove('on'));b.classList.add('on');
    fc=b.dataset.f;apply();}});
  if(sel)sel.addEventListener('change',()=>{{fs=sel.value;apply();}});
</script>"""


def _index(cfg, jobs):
    geo = cfg["_geo"]
    by_cont = {}
    for j in jobs.values():
        by_cont.setdefault(continent_of(country_of(j.get("location")), geo), []).append(j)
    tiles = ""
    for cont in CONTINENTS:
        rows = by_cont.get(cont, [])
        if rows:
            countries = sorted({country_of(r.get("location")) for r in rows})
            cl = " · ".join(countries[:3]) + (f" +{len(countries)-3}" if len(countries) > 3 else "")
            tiles += (f'<a class="tile" href="{_slug(cont)}.html"><span class="tile-c">{_esc(cont)}</span>'
                      f'<span class="tile-n">{len(rows)} unlisted</span>'
                      f'<span class="tile-cats">{_esc(cl)}</span></a>')
        else:
            tiles += (f'<div class="tile muted-tile"><span class="tile-c">{_esc(cont)}</span>'
                      f'<span class="tile-n">coming soon</span></div>')
    items = sorted(jobs.values(), key=lambda j: j.get("first_seen", ""), reverse=True)
    latest = "".join(
        f'<li><a href="{_esc(j["url"])}" target="_blank" rel="noopener">{_esc(j["title"])}</a>'
        f'<span>{_esc(j.get("category"))} · {_esc(country_of(j.get("location")))}</span></li>'
        for j in items[:6]) or "<li class='muted'>Nothing yet.</li>"
    body = (_header("The hidden job market", cfg["site_name"], cfg["site_tagline"],
                    len(items), "verified unlisted roles") + f"""
<div class="wrap">
  <h3 class="kicker">Browse by continent</h3>
  <div class="tiles">{tiles}</div>
  <h3 class="kicker">Latest finds</h3>
  <ul class="latest">{latest}</ul>

  <div class="diy">
    <h3 class="kicker">DIY — find these jobs yourself with AI</h3>
    <p>You can use AI to find jobs that aren't on the big job boards — so you have a better chance.</p>
    <p>Just ask an AI (like Gemini or ChatGPT) something like:</p>
    <p class="ask">"Find jobs about cars in Adelaide that aren't posted on any job network — only on mechanic or private company websites that most people wouldn't find."</p>
    <p>It will return some listings. Then ask:</p>
    <p class="ask">"Do any of these websites actually say they're looking for people right now?"</p>
    <p>Then ask:</p>
    <p class="ask">"Can you confirm these jobs aren't posted anywhere else?"</p>
    <p>After those steps, it'll give you a more reliable answer.</p>
    <p class="diy-note">Always double-check the link before applying — AI sometimes gets details wrong.</p>
  </div>

  {_footer()}
</div>""")
    return _shell(f"{cfg['site_name']} — unlisted jobs by continent, country & city",
                  cfg["site_tagline"], body)


def _continent_page(cfg, cont, rows):
    countries = sorted({country_of(r.get("location")) for r in rows})
    tiles = "".join(
        f'<a class="tile" href="{_slug(c)}.html"><span class="tile-c">{_esc(c)}</span>'
        f'<span class="tile-n">{sum(1 for r in rows if country_of(r.get("location"))==c)} unlisted</span></a>'
        for c in countries)
    body = (_header(cont, cont, "", len(rows), "verified unlisted roles",
                    _crumb([("All continents", "index.html"), (cont, None)])) + f"""
<div class="wrap">
  <h3 class="kicker">Countries in {_esc(cont)}</h3>
  <div class="tiles">{tiles}</div>
  <p class="muted" style="margin-top:18px">Choose a country to see its cities and roles.</p>
  {_footer()}
</div>""")
    return _shell(f"Unlisted jobs in {cont} — {cfg['site_name']}",
                  f"Unlisted jobs across {cont}, verified not on the big boards.", body)


def _country_page(cfg, country, rows, blurb):
    geo = cfg["_geo"]
    cont = continent_of(country, geo)
    rows = sorted(rows, key=lambda j: j.get('first_seen', ''), reverse=True)
    promoted = cfg["promoted_categories"]

    cities = sorted({(r.get("city") or _city_of(r.get("location"))) for r in rows})
    city_tiles = '<button class="tile citytile on" data-city="all"><span class="tile-c">All cities</span>' \
                 f'<span class="tile-n">{len(rows)} roles</span></button>'
    for c in cities:
        n = sum(1 for r in rows if (r.get("city") or _city_of(r.get("location"))) == c)
        city_tiles += (f'<button class="tile citytile" data-city="{_esc(c)}">'
                       f'<span class="tile-c">{_esc(c)}</span><span class="tile-n">{n} roles</span></button>')

    cats = _order_cats(sorted({r.get("category", "Other") for r in rows}), promoted)
    chips = '<button class="chip on" data-f="all">All categories</button>' + "".join(
        f'<button class="chip" data-f="{_esc(c)}">{_esc(c)}</button>' for c in cats)

    cards = "\n".join(_card(j, cont) for j in rows) or \
        '<p class="empty">Nothing here yet — the crawler fills this in.</p>'
    blurb_html = f'<p class="blurb">{_esc(blurb)}</p>' if blurb else ""

    body = (_header("Unlisted jobs", country, "", len(rows), "verified unlisted roles",
                    _crumb([("All continents", "index.html"),
                            (cont, f"{_slug(cont)}.html"), (country, None)])) + f"""
<div class="wrap">
  {blurb_html}
  <h3 class="kicker">Cities in {_esc(country)}</h3>
  <div class="tiles" id="cities">{city_tiles}</div>
  <div class="controls"><div class="chips" id="cats">{chips}</div></div>
  <main id="list">{cards}</main>
  {_footer()}
</div>
<script>
  const cities=document.getElementById('cities'), cats=document.getElementById('cats');
  let fc='all', fy='all';
  function apply(){{
    let n=0;
    document.querySelectorAll('.card').forEach(c=>{{
      const ok=(fc==='all'||c.dataset.cat===fc)&&(fy==='all'||c.dataset.city===fy);
      c.style.display=ok?'':'none'; if(ok)n++;
    }});
    document.getElementById('n').textContent=n;
  }}
  cities.addEventListener('click',e=>{{const t=e.target.closest('.citytile');if(!t)return;
    [...cities.children].forEach(x=>x.classList.remove('on'));t.classList.add('on');
    fy=t.dataset.city;apply();}});
  cats.addEventListener('click',e=>{{const b=e.target.closest('.chip');if(!b)return;
    [...cats.children].forEach(x=>x.classList.remove('on'));b.classList.add('on');
    fc=b.dataset.f;apply();}});
</script>""")
    return _shell(f"Unlisted jobs in {country} — {cfg['site_name']}",
                  f"Unlisted job openings in {country}, verified not on the big boards.", body)


def render(cfg, jobs, pages=None, geo=None):
    cfg = dict(cfg)
    cfg["_geo"] = geo or {}
    cfg.setdefault("promoted_categories", ["IT & Software"])
    pages = pages or {}
    SITE_DIR.mkdir(exist_ok=True)
    (SITE_DIR / "style.css").write_text(_CSS, encoding="utf-8")
    (SITE_DIR / "index.html").write_text(_index(cfg, jobs), encoding="utf-8")

    by_country, by_cont = {}, {}
    for j in jobs.values():
        c = country_of(j.get("location"))
        by_country.setdefault(c, []).append(j)
        by_cont.setdefault(continent_of(c, cfg["_geo"]), []).append(j)
    for cont, rows in by_cont.items():
        if cont == "Other":
            continue
        (SITE_DIR / f"{_slug(cont)}.html").write_text(_continent_page(cfg, cont, rows), encoding="utf-8")
    for country, rows in by_country.items():
        blurb = pages.get(country, {}).get("blurb", "")
        (SITE_DIR / f"{_slug(country)}.html").write_text(
            _country_page(cfg, country, rows, blurb), encoding="utf-8")

    (SITE_DIR / "jobs.json").write_text(
        json.dumps(list(jobs.values()), indent=2, ensure_ascii=False), encoding="utf-8")
    domain = (cfg.get("custom_domain") or "").strip()
    if domain:
        (SITE_DIR / "CNAME").write_text(domain + "\n", encoding="utf-8")


_CSS = """
:root{--ink:#0c0f14;--panel:#141a22;--line:#222d3a;--line-2:#2c3a4b;--signal:#ffb000;
--text:#e7eef6;--muted:#8593a4;--ok:#46d07f;--ok-dim:#16331f}
*{box-sizing:border-box}
body{margin:0;background:var(--ink);color:var(--text);font-family:Inter,system-ui,sans-serif;
line-height:1.5;-webkit-font-smoothing:antialiased}
a{color:inherit}
.wrap{max-width:820px;margin:0 auto;padding:0 20px}
header{position:relative;overflow:hidden;border-bottom:1px solid var(--line);
background:radial-gradient(120% 140% at 80% -20%,#16202b 0%,var(--ink) 60%)}
.scan{position:absolute;inset:0;pointer-events:none;
background:linear-gradient(transparent 0 50%,rgba(255,176,0,.05) 50%);
background-size:100% 6px;mix-blend-mode:screen;animation:drift 9s linear infinite}
@keyframes drift{to{background-position:0 600px}}
@media (prefers-reduced-motion:reduce){.scan{animation:none}}
.hd{position:relative;padding:38px 0 32px}
.crumb{font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--muted);margin-bottom:16px}
.crumb a{color:var(--signal);text-decoration:none} .crumb span{margin:0 6px;color:var(--line-2)}
.eyebrow{font-family:'JetBrains Mono',monospace;font-size:12px;letter-spacing:.22em;
text-transform:uppercase;color:var(--signal)}
h1{font-family:'Space Grotesk',sans-serif;font-weight:700;letter-spacing:-.02em;
font-size:clamp(38px,8vw,62px);margin:.16em 0 .12em;line-height:.96}
.tag{color:var(--muted);max-width:52ch;margin:0}
.count{font-family:'Space Grotesk',sans-serif;display:flex;align-items:baseline;gap:10px;margin-top:22px}
.count b{font-size:32px;color:var(--signal);font-weight:700}
.count span{font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--muted);
letter-spacing:.12em;text-transform:uppercase}
.kicker{font-family:'JetBrains Mono',monospace;font-size:12px;letter-spacing:.18em;
text-transform:uppercase;color:var(--muted);margin:34px 0 14px}
.blurb{color:var(--text);font-size:15.5px;max-width:64ch;margin:24px 0 6px;
border-left:2px solid var(--signal);padding-left:14px}
.tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px}
.tile{display:flex;flex-direction:column;gap:4px;text-decoration:none;
border:1px solid var(--line);background:var(--panel);border-radius:8px;padding:16px;transition:.15s}
.tile:hover{border-color:var(--signal)}
.citytile{cursor:pointer;text-align:left;font:inherit;color:var(--text)}
.citytile.on{border-color:var(--signal);background:rgba(255,176,0,.06)}
.citytile .tile-c{color:var(--text)}
.muted-tile{opacity:.5}
.tile-c{font-family:'Space Grotesk',sans-serif;font-size:18px;font-weight:500}
.tile-n{font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--signal)}
.tile-cats{font-size:12.5px;color:var(--muted)}
.latest{list-style:none;padding:0;margin:0}
.latest li{border-top:1px solid var(--line);padding:11px 0;display:flex;
justify-content:space-between;gap:14px;flex-wrap:wrap}
.latest a{font-family:'Space Grotesk',sans-serif;text-decoration:none}
.latest a:hover{text-decoration:underline;text-decoration-color:var(--signal)}
.latest span{font-family:'JetBrains Mono',monospace;font-size:11.5px;color:var(--muted)}
.diy{margin-top:40px;border:1px solid var(--line);border-radius:10px;
padding:20px 22px;background:var(--panel)}
.diy p{margin:10px 0;color:var(--text);font-size:14.5px;line-height:1.55}
.diy .ask{border-left:3px solid var(--signal);padding:8px 12px;margin:10px 0;
background:rgba(255,176,0,.05);font-style:italic;color:var(--text)}
.diy .diy-note{font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--muted);margin-top:14px}
.muted{color:var(--muted)}
.controls{position:sticky;top:0;background:var(--ink);z-index:5;border-bottom:1px solid var(--line);
padding:16px 0 14px;margin-top:8px}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{font-family:'JetBrains Mono',monospace;font-size:12px;letter-spacing:.03em;background:transparent;
color:var(--muted);border:1px solid var(--line-2);padding:6px 12px;border-radius:999px;cursor:pointer;transition:.15s}
.chip:hover{color:var(--text);border-color:var(--signal)}
.chip.on{color:var(--ink);background:var(--signal);border-color:var(--signal);font-weight:500}
.loc-row{display:flex;align-items:center;gap:10px;margin-top:12px}
.loc-row label{font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.12em;
text-transform:uppercase;color:var(--muted)}
select{font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--text);background:var(--panel);
border:1px solid var(--line-2);border-radius:7px;padding:7px 10px;cursor:pointer}
select:focus-visible,.chip:focus-visible,.open:focus-visible,.tile:focus-visible{outline:2px solid var(--signal);outline-offset:2px}
main{padding:18px 0 80px}
.card{border:1px solid var(--line);background:var(--panel);border-radius:8px;padding:16px 18px 14px;
margin:14px 0;transition:border-color .15s}
.card:hover{border-color:var(--line-2)}
.card-top{display:flex;justify-content:space-between;align-items:flex-start;gap:14px}
.cat{display:inline-block;font-family:'JetBrains Mono',monospace;font-size:10.5px;letter-spacing:.08em;
text-transform:uppercase;color:var(--signal);border:1px solid var(--line-2);border-radius:4px;padding:2px 7px;margin-bottom:8px}
.title{font-family:'Space Grotesk',sans-serif;font-size:19px;font-weight:500;margin:0;line-height:1.25}
.title a{text-decoration:none}
.title a:hover{text-decoration:underline;text-decoration-color:var(--signal)}
.found{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted);white-space:nowrap;padding-top:4px}
.meta{margin:4px 0 0;color:var(--text);font-size:14px}
.dot{color:var(--line-2);margin:0 4px}
.summary{margin:10px 0 14px;color:var(--muted);font-size:14.5px}
.card-bottom{display:flex;align-items:center;flex-wrap:wrap;gap:10px;border-top:1px solid var(--line);padding-top:12px}
.stamp{font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:500;color:var(--ok);
background:var(--ok-dim);border:1px solid #224a30;border-radius:5px;padding:5px 9px;letter-spacing:.06em}
.stamp-sub{color:var(--muted);font-weight:400;margin-left:4px}
.src{font-family:'JetBrains Mono',monospace;font-size:11.5px;color:var(--muted)}
.open{margin-left:auto;font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--signal);
text-decoration:none;border:1px solid var(--line-2);padding:6px 11px;border-radius:5px;transition:.15s}
.open:hover{border-color:var(--signal);background:rgba(255,176,0,.08)}
.empty{color:var(--muted);text-align:center;padding:60px 0;font-family:'JetBrains Mono',monospace}
footer{border-top:1px solid var(--line);color:var(--muted);font-size:12px;
font-family:'JetBrains Mono',monospace;padding:22px 0 40px}
footer a{color:var(--signal)}
"""
