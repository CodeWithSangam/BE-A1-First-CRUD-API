from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from src.llm.schema import TriageOutput, Category, Urgency, SuggestedTeam
import os

router = APIRouter()

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
    # Stub mode - no AI call
    if os.getenv("LLM_STUB") == "1":
        return TriageOutput(
            category=Category.billing,
            urgency=Urgency.low,
            suggested_team=SuggestedTeam.billing_team,
            confidence=0.99,
            reason="This is a stub response for testing."
        )
    
    # Real AI call aayega Stage 2 mein
    raise HTTPException(status_code=501, detail="AI not wired yet")