# AI-First CRM — HCP Log Interaction Module

A production-oriented starter for pharmaceutical field representatives to record HCP interactions through a structured form or a conversational, confirmation-first AI assistant.

## Architecture

```text
React + Redux (Vite)                     FastAPI + SQLAlchemy                 PostgreSQL
 ├─ Structured interaction form ───────► POST /interactions ───────────────► HCP / Interaction
 └─ Chat + review card ────────────────► POST /chat ─► LangGraph ──────────► FollowUp / ChatSession
                                                        │
                                                   Groq ChatGroq
                                              llama-3.3-70b-versatile (default; gemma2-9b-it was decommissioned by Groq)
                                              llama-3.3-70b-versatile (complex edits)
```

The chat workflow only creates or changes records after the representative selects **Confirm & save**. Conversation history and a pending action are retained in `ChatSession`, so the confirmation step survives separate requests.

## Repository layout

```text
backend/
  app/agents/       LangGraph, Groq client, and registered tools
  app/routers/      FastAPI endpoints
  app/models.py     PostgreSQL ORM models
frontend/
  src/components/   Form, conversational UI, review card, history
  src/store/        Redux Toolkit state
```

## Setup

Prerequisites: Python 3.11+, Node 20+, and a running PostgreSQL database.

1. Create a database, for example `createdb hcp_crm`.
2. Copy `backend/.env.example` to `backend/.env`, then set `DATABASE_URL` and the required `GROQ_API_KEY`. Never commit this file.
3. In `backend`, create/activate a virtual environment and run `pip install -r requirements.txt`.
4. Start the API from `backend`: `uvicorn app.main:app --reload --port 8000`.
5. Copy `frontend/.env.example` to `frontend/.env`. Update `VITE_API_URL` only if the API is not on port 8000.
6. In `frontend`, run `npm install` and `npm run dev`.

On startup the API creates the four PostgreSQL tables: `hcps`, `interactions`, `follow_ups`, and `chat_sessions`. Use migrations (Alembic) before deploying beyond this starter implementation.

## API

| Endpoint | Purpose |
| --- | --- |
| `POST /interactions` | Create a validated interaction from the form |
| `PUT /interactions/{id}` | Update a known interaction |
| `GET /interactions?q=` | List or filter interaction history |
| `GET /hcps` | List HCPs for UI state |
| `POST /chat` | Send a message through the LangGraph orchestration workflow |

## LangGraph tools

`REGISTERED_TOOLS` contains six LangChain tools (five required, plus compliance checking):

1. **log_interaction** extracts HCP, time, channel, products, samples, sentiment, notes, and follow-up details. Required-field gaps become a clarification request.
2. **edit_interaction** maps conversational changes to an update draft. The API applies it only after confirmation.
3. **search_past_interactions** identifies an HCP/search context; the orchestrator safely retrieves relevant database records.
4. **schedule_follow_up** extracts an HCP, action, and due date and stages a reminder for confirmation.
5. **suggest_talking_points** uses prior interaction records and open action context to form visit preparation prompts.
6. **compliance_flag_check** highlights phrases such as off-label, guarantee, cure, adverse event, and side effect for review. It is deliberately a guardrail, not a compliance decision.

The graph uses `llama-3.3-70b-versatile` for classification and extraction because Groq decommissioned `gemma2-9b-it`. The frontend renders extracted data as a confirmable card; replying `confirm` is the only path that persists a staged AI operation.

## Assumptions and production notes

- Voice is converted to text before calling `/chat`.
- HCP names are unique in this demo. A real deployment should use a master-data identifier and tenant/territory scoping.
- Authentication, role-based access, audit events, encryption, consent tracking, adverse-event workflows, and formal compliance approval are required before regulated production use.
- The LLM may return incomplete data. The system treats missing required fields as a request for clarification and does not fabricate values.
