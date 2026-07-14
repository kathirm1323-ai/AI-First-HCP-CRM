from fastapi import APIRouter, HTTPException
from ..agents.groq import AIServiceUnavailable, ask_json
from ..schemas import VoiceSummaryRequest, VoiceSummaryResponse

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/summarize", response_model=VoiceSummaryResponse)
def summarize_voice_note(payload: VoiceSummaryRequest):
    """Summarize consented voice-note text for review in the interaction form."""
    try:
        result = ask_json(
            "Summarize this consented HCP interaction voice note as concise factual CRM discussion notes. "
            "Return JSON with one field: notes. Do not add facts. Voice note: " + payload.transcript
        )
    except AIServiceUnavailable as exc:
        raise HTTPException(status_code=502, detail={"error": str(exc)}) from exc
    summary = result.get("notes") or result.get("summary") or payload.transcript
    return VoiceSummaryResponse(summary=summary)