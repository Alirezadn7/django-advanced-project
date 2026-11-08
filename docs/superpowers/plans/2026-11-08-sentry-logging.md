# Sentry & Logging Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate Sentry and standard Python logging into Django settings so that exceptions and application logs are recorded, while remaining a safe no-op when unconfigured.

**Architecture:** Use `sentry-sdk` with `DjangoIntegration` and `LoggingIntegration` loaded conditionally inside `core/core/settings/base.py` based on `SENTRY_DSN`. Configure Django's `LOGGING` dictionary with standard stream formatting so that logs flow seamlessly through the Python logger to console and Sentry.

**Tech Stack:** Python 3.13, Django 4.2+, `sentry-sdk`, `python-decouple`, `pytest-django`.

**Spec:** `docs/superpowers/specs/2026-11-08-sentry-logging-design.md`

## Global Constraints
- Sentry integration must not raise an error or halt execution if `SENTRY_DSN` is empty or missing.
- Default PII (`send_default_pii`) must remain `False` to prevent leaking credentials or sensitive user data.
- Environment variables must be parsed using `python-decouple` (`config`).

## Review Focus
- Empty `SENTRY_DSN` scenario does not initialize Sentry or raise any exception.
- Non-empty `SENTRY_DSN` initializes `sentry_sdk.init` with `DjangoIntegration` and `LoggingIntegration`.
- Django `LOGGING` dictionary is properly configured with a console stream handler and standard formatter.
- Application loggers (`accounts`, `blog`, `core`) propagate properly to handlers.
- Existing 51 tests continue to pass without regression.

---

### Task 1: Environment & Dependency Configuration

**Files:**
- Modify: `requirements.txt`
- Modify: `.env.example`

**Interfaces:**
- Consumes: None
- Produces: `sentry-sdk` dependency declaration and `SENTRY_*` environment template keys.

- [ ] **Step 1: Add `sentry-sdk` to `requirements.txt`**
Add `sentry-sdk~=2.0` to `requirements.txt`.

- [ ] **Step 2: Add Sentry configuration variables to `.env.example`**
Append Sentry settings to `.env.example`:
```env
# Sentry Observability & Error Monitoring
SENTRY_DSN=
SENTRY_ENVIRONMENT=development
SENTRY_TRACES_SAMPLE_RATE=1.0
```

- [ ] **Step 3: Install `sentry-sdk` in the virtual environment**
Run: `venv\Scripts\pip install sentry-sdk~=2.0`
Expected: Successfully installed `sentry-sdk`.

- [ ] **Step 4: Verify `sentry_sdk` can be imported in Python**
Run: `venv\Scripts\python -c "import sentry_sdk; print(sentry_sdk.__version__)"`
Expected: Version output starting with `2.`.

- [ ] **Step 5: Commit changes**
Run:
```bash
git add requirements.txt .env.example
git commit -m "chore: add sentry-sdk dependency and env templates"
```

---

### Task 2: Implement Sentry Initialization & Django Logging Configuration

**Files:**
- Modify: `core/core/settings/base.py`

**Interfaces:**
- Consumes: `decouple.config`, `sentry_sdk`, `sentry_sdk.integrations.django.DjangoIntegration`, `sentry_sdk.integrations.logging.LoggingIntegration`.
- Produces: `LOGGING` dictionary and conditional `sentry_sdk.init` execution.

- [ ] **Step 1: Write failing test in `core/tests/test_sentry_logging.py`**
Create `core/tests/test_sentry_logging.py` with tests verifying `settings.LOGGING` and Sentry setup functions:
```python
import logging
from unittest.mock import patch
from django.conf import settings
import pytest

def test_logging_settings_defined():
    assert hasattr(settings, "LOGGING")
    assert "console" in settings.LOGGING.get("handlers", {})
    assert "standard" in settings.LOGGING.get("formatters", {})

def test_logger_can_emit():
    logger = logging.getLogger("core.test")
    logger.info("Test info message")
    logger.error("Test error message")
```

- [ ] **Step 2: Run test to verify failure**
Run: `venv\Scripts\pytest core/tests/test_sentry_logging.py`
Expected: FAIL (assertion error: `settings` does not have `LOGGING`).

- [ ] **Step 3: Update `core/core/settings/base.py`**
In `core/core/settings/base.py`:
1. Import `logging`, `sentry_sdk`, `DjangoIntegration`, `LoggingIntegration`.
2. Read `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `SENTRY_TRACES_SAMPLE_RATE` using `config`.
3. Wrap `sentry_sdk.init(...)` conditionally on `if SENTRY_DSN:`.
4. Define the `LOGGING` dict with `version=1`, `disable_existing_loggers=False`, `formatters`, `handlers`, and `loggers` for `django`, `core`, `accounts`, `blog`.

- [ ] **Step 4: Run test to verify it passes**
Run: `venv\Scripts\pytest core/tests/test_sentry_logging.py`
Expected: PASS.

- [ ] **Step 5: Commit changes**
Run:
```bash
git add core/core/settings/base.py core/tests/test_sentry_logging.py
git commit -m "feat: configure Sentry initialization and Django logging in base settings"
```

---

### Task 3: Comprehensive Sentry & Logging Tests and Regression Check

**Files:**
- Modify: `core/tests/test_sentry_logging.py`

**Interfaces:**
- Consumes: `core.core.settings.base`, `sentry_sdk`
- Produces: Complete automated test coverage for DSN initialization, no-op behavior, and logging integration.

- [ ] **Step 1: Add unit tests for conditional Sentry init and breadcrumbs**
In `core/tests/test_sentry_logging.py`, add:
1. `test_sentry_init_with_dsn_invoked`: Mock `sentry_sdk.init` and test custom initialization logic.
2. `test_empty_dsn_does_not_initialize`: Verify `sentry_sdk.init` is not called when DSN is empty.
3. `test_unhandled_exception_logging`: Verify logging a critical/error message does not crash the application.

- [ ] **Step 2: Run all tests in test suite**
Run: `venv\Scripts\pytest`
Expected: All tests pass (51 existing + new tests).

- [ ] **Step 3: Commit changes**
Run:
```bash
git add core/tests/test_sentry_logging.py
git commit -m "test: add comprehensive unit tests for Sentry and logging"
```
