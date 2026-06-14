import json, datetime
from pathlib import Path

STATE_DIR = Path("state")
BUDGET_FILE = STATE_DIR / "budget.json"


def _month_key():
    return datetime.datetime.utcnow().strftime("%Y-%m")


class Budget:
    """Counts grounded (paid) Gemini calls. Resets automatically each month."""

    def __init__(self, max_per_month, max_per_run):
        self.max_per_month = max_per_month
        self.max_per_run = max_per_run
        self.run_calls = 0
        STATE_DIR.mkdir(exist_ok=True)
        self.data = self._load()

    def _load(self):
        d = json.loads(BUDGET_FILE.read_text()) if BUDGET_FILE.exists() else {}
        if d.get("month") != _month_key():
            d = {"month": _month_key(), "grounded_calls": 0}
        return d

    def remaining_month(self):
        return self.max_per_month - self.data["grounded_calls"]

    def can_spend(self):
        return (self.data["grounded_calls"] < self.max_per_month
                and self.run_calls < self.max_per_run)

    def record(self, n=1):
        self.data["grounded_calls"] += n
        self.run_calls += n
        self.save()

    def save(self):
        BUDGET_FILE.write_text(json.dumps(self.data, indent=2))
