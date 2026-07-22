# AI Architecture

## Overview

All AI interactions flow through the `ai_core` shared package, which provides:

- Retry logic with configurable attempts
- JSON extraction from AI responses (strips markdown)
- Structured logging with timing
- Consistent error handling

## Flow

```
Service → PromptService.build_*_prompt() → call_with_retry() → OmniRouteService
                                                                     │
                                                                     ▼
                                                               OmniRoute API
                                                                     │
                                                                     ▼
Service ← parse_response() ← extract_json() ← raw response
```

## Prompt Templates

All prompts are in `prompts/` directory:

| File | Used By |
|---|---|
| `resume_parser_system.md` | Resume parsing |
| `resume_parser_user.md` | Resume parsing |
| `resume_matcher_system.md` | ATS matching |
| `resume_matcher_user.md` | ATS matching |
| `resume_writer_system.md` | Resume writer |
| `resume_writer_user.md` | Resume writer |
| `cover_letter_system.md` | Cover letter generation |
| `cover_letter_user.md` | Cover letter generation |
| `interview_questions_system.md` | Question generation |
| `interview_questions_user.md` | Question generation |
| `interview_answer_coach_system.md` | Answer coaching |
| `interview_readiness_system.md` | Readiness assessment |
| `interview_summary_system.md` | Session summary |

## Retry Strategy

- Default: 1 retry (configurable via `OMNIROUTE_MAX_RETRIES`)
- Retries on: `JSONDecodeError`, `ValidationError`, `OmniRouteError`
- Fallback: mock data returned when AI is unavailable

## Adding a New AI Feature

1. Create prompt templates in `prompts/`
2. Add `build_*_prompt()` to `PromptService`
3. Use `call_with_retry()` from `ai_core`
4. Create service function with `parse_response` callback
