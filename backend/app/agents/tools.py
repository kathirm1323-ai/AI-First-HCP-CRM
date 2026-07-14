from datetime import datetime, timedelta, timezone
import re
from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.orm import Session
from .. import crud, models, schemas
from .groq import ask_json

REQUIRED = ("hcp_name", "occurred_at", "interaction_type", "notes")


def compliance_flags(text: str) -> list[str]:
    patterns = {
        "off-label": r"\boff[-\s]?label\w*\b",
        "guarantee": r"\bguarantee\w*\b",
        "cure": r"\bcure\w*\b",
        "adverse event": r"\badverse\s+event\w*\b",
        "side effect": r"\bside\s+effect\w*\b",
    }
    lowered = text.lower()
    return [f"Review possible compliance phrase: '{label}'" for label, pattern in patterns.items() if re.search(pattern, lowered)]


@tool("log_interaction")
def log_interaction(free_text: str) -> dict:
    """Extract a field-rep interaction from natural language; always return a confirmation-ready draft."""
    data = ask_json(f"Extract an interaction from: {free_text}")
    text = free_text.lower()
    name_match = re.search(r"Dr\.\s+[A-Za-z]+(?:\s+(?!next\b|about\b|on\b|at\b|today\b|yesterday\b)[A-Za-z]+)?", free_text)
    if name_match and not data.get("hcp_name"):
        data["hcp_name"] = name_match.group(0)
    if not data.get("notes"):
        data["notes"] = free_text.strip()
    product_match = re.search(r"discussed\s+([A-Za-z][A-Za-z0-9-]*)", free_text, re.IGNORECASE)
    if product_match and not data.get("products"):
        data["products"] = [product_match.group(1)]
    if not data.get("sentiment"):
        for value in ("positive", "neutral", "negative"):
            if value in text:
                data["sentiment"] = value
                break
    if "follow-up" in text or "follow up" in text:
        data.setdefault("follow_up_action", "Follow up with the HCP")
    now = datetime.now(timezone.utc)
    if not data.get("occurred_at"):
        data["occurred_at"] = (now - timedelta(days=1)).isoformat() if "yesterday" in text else now.isoformat()
    if not data.get("interaction_type"):
        data["interaction_type"] = "call" if "call" in text else "email" if "email" in text else "visit"
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
    channel_match = re.search(r"(?:channel|interaction\s+type).*(in[- ]person|visit|meeting|call|email)|(?:change|edit).*(in[- ]person|visit|meeting|call|email)", request, re.IGNORECASE)
    if channel_match:
        value = next(group for group in channel_match.groups() if group)
        fields["interaction_type"] = "visit" if value.lower() in {"in-person", "in person", "visit", "meeting"} else value.lower()
    date_match = re.search(r"(?:date|occurred(?:_at)?|visit date)\s+(?:is|to|should be)\s+(\d{4}-\d{2}-\d{2})", request, re.IGNORECASE)
    if date_match:
        fields["occurred_at"] = f"{date_match.group(1)}T09:00:00"
    product_match = re.search(r"(?:product|materials?)\s+(?:is|to|should be)\s+([A-Za-z0-9 -]+)", request, re.IGNORECASE)
    if product_match:
        fields["products"] = [product_match.group(1).strip().rstrip(".,")]
    follow_up_match = re.search(r"follow[- ]up(?: action)?\s+(?:is|to|should be)\s+(.+)", request, re.IGNORECASE)
    if follow_up_match:
        fields["follow_up_action"] = follow_up_match.group(1).strip().rstrip(".")
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
    allowed_fields = {"hcp_name", "occurred_at", "interaction_type", "products", "notes", "samples_distributed", "sentiment", "follow_up_action", "follow_up_due_at"}
    safe_extracted = {key: value for key, value in extracted.items() if key in allowed_fields and value not in (None, "", [])} if isinstance(extracted, dict) else {}
    if safe_extracted.get("interaction_type") not in {None, "visit", "call", "email"}:
        safe_extracted.pop("interaction_type")
    if safe_extracted.get("sentiment") not in {None, "positive", "neutral", "negative"}:
        safe_extracted.pop("sentiment")
    if "products" in safe_extracted and not isinstance(safe_extracted["products"], list):
        safe_extracted["products"] = [str(safe_extracted["products"])]
    return {**safe_extracted, **inline_edit_fields(request)}


@tool("search_past_interactions")
def search_past_interactions(query: str) -> dict:
    """Classify a search request; interaction retrieval is executed safely by the orchestrator."""
    return ask_json(f"Extract the HCP name, date hints, and search terms from: {query}")


@tool("schedule_follow_up")
def schedule_follow_up(request: str) -> dict:
    """Extract a dated follow-up task from natural language for confirmation."""
    data = ask_json(f"Extract hcp_name, follow_up_action, and follow_up_due_at from: {request}")
    name_match = re.search(r"with\s+(Dr\.\s+[A-Za-z]+(?:\s+(?!next\b|about\b|on\b|at\b)[A-Za-z]+)?)", request, re.IGNORECASE)
    if name_match and not data.get("hcp_name"):
        data["hcp_name"] = name_match.group(1)
    if not data.get("follow_up_action"):
        data["follow_up_action"] = request.strip()
    if not data.get("follow_up_due_at"):
        today = datetime.now(timezone.utc)
        if "next friday" in request.lower():
            days = (4 - today.weekday()) % 7 or 7
            data["follow_up_due_at"] = (today + timedelta(days=days)).replace(hour=9, minute=0, second=0, microsecond=0).isoformat()
        elif "next week" in request.lower():
            data["follow_up_due_at"] = (today + timedelta(days=7)).replace(hour=9, minute=0, second=0, microsecond=0).isoformat()
    return data


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
