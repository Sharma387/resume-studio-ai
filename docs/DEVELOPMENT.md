# Development Guide

## Prerequisites

- Python 3.12+
- Node.js 20+
- OmniRoute (AI gateway) running locally on port 20128

## Setup

```bash
# Clone and install
git clone https://github.com/Sharma387/resume-studio-ai.git
cd resume-studio-ai

# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Frontend
cd frontend
npm install
```

## Running

```bash
# Backend (http://localhost:8000)
make dev-backend

# Frontend (http://localhost:5173)  
make dev-frontend

# Both
make dev
```

## Testing

```bash
# Backend tests
make test

# Frontend lint
make lint

# Frontend build
make build
```

## Project Structure

```
backend/
├── app/
│   ├── api/v1/          # Route handlers (one file per resource)
│   ├── core/            # Config, logging, exceptions, middleware
│   ├── models/          # Pydantic schemas
│   └── services/        # Business logic
│       ├── ai_core/     # Shared AI infrastructure
│       ├── document/    # Document extraction pipeline
│       ├── pdf_templates/  # PDF theme engine
│       └── repositories/  # Data access layer
├── storage/             # JSON data (ignored by git)
├── tests/               # pytest tests
└── prompts/             # AI prompt templates
frontend/
├── src/
│   ├── components/      # UI components
│   │   └── review/      # Review page sections
│   ├── pages/           # Route pages
│   ├── services/        # API clients
│   ├── types/           # TypeScript interfaces
│   └── contexts/        # React contexts
docs/                    # Documentation
```

## Commit Convention

```
<type>(<scope>): <description>

Types: feat, fix, refactor, chore, docs, test, style
Scope: rsai-XXX or module name
```

## Architecture Principles

1. **Repository pattern** — data access is abstracted behind interfaces
2. **Externalized prompts** — AI behavior is configurable without code changes
3. **Shared AI core** — all AI services use `call_with_retry()` from `ai_core`
4. **No data duplication** — applications reference resumes/cover letters by ID
5. **Backward compatibility** — existing APIs never break
