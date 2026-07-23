# Resume Studio AI — Frontend

React + TypeScript + Vite + Material UI frontend for the Resume Studio AI platform.

## Tech Stack

- **React 19** with TypeScript (strict mode)
- **Material UI v9** with Emotion styling
- **Vite 8** for development and build
- **oxlint** for linting
- **react-router-dom** for routing

## Project Structure

```
src/
├── components/
│   ├── review/       # Review page section editors (PersonalInfo, Skills, Experience, etc.)
│   └── ui/           # Reusable UI components (EmptyState, SkeletonLoader, ConfirmDialog, etc.)
├── pages/
│   ├── Home.tsx      # Landing page with upload
│   └── ReviewPage.tsx # Resume review and editing
├── services/         # API client layer
├── types/            # TypeScript interfaces matching backend Pydantic models
├── contexts/         # Theme context (dark/light mode)
├── App.tsx           # Routing configuration
└── main.tsx          # Entry point
```

## Scripts

| Command | Description |
|---|---|
| `npm run dev` | Start development server on port 5173 |
| `npm run build` | TypeScript check + production build to `dist/` |
| `npm run lint` | Run oxlint |
| `npm run preview` | Preview production build |

## API Configuration

The frontend connects to the backend at `http://localhost:8000/api/v1`. This is configured in the service files under `src/services/`.

## Routing

| Path | Component | Description |
|---|---|---|
| `/` | Home | Landing page with upload |
| `/review?file=` | ReviewPage | Resume review and editing |
