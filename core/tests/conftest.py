"""Shared pytest configuration for the OTP test suite."""


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "natural_code: run without the fixed autouse OTP code fixture,"
        " so the real random code generator is exercised.",
    )
