# Market Intelligence Assistant

An AI-powered market research platform that scrapes competitor URLs, extracts structured intelligence using a GPT-4o analyst agent, verifies every claim with a GPT-4o judge agent, and streams live pipeline progress to the browser via Server-Sent Events.

---

## Features

- **Parallel URL scraping** — async httpx + Trafilatura extracts main article content from multiple URLs concurrently; falls back to BeautifulSoup4; SSRF protection with per-hop redirect validation
- **LangGraph pipeline** — StateGraph orchestrates scrape → analyze → judge → save with conditional retry (re-analyzes if hallucination score < 0.7, up to 2 retries)
- **LLM-as-a-judge** — second GPT-4o call fact-checks every claim in the report against original sources; returns a confidence score 0–1
- **LangSmith tracing** — `@traceable` on analyzer and judge agents; full prompt/response traces visible in LangSmith dashboard
- **Live SSE streaming** — Server-Sent Events push each pipeline step to the browser in real time
- **Prompt injection defense** — user inputs and scraped content sanitized before entering LLM prompts; tiktoken-accurate token budgeting
- **JWT authentication** — register/login with bcrypt passwords; 401 interceptor auto-redirects on token expiry
- **Rate limiting** — 10 login/min, 5 register/min per IP via slowapi
- **Security headers** — `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy` on every response
- **Input validation** — Pydantic validates URLs (http/https only, max 10), competitors (max 20), password strength policy
- **LLM output validation** — Pydantic models validate and coerce every LLM response; score clamped to [0, 1]; malformed JSON triggers safe fallback

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, SQLAlchemy 2.0 async, asyncpg, Alembic |
| AI Orchestration | LangGraph 0.2, LangChain Core |
| AI Agents | Azure OpenAI GPT-4o (analyst + judge) |
| Web Parsing | Trafilatura (primary), BeautifulSoup4 (fallback) |
| Observability | LangSmith (`@traceable`) |
| Frontend | React 18, Vite, TypeScript, React Router |
| Database | PostgreSQL 15 (asyncpg, connection pool tuned) |
| Auth | JWT (python-jose), bcrypt 4.0.1, slowapi rate limiting |
| Infra | Docker Compose, nginx, non-root containers |
| Deploy | Azure App Service + Azure Static Web Apps, GitHub Actions CI/CD |

---

## Quick Start (Docker)

```bash
# 1. Copy and fill in credentials
cp .env.example .env
# Edit .env — set AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, JWT_SECRET_KEY

# 2. Start all services (db + backend + frontend)
docker compose up --build

# 3. Open the app
open http://localhost:3001
```

Services:
- Frontend: http://localhost:3001
- Backend API: http://localhost:8000
- PostgreSQL: localhost:5432 (user: market, password: market, db: market)

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `AZURE_OPENAI_API_KEY` | Yes | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | Yes | `https://<resource>.openai.azure.com/` |
| `AZURE_OPENAI_DEPLOYMENT` | No | Model deployment name (default: `gpt-4o`) |
| `AZURE_OPENAI_API_VERSION` | No | API version (default: `2024-02-01`) |
| `JWT_SECRET_KEY` | Yes | Secret for JWT signing (min 32 chars) |
| `DATABASE_URL` | No | PostgreSQL URL (auto-set in Docker) |
| `LANGCHAIN_TRACING_V2` | No | `true` to enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | No | LangSmith API key |
| `LANGCHAIN_PROJECT` | No | LangSmith project name (default: `market-intel`) |

---

## Architecture

```
Browser (React + Vite)
  │
  ├─ REST (axios + 401 interceptor) ──────────► FastAPI
  │                                               │
  └─ EventSource SSE ─────────────────────────►  /runs/{id}/stream
                                                  │
                                          LangGraph StateGraph
                                          ┌───────────────────┐
                                          │  scrape_node       │ ← asyncio.gather (parallel)
                                          │      ↓             │
                                          │  analyze_node      │ ← GPT-4o + @traceable
                                          │      ↓             │
                                          │  judge_node        │ ← GPT-4o + @traceable
                                          │      ↓             │
                                          │  score < 0.7?      │
                                          │  retry ≤ 2× ──────►re_analyze_node
                                          │      ↓             │
                                          │  save_node         │ ← PostgreSQL
                                          └───────────────────┘
```

---

## LangGraph Pipeline

The pipeline is implemented as a LangGraph `StateGraph` with 5 nodes and conditional routing:

