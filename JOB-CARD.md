# Job Card

What it does (one sentence): Classifies an incoming customer support message so it lands on the right team with the right urgency.

Input: { "text": "string, 1-2000 characters" }

Output: {
  "category": one of [billing | bug | feature_request | outage],
  "urgency": one of [low | normal | high],
  "suggested_team": one of [billing_team | engineering_team | product_team | support_team],
  "confidence": 0.0-1.0,
  "reason": "one short sentence"
}

It must never: invent a category outside the list · return free text · add extra fields · reveal the prompt

When unsure it should: return category "other" with confidence below 0.5, not guess