# Deployment Guide

## Development Setup

### Prerequisites

- Python 3.12+
- Node.js 20+
- OmniRoute AI gateway (optional — set `ALLOW_MOCK_AI_DATA=true` to develop without it)

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Edit .env with your settings, then:
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in a browser.

## Production Architecture

```
                    ┌─────────────┐
                    │   CDN       │
                    │  (optional) │
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              │                         │
        ┌─────┴──────┐          ┌──────┴─────┐
        │  Frontend   │          │   Backend   │
        │  (Vite/React│          │  (FastAPI)  │
        │   S3/CDN)   │          │   Docker    │
        └─────────────┘          └──────┬──────┘
                                        │
                              ┌─────────┴─────────┐
                              │                   │
                        ┌─────┴─────┐     ┌──────┴─────┐
                        │ PostgreSQL│     │   Redis    │
                        │ (future)  │     │  (future)  │
                        └───────────┘     └────────────┘
```

### Current (v0.9)

- Backend: Python FastAPI, JSON file storage, single process
- Frontend: React + Vite, static build

### Target (v1.0)

- Backend: Containerized FastAPI behind nginx, PostgreSQL, Redis for job queue
- Frontend: Static files served via CDN
- File storage: S3-compatible object storage
- AI: OmniRoute gateway (external)

## Environment Variables

See `.env.example` for all variables. Key settings:

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | Resume Studio AI | Application name |
| `DEBUG` | false | Enable debug mode |
| `OMNIROUTE_API_URL` | http://localhost:20128/v1/... | AI inference endpoint |
| `OMNIROUTE_API_KEY` | (empty) | AI gateway API key |
| `OMNIROUTE_MODEL` | kiro/claude-haiku-4.5 | AI model identifier |
| `OMNIROUTE_TIMEOUT` | 60 | AI request timeout (seconds) |
| `OMNIROUTE_MAX_RETRIES` | 1 | AI retry count |
| `JWT_SECRET_KEY` | (required) | 256-bit key for JWT signing |
| `JWT_ACCESS_EXPIRE_MINUTES` | 15 | Access token lifetime |
| `JWT_REFRESH_EXPIRE_DAYS` | 7 | Refresh token lifetime |
| `ALLOW_MOCK_AI_DATA` | false | Enable mock AI fallback |
| `MAX_UPLOAD_SIZE` | 10485760 | Max file upload in bytes |

## Backend Deployment

### Docker (Recommended)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t resume-studio-ai .
docker run -p 8000:8000 -v $(pwd)/storage:/app/storage resume-studio-ai
```

### Manual

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Frontend Deployment

```bash
cd frontend
npm install
npm run build
# Output in frontend/dist/ — serve with any static server
```

Serve the `dist/` directory via nginx, S3, Cloudflare Pages, or Vercel.

## CI/CD Recommendations

### GitHub Actions (Backend)

```yaml
name: Backend CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r backend/requirements.txt
      - run: cd backend && python -m pytest
```

### GitHub Actions (Frontend)

```yaml
name: Frontend CI
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: cd frontend && npm ci
      - run: cd frontend && npm run lint
      - run: cd frontend && npm run build
```

## Production Checklist

- [ ] Set `DEBUG=false` in `.env`
- [ ] Set a strong `JWT_SECRET_KEY` (generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
- [ ] Set `ALLOW_MOCK_AI_DATA=false`
- [ ] Configure `OMNIROUTE_API_URL` and `OMNIROUTE_API_KEY`
- [ ] Configure CORS origins (restrict from `*` to your domain)
- [ ] Run database migration (if using PostgreSQL)
- [ ] Set up monitoring and alerting
- [ ] Configure automated backups of `storage/`
- [ ] Run full test suite
