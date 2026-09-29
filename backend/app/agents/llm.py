from __future__ import annotations

import json

from app.config import settings
from app.schemas import Recommendation


SYSTEM_PROMPT = """You are SignalDesk, an operations triage agent for a connectivity company.
You receive tool outputs about an incident. Return ONLY valid JSON matching this schema:
{
  "category": "network|wireless|application|integration|inquiry",
  "subcategory": "short snake_case label",
  "priority": 1-5 integer,
  "assignment_group": "one of the listed groups",
  "summary": "2-3 sentences for the engineer",
  "customer_update": "one paragraph, no jargon dump",
  "next_actions": ["action", "action", "action"],
  "confidence": 0.0-1.0,
  "similar_ticket_numbers": ["INC..."]
}
Be concrete. Prefer historical close notes when they exist. Never invent CI IDs.
"""


def synthesize_with_azure(ticket_number: str, tool_context: dict) -> Recommendation | None:
    if not settings.azure_openai_endpoint or not settings.azure_openai_api_key:
        return None

    from openai import AzureOpenAI

    client = AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )
    response = client.chat.completions.create(
        model=settings.azure_openai_deployment,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps({"ticket": ticket_number, "tools": tool_context}),
            },
        ],
    )
    payload = json.loads(response.choices[0].message.content or "{}")
    return Recommendation.model_validate(payload)
