from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.campaigns import decode_pubsub_push
from app.http_api import _safe_campaign_id, attach_flock_routes


def test_safe_campaign_id() -> None:
    assert _safe_campaign_id("peak-gym-71d02b5c")
    assert _safe_campaign_id("noya-salon-a1b2c3d4")
    assert not _safe_campaign_id("../etc/passwd")
    assert not _safe_campaign_id("still.png")


def _client() -> TestClient:
    app = FastAPI()
    attach_flock_routes(app)
    return TestClient(app)


def test_demo_route_is_public() -> None:
    res = _client().get("/demo")
    assert res.status_code == 200
    assert "Mira" in res.text
    assert "do not autopost" in res.text.lower() or "never autopost" in res.text.lower()


def test_ops_requires_token(monkeypatch) -> None:
    monkeypatch.delenv("OPS_TOKEN", raising=False)
    res = _client().get("/ops")
    assert res.status_code == 501


def test_telegram_webhook_501_without_token(monkeypatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    res = _client().post("/v1/telegram/webhook", json={"message": {}})
    assert res.status_code == 501


def test_telegram_webhook_403_bad_secret(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "shh")
    res = _client().post("/v1/telegram/webhook", json={"update_id": 1})
    assert res.status_code == 403


def test_decode_pubsub_push_payload() -> None:
    import base64
    import json

    body = {
        "campaignId": "c1",
        "step": "scout",
        "pipeline": ["scout"],
        "attempt": 1,
        "idempotencyKey": "c1:scout:1",
    }
    encoded = base64.b64encode(json.dumps(body).encode("utf-8")).decode("ascii")
    envelope = {"message": {"data": encoded, "messageId": "m1"}}
    out = decode_pubsub_push(envelope)
    assert out["campaignId"] == "c1"
    assert out["step"] == "scout"
    assert out["messageId"] == "m1"
