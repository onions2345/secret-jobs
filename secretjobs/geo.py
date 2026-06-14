CONTINENTS = ["Africa", "Asia", "Europe", "North America", "South America", "Oceania"]

FALLBACK = {
    "Australia": "Oceania", "New Zealand": "Oceania", "Fiji": "Oceania",
    "Papua New Guinea": "Oceania",
    "United Kingdom": "Europe", "Ireland": "Europe", "France": "Europe",
    "Germany": "Europe", "Spain": "Europe", "Italy": "Europe", "Portugal": "Europe",
    "Netherlands": "Europe", "Belgium": "Europe", "Switzerland": "Europe",
    "Austria": "Europe", "Sweden": "Europe", "Norway": "Europe", "Denmark": "Europe",
    "Finland": "Europe", "Poland": "Europe", "Greece": "Europe", "Romania": "Europe",
    "United States": "North America", "USA": "North America",
    "United States of America": "North America", "Canada": "North America",
    "Mexico": "North America",
    "Brazil": "South America", "Argentina": "South America", "Chile": "South America",
    "Colombia": "South America", "Peru": "South America", "Uruguay": "South America",
    "India": "Asia", "China": "Asia", "Japan": "Asia", "South Korea": "Asia",
    "Singapore": "Asia", "Malaysia": "Asia", "Indonesia": "Asia", "Philippines": "Asia",
    "Thailand": "Asia", "Vietnam": "Asia", "United Arab Emirates": "Asia",
    "Israel": "Asia", "Pakistan": "Asia", "Bangladesh": "Asia", "Hong Kong": "Asia",
    "Taiwan": "Asia",
    "South Africa": "Africa", "Nigeria": "Africa", "Kenya": "Africa", "Egypt": "Africa",
    "Ghana": "Africa", "Morocco": "Africa", "Ethiopia": "Africa", "Tanzania": "Africa",
}


def continent_of(country, cache):
    return cache.get(country) or FALLBACK.get(country) or "Other"


def resolve(gem, countries, cache):
    """Fill in continent for any country we don't yet know. Non-grounded, so it's
    effectively free and never touches the grounding budget."""
    for c in countries:
        if not c or c == "Other" or c in cache or c in FALLBACK:
            continue
        try:
            ans = gem.plain(
                f'Which continent is the country "{c}" in? Reply with exactly one of: '
                f'{", ".join(CONTINENTS)}. One line, nothing else.').strip()
        except Exception:
            ans = ""
        cache[c] = next((k for k in CONTINENTS if k.lower() in ans.lower()), "Other")
    return cache
