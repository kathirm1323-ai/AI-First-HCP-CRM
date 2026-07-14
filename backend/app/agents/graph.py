import re
from typing import TypedDict
from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from .. import crud, models, schemas
from .groq import ask_json
from .tools import REGISTERED_TOOLS, interaction_draft, log_interaction, edit_interaction, search_past_interactions, schedule_follow_up, suggest_talking_points


class AgentState(TypedDict, total=False):
    message: str
    intent: str
    extracted_data: dict
    reply: str
    records: list[dict]


def classify(state: AgentState) -> AgentState:
    text = state["message"].lower()
    valid_intents = {"log_interaction", "edit_interaction", "search_past_interactions", "schedule_follow_up", "suggest_talking_points"}
    correction_cues = ("change ", "edit ", "update ", "correct ", "sorry", "name is", "name should be", "instead")
    if any(cue in text for cue in correction_cues):
        rule_intent = "edit_interaction"
    elif any(cue in text for cue in ("what did", "show", "history", "last time")):
        rule_intent = "search_past_interactions"
    elif "follow up" in text or "remind" in text:
        rule_intent = "schedule_follow_up"
    elif any(phrase in text for phrase in ("talking point", "prepare", "what should i discuss", "what should i talk", "next visit")):
        rule_intent = "suggest_talking_points"
    else:
        rule_intent = "log_interaction"
    classified = ask_json(f"Classify this CRM rep message: {state['message']}").get("intent")
    # Guard against an LLM returning a nested JSON object for the intent.
    # The agent should use its safe fallback rather than fail the chat.
    if isinstance(classified, dict):
        classified = classified.get("intent") or classified.get("name")
    if not isinstance(classified, str):
        classified = None
    intent = rule_intent if rule_intent != "log_interaction" else (classified if classified in valid_intents else rule_intent)
    return {"intent": intent}


def route(state: AgentState) -> str:
    return state["intent"]


def log_node(state: AgentState) -> AgentState:
    raw = log_interaction.invoke({"free_text": state["message"]})
    draft = interaction_draft(raw)
    missing = raw.get("missing_fields", [])
    reply = "I need " + ", ".join(missing) + " before I can prepare this interaction." if missing else "I extracted this interaction. Please review and confirm to save it."
    draft["missing_fields"] = missing
    return {"extracted_data": draft, "reply": reply}


def edit_node(state: AgentState) -> AgentState:
    return {"extracted_data": edit_interaction.invoke({"request": state["message"]}), "reply": "I found the requested changes. Please confirm the update before it is applied."}


def search_node(state: AgentState) -> AgentState:
    return {"extracted_data": search_past_interactions.invoke({"query": state["message"]}), "reply": "I searched the interaction history."}


def followup_node(state: AgentState) -> AgentState:
    return {"extracted_data": schedule_follow_up.invoke({"request": state["message"]}), "reply": "I prepared that follow-up task. Please confirm to create it."}


def talking_node(state: AgentState) -> AgentState:
    return {"extracted_data": suggest_talking_points.invoke({"request": state["message"]}), "reply": "I will use this HCP's history to suggest focused talking points."}


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("classify", classify)
    graph.add_node("log_interaction", log_node)
    graph.add_node("edit_interaction", edit_node)
    graph.add_node("search_past_interactions", search_node)
    graph.add_node("schedule_follow_up", followup_node)
    graph.add_node("suggest_talking_points", talking_node)
    graph.add_edge(START, "classify")
    graph.add_conditional_edges("classify", route, {name: name for name in ("log_interaction", "edit_interaction", "search_past_interactions", "schedule_follow_up", "suggest_talking_points")})
    for node in ("log_interaction", "edit_interaction", "search_past_interactions", "schedule_follow_up", "suggest_talking_points"):
        graph.add_edge(node, END)
    return graph.compile(debug=True)


agent_graph = build_graph()


def run_agent(db: Session, message: str) -> dict:
    result = agent_graph.invoke({"message": message})
    intent, data = result["intent"], result.get("extracted_data", {})
    if intent == "search_past_interactions":
        requested_name = data.get("hcp_name") if isinstance(data.get("hcp_name"), str) else None
        generic_latest = any(phrase in message.lower() for phrase in ("my latest", "latest interaction", "recent interaction", "show latest"))
        name_in_message = re.search(r"(?:with|for)\s+(Dr\.\s+[A-Za-z]+(?:\s+(?!next\b|about\b|on\b|at\b)[A-Za-z]+)?)", message, re.IGNORECASE)
        query = None if generic_latest else (requested_name or (name_in_message.group(1) if name_in_message else message))
        count_match = re.search(r"(?:last|latest)\s+(\d+)\s+interaction", message, re.IGNORECASE)
        limit = min(int(count_match.group(1)), 30) if count_match else 5
        records = [crud.record_to_dict(x) for x in crud.list_interactions(db, query, limit)]
        return {"action": intent, "reply": "Here are the most relevant interactions." if records else "No matching interactions were found.", "records": records}
    if intent == "suggest_talking_points":
        name = data.get("hcp_name", "") if isinstance(data.get("hcp_name"), str) else ""
        name_match = re.search(r"Dr\.\s+[A-Za-z]+(?:\s+(?!next\b|about\b|on\b|at\b|today\b|yesterday\b)[A-Za-z]+)?", message)
        if not name and name_match:
            name = name_match.group(0)
        records = [crud.record_to_dict(x) for x in crud.list_interactions(db, name or None, 5)]
        points = [f"Revisit {r['products'] or 'the prior discussion'} from {r['occurred_at'][:10]}." for r in records]
        if any(r.get("follow_up_action") for r in records): points.append("Close any outstanding follow-up actions before introducing a new topic.")
        return {"action": intent, "reply": "Talking points: " + (" ".join(points) if points else "No history yet; ask about current clinical priorities and document consented feedback."), "records": records}
    return {"action": intent, "reply": result["reply"], "extracted_data": data, "requires_confirmation": intent in {"log_interaction", "edit_interaction", "schedule_follow_up"} and not (intent == "log_interaction" and data.get("missing_fields"))}
