
# ingestion/llm_provider.py
# Patch: lädt .env explizit aus dem Projekt-Root und liest OPENAI_API_KEY/OPENAI_MODEL

from dataclasses import dataclass
import os
import json
from pathlib import Path

# --- .env laden (explizit aus dem Projekt-Root) ---
try:
    from dotenv import load_dotenv
    # Projekt-Root = Elternordner von 'ingestion'
    ROOT = Path(__file__).resolve().parents[1]
    env_path = ROOT / ".env"
    # Falls es zusätzlich eine .env im CWD gibt, lädt load_dotenv beide (Root zuerst)
    load_dotenv(dotenv_path=env_path, override=False)
    load_dotenv(override=False)  # als Fallback auch CWD prüfen
except Exception:
    # dotenv optional; wenn nicht installiert, überspringen
    pass

@dataclass
class LLMConfig:
    model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    api_key: str = os.getenv("OPENAI_API_KEY", "")

class LLMProvider:
    def __init__(self, cfg: LLMConfig | None = None):
        self.cfg = cfg or LLMConfig()
        if not self.cfg.api_key:
            # Fehlermeldung mit Hinweis, wo .env erwartet wird
            raise RuntimeError(
                "OPENAI_API_KEY fehlt. Erwartet in .env im Projekt-Root. "
                "Geprüfter Pfad: {}. Alternativ Umgebungsvariable setzen."
                .format((Path(__file__).resolve().parents[1] / ".env"))
            )
        from openai import OpenAI
        self.client = OpenAI(api_key=self.cfg.api_key)

    def extract_json(self, system_prompt: str, user_prompt: str) -> dict:
        resp = self.client.chat.completions.create(
            model=self.cfg.model,
            temperature=0.2,
            messages=[
                { "role": "system", "content": system_prompt },
                { "role": "user", "content": user_prompt },
            ]
        )
        text = resp.choices[0].message.content or "{}"
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start:end+1]
        try:
            return json.loads(text)
        except json.JSONDecodeError as ex:
            raise ValueError("LLM lieferte kein valides JSON. Rohtext:\n" + text) from ex
