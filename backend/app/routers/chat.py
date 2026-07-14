from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from .. import crud, models, schemas
from ..agents.graph import run_agent
from ..agents.tools import REQUIRED, edit_interaction
from ..database import get_db

router = APIRouter(tags=["chat"])
CONFIRM_WORDS = {"confirm", "yes", "save", "apply", "create it"}


def session_for(db: Session, session_id: str) -> models.ChatSession:
    session = db.get(models.ChatSession, session_id)
    if not session:
        session = models.ChatSession(id=session_id, messages=[], pending_action=None)
        db.add(session)
        db.flush()
    return session


def persist(db: Session, session: models.ChatSession, role: str, text: str, pending: dict | None = None):
    session.messages = [*session.messages, {"role": role, "content": text, "at": datetime.now(timezone.utc).isoformat()}][-30:]
    session.pending_action = pending
    db.commit()


DRAFT_FIELDS = {"hcp_name", "occurred_at", "interaction_type", "products", "notes", "samples_distributed", "sentiment", "follow_up_action", "follow_up_due_at", "compliance_flags"}
CORRECTION_CUES = ("change ", "edit ", "update ", "correct ", "sorry", "name is", "name should be", "instead")


def is_draft_correction(text: str) -> bool:
    return any(cue in text.lower() for cue in CORRECTION_CUES)


def revise_pending_draft(pending: dict, request: str) -> tuple[dict, list[str]]:
    changes = edit_interaction.invoke({"request": request})
    safe_changes = {key: value for key, value in changes.items() if key in DRAFT_FIELDS and value not in (None, "", [])}
    revised = {**pending["data"], **safe_changes}
    revised["missing_fields"] = [key for key in REQUIRED if not revised.get(key)]
    return revised, list(safe_changes)


def commit_pending(db: Session, pending: dict) -> str:
    action, data = pending["action"], pending["data"]
    if action == "log_interaction":
        data = {**data, "samples_distributed": str(data["samples_distributed"])} if data.get("samples_distributed") is not None else data
        draft = schemas.InteractionCreate(**data)
        record = crud.create_interaction(db, draft)
        record.compliance_flags = data.get("compliance_flags", [])
        db.commit()
        return f"Saved interaction #{record.id} with {record.hcp.name}."
    if action == "schedule_follow_up":
        hcp = crud.get_or_create_hcp(db, data["hcp_name"])
        due_at = datetime.fromisoformat(data["follow_up_due_at"].replace("Z", "+00:00"))
        db.add(models.FollowUp(hcp_id=hcp.id, due_at=due_at, action=data["follow_up_action"]))
        db.commit()
        return f"Created a follow-up for {hcp.name}."
    if action == "edit_interaction":
        name = data.get("hcp_name", "")
        record = next(iter(crud.list_interactions(db, name, 1)), None)
        if not record:
            return "I couldn't find an interaction to update. Please specify the HCP and date."
        allowed = {key: value for key, value in data.items() if key in schemas.InteractionUpdate.model_fields and value is not None}
        crud.update_interaction(db, record, schemas.InteractionUpdate(**allowed))
        return f"Updated interaction #{record.id} with {record.hcp.name}."
    return "Nothing was saved."


@router.post("/chat", response_model=schemas.ChatResponse)
def chat(payload: schemas.ChatRequest, db: Session = Depends(get_db)):
    session = session_for(db, payload.session_id)
    text = payload.message.strip()
    if session.pending_action and session.pending_action.get("action") == "log_interaction" and is_draft_correction(text):
        revised, changed_fields = revise_pending_draft(session.pending_action, text)
        pending = {"action": "log_interaction", "data": revised}
        labels = {"hcp_name": "HCP name", "occurred_at": "date and time", "interaction_type": "interaction type", "products": "materials", "notes": "topics", "samples_distributed": "samples", "sentiment": "sentiment", "follow_up_action": "follow-up action", "follow_up_due_at": "follow-up due date"}
        changed = ", ".join(labels.get(field, field.replace("_", " ")) for field in changed_fields) or "your draft"
        reply = f"Updated {changed} in the interaction draft. Please review the form, then select Log interaction."
        persist(db, session, "user", text, pending)
        persist(db, session, "assistant", reply, pending)
        return schemas.ChatResponse(session_id=payload.session_id, reply=reply, action="edit_draft", extracted_data=revised)
    if session.pending_action and text.lower() in CONFIRM_WORDS:
        reply = commit_pending(db, session.pending_action)
        persist(db, session, "user", text, None)
        persist(db, session, "assistant", reply, None)
        return schemas.ChatResponse(session_id=payload.session_id, reply=reply, action="saved")
    if text.lower() in CONFIRM_WORDS:
        reply = "There is no interaction waiting for confirmation. Please describe a new HCP interaction first."
        persist(db, session, "user", text, None)
        persist(db, session, "assistant", reply, None)
        return schemas.ChatResponse(session_id=payload.session_id, reply=reply, action="nothing_pending")
    if session.pending_action and text.lower() in {"cancel", "no", "discard"}:
        reply = "Okay, I discarded the pending change."
        persist(db, session, "user", text, None)
        persist(db, session, "assistant", reply, None)
        return schemas.ChatResponse(session_id=payload.session_id, reply=reply, action="cancelled")
    result = run_agent(db, text)
    pending = {"action": result["action"], "data": result.get("extracted_data", {})} if result.get("requires_confirmation") and result.get("extracted_data") else None
    persist(db, session, "user", text, pending)
    persist(db, session, "assistant", result["reply"], pending)
    return schemas.ChatResponse(session_id=payload.session_id, **result)
