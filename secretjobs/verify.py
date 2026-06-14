"""Second check: confirm a NEWLY-found job is NOT also posted on a major board.
ONE grounded search per new job (not per existing job, not repeated), bounded by
budget and protected by the same backoff as discovery. If the check can't get a
clear answer, the job is kept but marked UNVERIFIED (never falsely stamped)."""


def _prompt(job, boards):
    blist = ", ".join(boards[:25])
    return (f'Use Google Search to check ONE thing: is this exact job vacancy ALSO '
            f'advertised on any of these major job boards?\n'
            f'Job: title="{job.get("title")}", company="{job.get("company")}", '
            f'location="{job.get("location")}".\n'
            f'Major boards to check: {blist}.\n'
            f'Search for this role (title + company) on those boards. '
            f'Return ONLY JSON: {{"on_board": true_or_false, "board": "name-or-null", '
            f'"evidence_url": "url-or-null"}}. '
            f'Answer on_board=true ONLY if you find a genuine matching listing on one '
            f'of those boards; if you cannot confirm a match, answer false.')


def check_one(gem, budget, job, boards):
    """Return dict {on_board: bool, board, evidence_url} or None if budget is gone."""
    if not budget.can_spend():
        return None
    res = gem.parse_json(gem.grounded(_prompt(job, boards)),
                         {"on_board": None, "board": None, "evidence_url": None})
    budget.record(1)
    if not isinstance(res, dict):
        return {"on_board": None, "board": None, "evidence_url": None}
    return res
