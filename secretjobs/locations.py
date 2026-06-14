def expand(gem, start_location, n):
    """Ask the AI for an ordered list of places to cover, starting at `start_location`
    and spreading outward (nearby cities first, then further, then other countries).
    Non-grounded — uses the model's world knowledge, so it's free of grounding budget."""
    if n <= 1:
        return [start_location]
    prompt = f"""Starting from "{start_location}", list the first {n} places a job-search
crawler should cover, in order: the start first, then progressively wider — nearby cities
and towns, then the rest of that country's major cities, then other countries.
Return ONLY a JSON array of "City, Region/State, Country" strings. No prose."""
    out = gem.parse_json(gem.plain(prompt), [start_location])
    if not isinstance(out, list) or not out:
        return [start_location]
    if out[0] != start_location:
        out = [start_location] + [x for x in out if x != start_location]
    return out[:n]
