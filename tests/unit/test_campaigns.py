from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.campaigns import create_campaign, decode_pubsub_push
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
    assert "Glen" in res.text
    assert "google-listing-eaf57cae" in res.text
    assert "Mira" not in res.text
    assert "do not autopost" in res.text.lower() or "never autopost" in res.text.lower()
    assert "Telegram is the meeting" not in res.text
    assert "Open Telegram" not in res.text


def test_home_is_capture_form() -> None:
    res = _client().get("/")
    assert res.status_code == 200
    assert 'name="url"' in res.text
    assert "required" in res.text
    assert "Open Telegram" not in res.text
    assert "t.me" not in res.text.lower()


def test_home_prefills_query() -> None:
    res = _client().get("/?name=Glen&goal=cupcakes&geo=Indiranagar")
    assert res.status_code == 200
    assert "Glen" in res.text
    assert "cupcakes" in res.text
    assert "Indiranagar" in res.text


def test_run_room_bad_id() -> None:
    res = _client().get("/r/bad")
    assert res.status_code == 400


def test_run_room_missing_key(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.http_api.ledger.get_campaign",
        lambda _id: {
            "id": "listing-abcd1234",
            "studioKey": "secret",
            "status": "planned",
            "brief": {"businessName": "listing"},
            "engineConfig": {"hired": ["scout", "inka", "stella"], "price_inr": 5997},
        },
    )
    res = _client().get("/r/listing-abcd1234")
    assert res.status_code == 403


def test_run_room_with_key(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.http_api.ledger.get_campaign",
        lambda _id: {
            "id": "listing-abcd1234",
            "studioKey": "secret",
            "status": "planned",
            "brief": {"businessName": "listing", "website": "https://shop.example/"},
            "engineConfig": {"hired": ["scout", "inka", "stella"], "price_inr": 5997},
        },
    )
    res = _client().get("/r/listing-abcd1234?k=secret")
    assert res.status_code == 200
    assert "YES" in res.text
    assert "5997" in res.text
    assert "creative_gate" in res.text


def test_capture_post_redirects(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.http_api.create_campaign",
        lambda brief, raw_text="": {
            "id": "listing-aa11bb22",
            "runPath": "/r/listing-aa11bb22?k=abc",
            "studioPath": "/s/listing-aa11bb22?k=abc",
            "status": "planned",
            "brief": brief,
        },
    )
    res = _client().post(
        "/",
        data={"url": "https://shop.example/", "name": "Shop"},
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert res.headers["location"] == "/r/listing-aa11bb22?k=abc"


def test_create_campaign_classifies_listing(monkeypatch) -> None:
    monkeypatch.setattr("app.campaigns.sanitize_user_prompt", lambda _t: {"skipped": True})
    monkeypatch.setattr("app.campaigns.ledger.upsert_campaign", lambda *_a, **_k: None)
    monkeypatch.setattr("app.campaigns.ledger.write_receipt", lambda **_k: None)
    monkeypatch.setattr("app.campaigns.ledger.write_event", lambda **_k: None)
    monkeypatch.setattr("app.campaigns.channel.stamp_campaign", lambda _x: None)
    monkeypatch.setattr("app.campaigns.channel.get", lambda: None)
    out = create_campaign({"url": "https://share.google/abc"})
    assert out["status"] == "planned"
    assert out["runPath"].startswith("/r/")
    assert "k=" in out["runPath"]
    assert out["brief"]["googleListing"] == "https://share.google/abc"
    assert out["brief"]["businessName"] == "listing"


def test_infra_surfaces_home_and_run() -> None:
    res = _client().get("/v1/infra")
    assert res.status_code == 200
    surfaces = res.json()["surfaces"]
    assert surfaces["home"] == "/"
    assert surfaces["run"] == "/r/{id}?k="
    assert surfaces["seedKit"] == "/k/google-listing-eaf57cae"


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
