from pydantic import BaseModel
from enum import Enum

class Category(str, Enum):
    billing = "billing"
    bug = "bug"
    feature_request = "feature_request"
    outage = "outage"

class Urgency(str, Enum):
    low = "low"
    normal = "normal"
    high = "high"

class SuggestedTeam(str, Enum):
    billing_team = "billing_team"
    engineering_team = "engineering_team"
    product_team = "product_team"
    support_team = "support_team"

class TriageOutput(BaseModel):
    category: Category
    urgency: Urgency
    suggested_team: SuggestedTeam
    confidence: float
    reason: str