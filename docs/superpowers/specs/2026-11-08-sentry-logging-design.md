# Design Document: Sentry & Logging Integration

## Intent & Why
To capture runtime exceptions and application logs in real-time using Sentry, providing observability and alerting for both development testing (when enabled) and production environments without imposing performance penalties or errors when unconfigured.

## Goals
- Add `sentry-sdk` dependency to `requirements.txt`.
- Configure `sentry_sdk.init` in `core/core/settings/base.py` conditional on `SENTRY_DSN`.
- Configure `LoggingIntegration` so that logs (`INFO` and above) are breadcrumbs, while `ERROR`/`CRITICAL` logs generate Sentry issues.
- Establish a clean, standard Django `LOGGING` dictionary for console output and app-level loggers.
- Expose configuration knobs via `python-decouple` in `.env.example` (`SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `SENTRY_TRACES_SAMPLE_RATE`).
- Provide an isolated test/verification mechanism to verify Sentry event capture without polluting production logs.

## Non-Goals & Anti-Goals
- Non-goal: Hardcoding Sentry credentials or making Sentry mandatory for local run without DSN.
- Anti-goal: Crashing Django startup if `SENTRY_DSN` is empty or invalid.
- Anti-goal: Capturing sensitive credentials or passwords in Sentry (ensure PII filtering / default hygiene).

## Approaches Considered
- **Approach 1 (Chosen): Conditional initialization in `base.py` with `LoggingIntegration` and Django `LOGGING`.**
  - *Pros:* Works seamlessly in all environments when DSN is present; no-op when absent; full integration between Python logging and Sentry breadcrumbs/events.
  - *Trade-off:* Shared setup across settings, requires defensive environment variable checking.
- **Approach 2: Production-only initialization in `production.py`.**
  - *Pros:* Zero Sentry presence during development.
  - *Trade-off:* Harder to verify integration locally before deploying to production.

## Selected Architecture & Implementation Details
1. **Dependency:** Add `sentry-sdk>=2.0.0` to `requirements.txt`.
2. **Environment Variables (.env.example):**
   - `SENTRY_DSN`: Sentry DSN string (default: empty).
   - `SENTRY_ENVIRONMENT`: e.g. `development` / `production` (default: `development` or dynamic).
   - `SENTRY_TRACES_SAMPLE_RATE`: float (default: `1.0` in dev, configurable for production).
3. **Settings (`core/core/settings/base.py`):**
   - Read `SENTRY_DSN` via `config("SENTRY_DSN", default="")`.
   - If `SENTRY_DSN` is provided, initialize `sentry_sdk.init(...)` with `DjangoIntegration()` and `LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)`.
   - Add standard `LOGGING` setting with `console` handler and formatters.
4. **Verification:**
   - Add a triggerable test view or management command / unit test that triggers a logger error and captures it.
