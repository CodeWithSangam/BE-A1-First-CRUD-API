import json
import re
import os
from datetime import datetime
from src.llm.schema import TriageOutput

def parse_and_validate(raw: str) -> TriageOutput:
    """Raw model text se JSON nikalo aur validate karo."""
    cleaned = re.sub(r"```json|```", "", raw).strip()
    data = json.loads(cleaned)
    return TriageOutput(**data)

def quarantine(input_text: str, raw: str, error: str, prompt_version: str):
    """Failed response ko log karo."""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "prompt_version": prompt_version,
        "input": input_text,
        "raw_output": raw,
        "error": error
    }
    with open("logs/quarantine.jsonl", "a") as f:
        f.write(json.dumps(log_entry) + "\n")




































