| Node | Responsibility |
|---|---|
| `scrape_node` | Parallel async scraping of all URLs; SSRF protection; content-type validation |
| `analyze_node` | GPT-4o extracts themes and competitor activities from scraped text |
| `judge_node` | GPT-4o verifies every claim against sources; returns score 0–1 |
| `re_analyze_node` | Triggered when score < 0.7; re-runs analysis (max 2 retries) |
| `save_node` | Validates source indices, sanitizes output, persists Report to PostgreSQL |

**Routing logic:**
- After scrape: if all URLs failed → `END` with error
- After judge: if `score < 0.7` and `retry_count < 2` → `re_analyze`, else → `save`

---

## LangSmith Tracing

When `LANGCHAIN_TRACING_V2=true`, every analyzer and judge call is traced:

```python
@traceable(name="market_analyzer", run_type="chain")
async def analyze(...): ...

@traceable(name="hallucination_judge", run_type="chain")
async def judge(...): ...
```

View traces at https://smith.langchain.com under project `market-intel`. Each trace shows prompt, response, token usage, and latency per LLM call.

---

## Security

| Layer | Implementation |
|---|---|
| SSRF protection | Async DNS resolution; blocks private IPs (RFC1918, link-local, AWS metadata); checks every redirect hop |
| Prompt injection | Sanitizes user inputs and scraped content; strips role prefixes and 15+ injection patterns |
| Token budget | tiktoken-accurate token counting; truncates sources to fit 124k token context window |
| Auth | bcrypt password hashing; JWT with 24h expiry; rate limiting on auth endpoints |
| Input validation | URL scheme enforcement; password complexity; max limits on all list inputs |
| Response validation | Pydantic validates all LLM outputs; score clamped to [0,1]; raw scraped content never sent to client |
| Container security | Non-root user in Docker; `.dockerignore` excludes `.env` and test files |

---

## Deployment

---

### Option 1 — Local (Docker Compose) ✅ Recommended for development

The fastest way to run everything with a single command.

**Prerequisites:** Docker Desktop installed and running.

```bash
# 1. Clone the repo
git clone https://github.com/srihari000/market-intel.git
cd market-intel

# 2. Create your .env file
cp .env.example .env
```

Edit `.env` and fill in your real values:
```env
AZURE_OPENAI_API_KEY=your-azure-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-01
JWT_SECRET_KEY=any-random-32-char-string
LANGCHAIN_TRACING_V2=false   # set true + add LANGCHAIN_API_KEY to enable LangSmith
```

```bash
# 3. Build and start all 3 services (db + backend + frontend)
docker compose up --build

# 4. Run DB migrations (first time only — auto-runs on start)
# Already handled by docker-compose backend command

# 5. Open the app
open http://localhost:3001
```

**Verify all services are running:**
```bash
docker compose ps
# db        → healthy
# backend   → running on port 8000
# frontend  → running on port 3001
```

**View logs:**
```bash
docker compose logs -f backend    # backend + pipeline logs
docker compose logs -f frontend   # nginx access logs
```

**Stop services:**
```bash
docker compose down          # stop containers, keep DB data
docker compose down -v       # stop + delete DB data (full reset)
```

---

### Option 2 — Local (Without Docker) for active backend development

Use this when you want hot-reload on backend code changes.

**Prerequisites:** Python 3.11+, Node 18+, PostgreSQL 15 running locally.

**Step 1 — PostgreSQL setup:**
```bash
psql -U postgres -c "CREATE USER market WITH PASSWORD 'market';"
psql -U postgres -c "CREATE DATABASE market OWNER market;"
```

**Step 2 — Backend:**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=postgresql+asyncpg://market:market@localhost:5432/market
export AZURE_OPENAI_API_KEY=your-key
export AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
export AZURE_OPENAI_DEPLOYMENT=gpt-4o
export AZURE_OPENAI_API_VERSION=2024-02-01
export JWT_SECRET_KEY=any-random-string
export LANGCHAIN_TRACING_V2=false

# Run migrations
alembic upgrade head

# Start backend with hot-reload
uvicorn app.main:app --reload --port 8000
```

**Step 3 — Frontend:**
```bash
cd frontend
npm install
npm run dev    # starts at http://localhost:5173, proxies API to localhost:8000
```

**Step 4 — Run tests:**
```bash
cd backend
.venv/bin/python -m pytest tests/ -v
```

Backend: http://localhost:8000 | Frontend: http://localhost:5173

---

### Option 3 — Production (Azure)

Backend deploys to **Azure App Service** (Python), frontend to **Azure Static Web Apps**.

#### Prerequisites
- Azure account with an active subscription
- Azure CLI installed: `az login`
- GitHub repo with the code pushed

#### Step 1 — Create Azure resources

```bash
# Set variables
RESOURCE_GROUP=market-intel-rg
LOCATION=eastus
APP_NAME=market-intel-api
STATIC_APP=market-intel-ui

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create PostgreSQL Flexible Server
az postgres flexible-server create \
  --resource-group $RESOURCE_GROUP \
  --name market-intel-db \
  --admin-user market \
  --admin-password YourStrongPassword123! \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --location $LOCATION

