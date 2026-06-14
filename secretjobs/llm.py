import json, re, time
from google import genai
from google.genai import types

_FENCE = re.compile(r"```(?:json)?|```")


class Gemini:
    def __init__(self, api_key, model, temperature=0.2):
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.temperature = temperature

    def plain(self, prompt, retries=2):
        """A normal (non-grounded) call — uses the model's own knowledge. Doesn't
        touch the grounding budget. Used for reasoning like 'which city next?'."""
        last = None
        for attempt in range(retries + 1):
            try:
                r = self.client.models.generate_content(
                    model=self.model, contents=prompt,
                    config=types.GenerateContentConfig(temperature=self.temperature))
                return r.text or ""
            except Exception as e:
                last = e
                time.sleep(2 * (attempt + 1))
        raise last

    def grounded(self, prompt, retries=2):
        """One grounded (Google Search) call. Returns plain text."""
        cfg = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=self.temperature,
        )
        last = None
        for attempt in range(retries + 1):
            try:
                r = self.client.models.generate_content(
                    model=self.model, contents=prompt, config=cfg)
                return r.text or ""
            except Exception as e:
                last = e
                time.sleep(2 * (attempt + 1))
        raise last

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
