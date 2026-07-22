# Architecture

## Overview

Resume Studio AI follows a layered architecture:

```
Frontend (React + MUI)
    │
    ▼ HTTP (REST JSON)
Backend (FastAPI + Python)
    ├── API Layer (routers)
    ├── Service Layer (business logic)
    ├── AI Core (shared AI infrastructure)
    ├── Storage Layer (JSON files → future PostgreSQL)
    └── Model Layer (Pydantic schemas)
    │
    ▼
OmniRoute Gateway (AI inference)
```

## Key Design Decisions

| Decision | Rationale |
|---|---|
| JSON storage (current) | Simplicity for MVP; repository pattern ready for PostgreSQL |
| Repository pattern | Swap storage backend without changing business logic |
| Externalized prompts | Modify AI behavior without code changes |
| `ai_core` package | Shared retry/parse/error logic eliminates duplication |
| Template Engine | Add new PDF themes without touching generation code |
| OwnedResource model | User isolation prepared from day one |

## Directory Structure

```
backend/
├── app/
│   ├── api/v1/          # Route handlers
│   ├── core/            # Config, logging, exceptions, middleware
│   ├── models/          # Pydantic schemas
│   └── services/        # Business logic + AI + storage
├── storage/             # JSON data files
├── tests/               # pytest suite
└── prompts/             # AI prompt templates
frontend/
├── src/
│   ├── components/      # React components
│   ├── pages/           # Route pages
│   ├── services/        # API client layer
│   ├── types/           # TypeScript interfaces
│   └── contexts/        # React contexts (auth, theme)
docs/                    # Project documentation
```
