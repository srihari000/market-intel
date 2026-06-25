# Market Intelligence Assistant

An AI-powered web application that scrapes URLs, extracts competitive insights using GPT-4o, and runs an LLM-as-a-judge hallucination check — all streamed live to the browser.

## Features

- **URL scraping** — async httpx + BeautifulSoup4 scrapes any public page
- **Market analysis** — GPT-4o extracts themes and competitor activity from scraped text
- **Hallucination verification** — same GPT-4o model with a judge system prompt scores every claim
- **Live streaming** — Server-Sent Events push pipeline progress in real time
- **JWT auth** — register/login with bcrypt passwords

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, SQLAlchemy 2.0 async, asyncpg, Alembic |
| AI | Azure OpenAI GPT-4o (analysis + judge) |
| Frontend | React 18, Vite, TypeScript, React Router |
| Database | PostgreSQL 15 |
| Auth | JWT (python-jose), bcrypt 4.0.1 |
| Deploy | Azure App Service + Azure Static Web Apps |

## Quick Start (Docker)

```bash
# Copy and fill in your Azure OpenAI credentials
cp .env.example .env

docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

## Local Development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/market
export AZURE_OPENAI_API_KEY=...
export AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
export JWT_SECRET_KEY=your-secret

alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev    # proxies /auth and /runs to localhost:8000
```

### Tests

```bash
cd backend
.venv/bin/python -m pytest tests/ -v
```

All 17 tests pass (auth, runs CRUD, scraper, analyzer, pipeline).

## Environment Variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL async URL |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_DEPLOYMENT` | Model deployment name (default: `gpt-4o`) |
| `AZURE_OPENAI_API_VERSION` | API version (default: `2024-02-01`) |
| `JWT_SECRET_KEY` | Secret for JWT signing |

## Architecture

```
Browser  →  React SPA (Vite)
              │
              ├── REST calls (axios) → FastAPI backend
              └── EventSource (SSE)  → /runs/{id}/stream
                                          │
                                          ├── scrape_url()   httpx + BS4
                                          ├── analyze()      GPT-4o (analyst prompt)
                                          └── judge()        GPT-4o (judge prompt)
                                                  │
                                              PostgreSQL
```

## Pipeline Flow

1. User submits title, competitors, topics, and source URLs
2. Backend creates a `Run` record (status: `pending`)
3. Browser opens an SSE connection to `/runs/{id}/stream`
4. Pipeline runs:
   - Scrapes each URL concurrently
   - Sends scraped text + competitors/topics to GPT-4o analyst
   - Sends analysis + sources to GPT-4o judge for hallucination scoring
   - Persists `Report` to DB
5. SSE emits `complete` event; browser fetches and renders the report

## Deployment

GitHub Actions (`.github/workflows/deploy.yml`) runs backend tests and frontend build on every PR, then deploys to Azure on merge to `main`.

Required secrets: `AZURE_BACKEND_APP_NAME`, `AZURE_BACKEND_PUBLISH_PROFILE`, `AZURE_STATIC_WEB_APPS_API_TOKEN`, `VITE_API_URL`.
