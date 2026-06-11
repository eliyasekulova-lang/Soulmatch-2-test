import os

import pytest


# Ensure tests run with explicit test-mode settings before app imports.
# Use direct assignment (not setdefault) so local .env values don't leak into tests.
os.environ["APP_ENV"] = "test"
os.environ["ADMIN_EMAILS"] = "admin@example.com"
os.environ["AUTH_RATE_LIMIT_PER_MINUTE"] = "10000"
os.environ["AUTH_REFRESH_RATE_LIMIT_PER_MINUTE"] = "10000"
os.environ["MESSAGE_SEND_RATE_LIMIT_PER_MINUTE"] = "10000"


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    from app.rate_limit import rate_limiter

    rate_limiter.reset()
    yield
    rate_limiter.reset()
