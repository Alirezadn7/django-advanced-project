import logging
from unittest.mock import patch
from django.conf import settings
import pytest
from core.settings.base import init_sentry

def test_logging_settings_defined():
    assert hasattr(settings, "LOGGING"), "LOGGING configuration missing from settings"
    assert "console" in settings.LOGGING.get("handlers", {})
    assert "standard" in settings.LOGGING.get("formatters", {})
    assert "core" in settings.LOGGING.get("loggers", {})
    assert "accounts" in settings.LOGGING.get("loggers", {})
    assert "blog" in settings.LOGGING.get("loggers", {})

def test_logger_can_emit():
    for logger_name in ["core", "accounts", "blog"]:
        logger = logging.getLogger(logger_name)
        logger.info("Test info message for %s", logger_name)
        logger.warning("Test warning message for %s", logger_name)
        logger.error("Test error message for %s", logger_name)

def test_init_sentry_with_dsn_calls_sdk_init():
    with patch("sentry_sdk.init") as mock_init:
        result = init_sentry(
            dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
            environment="test",
            traces_sample_rate=0.5,
        )
        assert result is True
        assert mock_init.called
        kwargs = mock_init.call_args.kwargs
        assert kwargs["dsn"] == "https://examplePublicKey@o0.ingest.sentry.io/0"
        assert kwargs["environment"] == "test"
        assert kwargs["traces_sample_rate"] == 0.5
        assert kwargs["send_default_pii"] is False
        assert len(kwargs["integrations"]) == 2

def test_init_sentry_without_dsn_is_noop():
    with patch("sentry_sdk.init") as mock_init:
        result = init_sentry(dsn="", environment="test")
        assert result is False
        assert not mock_init.called