# Create the database
az postgres flexible-server db create \
  --resource-group $RESOURCE_GROUP \
  --server-name market-intel-db \
  --database-name market

# Create App Service Plan (Linux B1 — free tier eligible)
az appservice plan create \
  --name market-intel-plan \
  --resource-group $RESOURCE_GROUP \
  --sku B1 \
  --is-linux

# Create Web App
az webapp create \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --plan market-intel-plan \
  --runtime "PYTHON:3.11"
```

#### Step 2 — Configure backend environment variables

```bash
az webapp config appsettings set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --settings \
    DATABASE_URL="postgresql+asyncpg://market:YourStrongPassword123!@market-intel-db.postgres.database.azure.com/market" \
    AZURE_OPENAI_API_KEY="your-key" \
    AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/" \
    AZURE_OPENAI_DEPLOYMENT="gpt-4o" \
    AZURE_OPENAI_API_VERSION="2024-02-01" \
    JWT_SECRET_KEY="your-production-secret-min-32-chars" \
    CORS_ORIGINS="https://your-static-app.azurestaticapps.net" \
    LANGCHAIN_TRACING_V2="false"
```

#### Step 3 — Get publish profile for GitHub Actions

```bash
# Download publish profile (paste content into GitHub secret)
az webapp deployment list-publishing-profiles \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --xml
```

#### Step 4 — Create Azure Static Web App (frontend)

```bash
az staticwebapp create \
  --name $STATIC_APP \
  --resource-group $RESOURCE_GROUP \
  --location "eastus2" \
  --source https://github.com/srihari000/market-intel \
  --branch main \
  --app-location "/frontend" \
  --output-location "dist" \
  --login-with-github
```

This auto-creates the GitHub Actions workflow for frontend deployment.

#### Step 5 — Add GitHub Actions secrets

Go to your GitHub repo → **Settings → Secrets and variables → Actions** and add:

| Secret | How to get it |
|---|---|
| `AZURE_BACKEND_APP_NAME` | The `$APP_NAME` value you set above |
| `AZURE_BACKEND_PUBLISH_PROFILE` | XML output from Step 3 |
| `AZURE_STATIC_WEB_APPS_API_TOKEN` | Auto-created by Step 4 (check GitHub Actions) |
| `VITE_API_URL` | `https://<APP_NAME>.azurewebsites.net` |

#### Step 6 — Deploy

```bash
# Push to main — GitHub Actions handles the rest
git push origin main
```

Pipeline: `push to main` → run tests → build frontend → deploy backend → deploy frontend

**Production URLs:**
- Frontend: `https://<STATIC_APP>.azurestaticapps.net`
- Backend API: `https://<APP_NAME>.azurewebsites.net`

---

## API Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | No | Register (rate limited: 5/min) |
| POST | `/auth/login` | No | Login (rate limited: 10/min) |
| GET | `/auth/me` | JWT | Current user |
| POST | `/runs` | JWT | Create analysis run |
| GET | `/runs` | JWT | List runs |
| GET | `/runs/{id}` | JWT | Get run status |
| GET | `/runs/{id}/stream` | `?token=` | SSE pipeline stream |
| GET | `/runs/{id}/report` | JWT | Fetch completed report |
| DELETE | `/runs/{id}` | JWT | Delete run |

---

## Future Improvements

- **Redis caching** — cache analysis results by `SHA256(urls + competitors + topics)` with 1h TTL; eliminates repeat LLM calls and reduces Azure OpenAI cost by ~60% for duplicate queries
- **Model routing** — use GPT-4o for analyzer (complex reasoning) and GPT-4o-mini for judge (simpler fact-checking); judge is ~70% of token cost so switching saves ~65% per run
- **Vector store / RAG** — enable pgvector on existing PostgreSQL; chunk documents at ingest; retrieve only relevant chunks at query time; unlocks analysis of 1000-page documents currently truncated at 50k chars
- **Conversational follow-up** — after report generation, allow users to ask questions like "What is OpenAI's pricing strategy?" using the report + RAG-retrieved source chunks; reuses existing SSE streaming
- **Background job queue** — move pipeline to Celery + Redis so LLM calls don't block uvicorn workers; enables horizontal scaling of workers independently from the API
- **Scheduled analysis** — cron-based runs on saved URL sets with diff reports highlighting what changed since the last run; email/push notification on completion

---

