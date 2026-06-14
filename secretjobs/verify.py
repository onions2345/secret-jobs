def _prompt(job, boards):
    bad = ", ".join(boards)
    return f"""Use Google Search to decide whether this job is ALSO listed on a major job board.
Job: title="{job.get('title')}", company="{job.get('company')}", location="{job.get('location')}".
Boards to check: {bad}.

Search those boards for the SAME role at the SAME company. Return ONLY JSON (no prose):
{{"on_major_board": true_or_false, "evidence_url": "url-or-null"}}
Answer true only with a genuine match on one of those boards."""


def is_secret(gem, budget, job, boards):
    """Return (secret_bool, evidence_url). Returns (None, None) if budget is exhausted."""
    if not budget.can_spend():
        return None, None
    text = gem.grounded(_prompt(job, boards))
    budget.record(1)
    res = gem.parse_json(text, {"on_major_board": False, "evidence_url": None})
    return (not bool(res.get("on_major_board"))), res.get("evidence_url")
