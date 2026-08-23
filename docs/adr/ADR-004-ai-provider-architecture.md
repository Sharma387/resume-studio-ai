# ADR-004: AI Provider Architecture

**Context:** RSAI requires AI-powered resume parsing, ATS matching, cover letter generation, and writing suggestions.

**Decision:** Abstract AI integration behind `OmniRouteService` with a shared retry layer (`call_with_retry`) and JSON extraction utilities. All AI calls go through the same retry/timeout pipeline.

**Alternatives considered:** Direct API calls per service (duplicated retry logic), multiple AI providers simultanously (premature optimization).

**Consequences:** Single AI provider (OmniRoute). Adding a new provider requires implementing a new service class. All AI features share consistent error handling and logging.
