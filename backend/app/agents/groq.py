import json
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from ..config import get_settings

EXTRACTION_SYSTEM = """You are a compliant pharmaceutical CRM assistant. Return ONLY valid JSON.
Extract the requested data without inventing facts. Dates must be ISO-8601 if stated. Never make medical claims.
For interaction extraction use: hcp_name, occurred_at, interaction_type (visit/call/email), products (array), notes,
samples_distributed, sentiment (positive/neutral/negative), follow_up_action, follow_up_due_at, missing_fields (array).
For intent use: intent (log_interaction/edit_interaction/search_past_interactions/schedule_follow_up/suggest_talking_points/compliance_flag_check/clarify), confidence.
"""


def llm(complex_reasoning: bool = False) -> ChatGroq | None:
    settings = get_settings()
    if not settings.groq_api_key:
        return None
    return ChatGroq(model="llama-3.3-70b-versatile", api_key=settings.groq_api_key, temperature=0, request_timeout=15, max_retries=1)


def ask_json(prompt: str, complex_reasoning: bool = False) -> dict:
    model = llm(complex_reasoning)
    if not model:
        return {}
    try:
        response = model.invoke([SystemMessage(content=EXTRACTION_SYSTEM), HumanMessage(content=prompt)])
    except Exception:
        return {}
    text = response.content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
    if text.endswith("```"):
        text = text[:-3].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}
