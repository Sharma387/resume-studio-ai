# Resume Studio AI — Enterprise Resume Management Platform

**Version:** 1.0.0-beta (2026-07-26)

RSAI is a full-stack AI-powered resume management platform with PostgreSQL storage, enterprise administration, and OmniRoute AI integration.

## Quick Start

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # edit JWT_SECRET_KEY and DATABASE_URL
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

### Creating the First Administrator

```bash
cd backend && source .venv/bin/activate
python scripts/create_admin.py --email admin@example.com --password "SecurePass123!" --name "Admin"
```

## Architecture

```
Frontend (React + TypeScript + Vite + MUI)
       ↓ HTTP/JSON
API (FastAPI + Pydantic)
       ↓
Services (AuthService, UserService, AdminService, ParserService, ...)
       ↓
Repository Factory
       ↓
14 PostgreSQL Repositories
       ↓
PostgreSQL 16 Database
```

## Key Features

| Feature | Status |
|---|---|
| AI Resume Parsing | ✅ Production |
| AI Cover Letters | ✅ Production |
| AI ATS Matching | ✅ Production |
| AI Writing Suggestions | ✅ Production |
| Resume Rendering & Export (RenderTree → PDF/DOCX/HTML) | ✅ Production |
| Application Tracking | ✅ Production |
| Interview Preparation | ✅ Production |
| PostgreSQL Storage | ✅ Production |
| Administrator Console | ✅ Production |
| User Management | ✅ Production |
| CI/CD Pipeline | ✅ Production |
| Docker Deployment | ✅ Production |

## Documentation

| Document | Location |
|---|---|
| Architecture | `docs/ARCHITECTURE.md` |
| API Reference | `docs/API.md` |
| AI Integration | `docs/AI.md` |
| PostgreSQL Setup | `docs/postgresql/Setup.md` |
| Production Deployment | `docs/postgresql/ProductionDeployment.md` |
| CI/CD | `docs/postgresql/ContinuousIntegration.md` |
| Security | `docs/security/AdminAuthentication.md` |
| Operations | `docs/operations/ConfigurationDiagnostics.md` |
| Storage | `docs/STORAGE.md` |

## Test Suite

```
322 passed, 1 skipped, 20 errors (PG integration tests)
```

## License

Proprietary — All rights reserved.
