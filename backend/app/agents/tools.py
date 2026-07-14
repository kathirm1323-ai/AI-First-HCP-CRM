from datetime import datetime, timezone
import re
from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.orm import Session
from .. import crud, models, schemas
from .groq import ask_json

REQUIRED = ("hcp_name", "occurred_at", "interaction_type", "notes")


def compliance_flags(text: str) -> list[str]:
    flags = []
    for term in ("off-label", "guaranteed", "cure", "adverse event", "side effect"):
        if term in text.lower():
            flags.append(f"Review possible compliance phrase: '{term}'")
    return flags


@tool("log_interaction")
def log_interaction(free_text: str) -> dict:
    """Extract a field-rep interaction from natural language; always return a confirmation-ready draft."""
    data = ask_json(f"Extract an interaction from: {free_text}")
    data["compliance_flags"] = compliance_flags(free_text)
    data["missing_fields"] = list(set(data.get("missing_fields", [])) | {key for key in REQUIRED if not data.get(key)})
    return data


def inline_edit_fields(request: str) -> dict:
    """Reliably capture common short corrections while the LLM handles richer edits."""
    fields: dict[str, str] = {}
    name_match = re.search(r"(?:the\s+)?(?:hcp\s+)?name\s+(?:is|should\s+be|to)\s+(.+)", request, re.IGNORECASE)
    if name_match:
        name = name_match.group(1).strip().rstrip(".,")
        name = re.sub(r"\bdr\s*\.\s*", "Dr. ", name, flags=re.IGNORECASE)
        name = re.sub(r"^(Dr\.\s+)([a-z])", lambda match: match.group(1) + match.group(2).upper(), name)
        if len(name) >= 2:
            fields["hcp_name"] = name
    sentiment_match = re.search(r"sentiment\s+(?:is|should\s+be|to)\s+(positive|neutral|negative)", request, re.IGNORECASE)
    if sentiment_match:
        fields["sentiment"] = sentiment_match.group(1).lower()
    return fields


@tool("edit_interaction")
def edit_interaction(request: str) -> dict:
    """Map a natural-language request to the interaction fields that should be changed."""
    extracted = ask_json(
        "Return only the fields that change in this CRM interaction correction. "
        "Allowed fields: hcp_name, occurred_at, interaction_type, products, notes, "
        "samples_distributed, sentiment, follow_up_action, follow_up_due_at. "
        f"Correction: {request}",
        complex_reasoning=True,
    )
    return {**(extracted if isinstance(extracted, dict) else {}), **inline_edit_fields(request)}


@tool("search_past_interactions")
def search_past_interactions(query: str) -> dict:
    """Classify a search request; interaction retrieval is executed safely by the orchestrator."""
    return ask_json(f"Extract the HCP name, date hints, and search terms from: {query}")


@tool("schedule_follow_up")
def schedule_follow_up(request: str) -> dict:
    """Extract a dated follow-up task from natural language for confirmation."""
    return ask_json(f"Extract hcp_name, follow_up_action, and follow_up_due_at from: {request}")


@tool("suggest_talking_points")
def suggest_talking_points(request: str) -> dict:
    """Extract the HCP and visit context for tailored talking-point suggestions."""
    return ask_json(f"Extract HCP name and intended visit context from: {request}")


@tool("compliance_flag_check")
def compliance_flag_check(text: str) -> dict:
    """Check text for phrases that require compliance review."""
    return {"flags": compliance_flags(text)}


REGISTERED_TOOLS = [log_interaction, edit_interaction, search_past_interactions, schedule_follow_up, suggest_talking_points, compliance_flag_check]


def interaction_draft(data: dict) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "hcp_name": data.get("hcp_name", ""), "occurred_at": data.get("occurred_at") or now,
        "interaction_type": data.get("interaction_type", "visit"), "products": data.get("products") or [],
        "notes": data.get("notes", ""), "samples_distributed": str(data["samples_distributed"]) if data.get("samples_distributed") is not None else None,
        "sentiment": data.get("sentiment"), "follow_up_action": data.get("follow_up_action"),
        "follow_up_due_at": data.get("follow_up_due_at"), "compliance_flags": data.get("compliance_flags", []),
    }
