from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from src.llm.schema import TriageOutput, Category, Urgency, SuggestedTeam
from src.llm.parser import parse_and_validate, quarantine
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
router = APIRouter()

PROMPT_VERSION = "triage-v1"

with open("prompts/triage-v1.md", "r") as f:
    SYSTEM_PROMPT = f.read()

client = OpenAI(
    base_url=os.getenv("LLM_BASE_URL"),
    api_key=os.getenv("LLM_API_KEY")
)

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

def call_model(messages):
    response = client.chat.completions.create(
        model=os.getenv("LLM_MODEL"),
        temperature=0.2,
        messages=messages
    )
    return response.choices[0].message.content

@router.post('/triage', response_model=TriageOutput)
async def triage(item: TriageInput):
    # Stub mode
    if os.getenv("LLM_STUB") == "1":
        return TriageOutput(
            category=Category.billing,
            urgency=Urgency.low,
            suggested_team=SuggestedTeam.billing_team,
            confidence=0.99,
            reason="This is a stub response for testing."
        )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": item.text}
    ]

    # First attempt
    raw = call_model(messages)
    try:
        return parse_and_validate(raw)
    except Exception as e:
        first_error = str(e)

    # Repair retry - ek baar aur try
    repair_messages = messages + [
        {"role": "assistant", "content": raw},
        {"role": "user", "content": f"Your previous answer was rejected for this reason: {first_error}. Return only corrected JSON matching the schema."}
    ]
    raw2 = call_model(repair_messages)
    try:
        return parse_and_validate(raw2)
    except Exception as e:
        # Dono fail — quarantine karo
        quarantine(item.text, raw2, str(e), PROMPT_VERSION)
        raise HTTPException(status_code=422, detail="Model returned invalid response after repair. Logged to quarantine.")