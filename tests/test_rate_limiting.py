from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import RateLimitMiddleware


def test_rate_limiter_blocks_excess_requests():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, limit=2, window_seconds=60, paths=["/protected"])

    @app.get("/protected")
    def protected():
        return {"ok": True}

    client = TestClient(app)

    assert client.get("/protected").status_code == 200
    assert client.get("/protected").status_code == 200
    assert client.get("/protected").status_code == 429
