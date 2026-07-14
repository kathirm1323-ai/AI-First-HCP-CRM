# AI-First HCP CRM

A life-sciences CRM module for field representatives to record Healthcare Professional (HCP) interactions through a structured React form or a LangGraph-powered AI conversation.

## Features

- React + Redux Toolkit user interface using Google Inter
- FastAPI and PostgreSQL backend
- Groq LLM integration using `llama-3.3-70b-versatile` (documented substitute because Groq deprecated `gemma2-9b-it`)
- LangGraph workflow with six tools: log interaction, edit interaction, search history, schedule follow-up, suggest talking points, and compliance flag check
- Human review gate: AI drafts are not saved until **Confirm & save** is selected
- Voice-note transcription and summarization with an explicit consent step

## Run locally

### 1. Start PostgreSQL

Install Docker Desktop, then run from the repository root:

```bash
docker compose up -d
```

### 2. Configure the backend

```bash
cd backend
copy .env.example .env
```

Set `GROQ_API_KEY` in `backend/.env`. Do not commit this file.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open FastAPI Swagger documentation at `http://127.0.0.1:8000/docs`.

### 3. Configure the frontend

Open a second terminal:

```bash
cd frontend
copy .env.example .env
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

## Verification flow

1. Choose **Structured form** or **AI conversation**.
2. In AI conversation, describe an HCP interaction in natural language.
3. Review the extracted card and select **Confirm & save**.
4. Search saved history with: `Show my latest interaction.`

## LangGraph tools

1. `log_interaction` extracts an interaction draft.
2. `edit_interaction` stages updates to the latest matching interaction.
3. `search_past_interactions` retrieves database records only.
4. `schedule_follow_up` stages a dated reminder.
5. `suggest_talking_points` uses prior interaction history.
6. `compliance_flag_check` flags terms such as guarantee, cure, off-label, adverse event, and side effect.

## Safety notes

This is a demonstration project. A regulated production CRM would require authentication, audit trails, formal compliance workflows, role-based access, encryption, and robust adverse-event reporting.