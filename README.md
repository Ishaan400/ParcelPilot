# ParcelPilot Internal Support Operations AI Agent

An AI-powered internal support agent for CalQuity's ParcelPilot platform. The agent helps support staff answer customer inquiries using retrieval-augmented generation (RAG), tool use, and automated actions.

## Tech Stack

- **Backend:** FastAPI
- **UI:** Streamlit
- **LLM:** Groq (OpenAI-compatible API)

## Setup

Run all commands from the **repository root** (`CalQuity/`).

### 1. Create and activate a virtual environment

**Linux / macOS**

```bash
python -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell)**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt)**

```bat
python -m venv .venv
.venv\Scripts\activate.bat
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and set `GROQ_API_KEY` (required for a live agent).

**Linux / macOS**

```bash
cp .env.example .env
```

**Windows (PowerShell)**

```powershell
Copy-Item .env.example .env
```

Edit `.env`:

```
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b
```

`GROQ_MODEL` is optional. If omitted, the app defaults to `openai/gpt-oss-120b`. The OpenAI Python SDK talks to Groq at `https://api.groq.com/openai/v1`.

## Run

Use two terminals, both at the repository root, with the virtual environment activated.

**Terminal 1 — FastAPI backend**

```bash
uvicorn app.api.main:app --reload
```

The API listens on `http://127.0.0.1:8000`.

**Terminal 2 — Streamlit UI**

```bash
streamlit run app/ui/streamlit_app.py
```

The UI calls `POST /chat` on `http://127.0.0.1:8000` by default. Override with `PARCELPILOT_API_URL` or the API URL field in the sidebar.

## Project Structure

See the repository tree for layout details. Core application code lives under `app/`.
