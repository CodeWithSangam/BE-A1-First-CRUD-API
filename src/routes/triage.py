from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from src.llm.schema import TriageOutput, Category, Urgency, SuggestedTeam
from src.llm.parser import parse_and_validate, quarantine
from src.llm.client import call_with_retry
from dotenv import load_dotenv
import logging
import os

load_dotenv()
router = APIRouter()
logger = logging.getLogger(__name__)

PROMPT_VERSION = "triage-v1"

with open("prompts/triage-v1.md", "r") as f:
    SYSTEM_PROMPT = f.read()

class TriageInput(BaseModel):
    text: str

    @field_validator('text')
    @classmethod
    def text_must_be_valid(cls, v):
        if not v.strip():
            raise ValueError('text cannot be empty')
        if len(v) > 2000:
            raise ValueError('text cannot exceed 2000 characters')
        return v

@router.post('/triage', response_model=TriageOutput)
async def triage(item: TriageInput):
    # Kill switch
    if os.getenv("LLM_ENABLED", "true").lower() == "false":
        raise HTTPException(status_code=503, detail="LLM is currently disabled.")

    # Stub mode
    if os.getenv("LLM_STUB") == "1":
        return TriageOutput(
            category=Category.billing,
            urgency=Urgency.low,
            suggested_team=SuggestedTeam.billing_team,
            confidence=0.99,
            reason="This is a stub response for testing."
        )

    model = os.getenv("LLM_MODEL")
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": item.text}
    ]

    # First attempt
    try:
        raw, cost = call_with_retry(messages, model)
        logger.info(f"Cost log | prompt_version={PROMPT_VERSION} model={cost['model']} "
                   f"input_tokens={cost['prompt_tokens']} output_tokens={cost['completion_tokens']} "
                   f"duration_ms={cost['duration_ms']} repair=False")
    except Exception as e:
        raise HTTPException(status_code=504, detail=f"Model call failed: {str(e)}")

    try:
        return parse_and_validate(raw)
    except Exception as e:
        first_error = str(e)

    # Repair retry
    repair_messages = messages + [
        {"role": "assistant", "content": raw},
        {"role": "user", "content": f"Your previous answer was rejected: {first_error}. Return only corrected JSON matching the schema."}
    ]
    try:
        raw2, cost2 = call_with_retry(repair_messages, model)
        logger.info(f"Cost log | prompt_version={PROMPT_VERSION} model={cost2['model']} "
                   f"input_tokens={cost2['prompt_tokens']} output_tokens={cost2['completion_tokens']} "
                   f"duration_ms={cost2['duration_ms']} repair=True")
    except Exception as e:
        raise HTTPException(status_code=504, detail=f"Repair call failed: {str(e)}")

    try:
        return parse_and_validate(raw2)
    except Exception as e:
        quarantine(item.text, raw2, str(e), PROMPT_VERSION)
        raise HTTPException(status_code=422, detail="Model returned invalid response after repair. Logged to quarantine.")