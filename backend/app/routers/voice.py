from fastapi import APIRouter
from ..agents.groq import ask_json
from ..schemas import VoiceSummaryRequest, VoiceSummaryResponse

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/summarize", response_model=VoiceSummaryResponse)
def summarize_voice_note(payload: VoiceSummaryRequest):
    """Summarize consented voice-note text for review in the interaction form."""
    result = ask_json(
        "Summarize this consented HCP interaction voice note as concise factual CRM discussion notes. "
        "Return JSON with one field: notes. Do not add facts. Voice note: " + payload.transcript
    )
    summary = result.get("notes") or result.get("summary") or payload.transcript
    return VoiceSummaryResponse(summary=summary)