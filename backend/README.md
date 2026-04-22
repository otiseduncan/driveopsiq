# SyferStack Backend

FastAPI backend for the SyferStack platform. The service ships with authentication, user management, and AI-assistant endpoints and is ready for local development or container deployment.

## Features
- FastAPI 0.1 style app with Pydantic v2 schemas and async SQLAlchemy models
- JWT authentication with refresh tokens, password reset helpers, and API keys
- Ready-to-use AI routes targeting OpenAI and Anthropic SDKs
- SQLite out of the box, configurable for PostgreSQL with asyncpg
- Docker and docker-compose definitions for dev and production topologies

## Prerequisites
- Python 3.11
- pip (recommended: `python -m pip install --upgrade pip`)
- Optional: Docker Desktop if you plan to use containers

## Local Development
1. **Clone and enter the project**
   ```powershell
   git clone https://github.com/yourusername/syferstack.git
   cd syferstack/backend
   ```
2. **Create a virtual environment**
   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   On macOS/Linux use `python3.11 -m venv .venv` and `source .venv/bin/activate`.
3. **Install dependencies**
   ```powershell
   pip install -e ".[dev]"
   ```
4. **Configure environment variables**
   ```powershell
   Copy-Item .env.example .env
   ```
   Update `.env` with real secrets before deploying. The defaults use SQLite so you can run immediately.
5. **Start the API**
   ```powershell
   uvicorn app.main:app --reload
   ```
   The service exposes docs at http://localhost:8000/docs when `DEBUG=true`.

## Running Tests
```powershell
pytest
```
Coverage reports (`htmlcov/`) are generated automatically via the pytest configuration in `pyproject.toml`.

## Docker Workflow
```powershell
docker compose up --build
```
This brings up the API, PostgreSQL, Redis, pgAdmin, and Redis Commander. For production-focused settings, use `docker compose -f docker-compose.prod.yml up --build`.

## Project Structure
```
backend/
├── app/
│   ├── api/          # FastAPI routers
│   ├── core/         # Config, database, security utilities
│   ├── models/       # SQLAlchemy models
│   ├── schemas/      # Pydantic schemas
│   └── main.py       # Application entrypoint
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Environment Variables
- Review `.env.example` for a full list of supported variables.
- `SECRET_KEY` **must** be replaced prior to deployment.
- `ENVIRONMENT` should be set to `production` for live deployments.
- Set `DATABASE_URL` to a PostgreSQL async URL (e.g., `postgresql+asyncpg://user:pass@host:5432/db`) when running against Postgres.

### Production Hardening Defaults
- Demo user seeding is disabled by default (`DEMO_MODE=false`).
- Production startup now fails fast if an insecure default `SECRET_KEY` is used.
- HSTS headers are only sent on HTTPS requests to avoid local-development browser lock-in.

## Next Steps
1. Configure CI to run `pytest` and formatting checks.
2. Add Alembic migrations once database schemas stabilize.
3. Implement email delivery for password reset and verification flows.
