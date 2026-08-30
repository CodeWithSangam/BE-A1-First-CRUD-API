from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from src.llm.schema import TriageOutput, Category, Urgency, SuggestedTeam
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import re
load_dotenv()
router = APIRouter()

# Prompt file load karo
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

    # Real model call
    response = client.chat.completions.create(
        model=os.getenv("LLM_MODEL"),
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": item.text}
        ]
    )

    # raw text se JSON nikalo
    raw = response.choices[0].message.content

    # code fence strip karo
    cleaned = re.sub(r"```json|```", "", raw).strip()

    # parse karo
    data = json.loads(cleaned)

    return TriageOutput(**data)
    

