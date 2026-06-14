import json, re, time
from google import genai
from google.genai import types

_FENCE = re.compile(r"```(?:json)?|```")


class Gemini:
    def __init__(self, api_key, model, temperature=0.2):
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.temperature = temperature

    def _call(self, prompt, grounded):
        cfg_kwargs = {"temperature": self.temperature}
        if grounded:
            cfg_kwargs["tools"] = [types.Tool(google_search=types.GoogleSearch())]
        cfg = types.GenerateContentConfig(**cfg_kwargs)
        r = self.client.models.generate_content(
            model=self.model, contents=prompt, config=cfg)
        return r.text or ""

    def _with_backoff(self, prompt, grounded, retries=5):
        """Exponential backoff on transient errors (503 overloaded, rate limits).
        Waits 2s, 4s, 8s, 16s, 32s between tries, then gives up and returns ''."""
        for attempt in range(retries):
            try:
                return self._call(prompt, grounded)
            except Exception as e:
                msg = str(e).lower()
                transient = any(s in msg for s in (
                    "503", "unavailable", "overloaded", "429", "rate", "deadline", "timeout"))
                if attempt == retries - 1 or not transient:
                    if attempt == retries - 1:
                        print(f"    (gave up after {retries} tries: {str(e)[:70]})")
                    else:
                        print(f"    (non-transient error, skipped: {str(e)[:70]})")
                    return ""
                wait = 2 ** (attempt + 1)
                print(f"    (503/overload — retry in {wait}s)")
                time.sleep(wait)
        return ""

    def grounded(self, prompt):
        return self._with_backoff(prompt, grounded=True)

    def plain(self, prompt):
        return self._with_backoff(prompt, grounded=False)

    @staticmethod
    def parse_json(text, default):
        if not text:
            return default
        t = _FENCE.sub("", text).strip()
        m = re.search(r"(\[.*\]|\{.*\})", t, re.DOTALL)
        if m:
            t = m.group(1)
        try:
            return json.loads(t)
        except Exception:
            return default
