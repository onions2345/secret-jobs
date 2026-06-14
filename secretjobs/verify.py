def _prompt(job):
    return f"""Use Google Search to judge whether this job is ALSO discoverable on a MAINSTREAM
/ major job board — you decide which sites qualify as major boards (large aggregators and the
well-known career portals).

Job: title="{job.get('title')}", company="{job.get('company')}", location="{job.get('location')}".

Search for the same role at the same company on those mainstream boards. Return ONLY JSON:
{{"on_major_board": true_or_false, "board": "name-or-null", "evidence_url": "url-or-null"}}
Answer true only on a genuine match to a mainstream board."""


def is_secret(gem, budget, job):
    """Return (secret_bool, board_name, evidence_url). (None, None, None) if budget gone."""
    if not budget.can_spend():
        return None, None, None
    res = gem.parse_json(gem.grounded(_prompt(job)),
                         {"on_major_board": False, "board": None, "evidence_url": None})
    budget.record(1)
    return (not bool(res.get("on_major_board"))), res.get("board"), res.get("evidence_url")
