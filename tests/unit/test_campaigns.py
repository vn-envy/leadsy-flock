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
    assert "Hire the flock" in res.text
    assert "observatory" in res.text
    assert "allow-top-navigation-by-user-activation" in res.text
    assert 'class="grain"' in res.text
    roost = res.text.find('id="roost"')
    grain = res.text.find('class="grain"')
    plate = res.text.find('class="plate"')
    assert 0 <= roost < grain < plate
    assert "theater.css" in res.text
    assert "<form" not in res.text.lower()
    assert "<label" not in res.text.lower()
    assert "Get a quote" not in res.text
    assert "Open Telegram" not in res.text
    assert "t.me" not in res.text.lower()


def test_flock_hero_asset() -> None:
    res = _client().get("/assets/flock/hero.webp")
    assert res.status_code == 200
    assert "image/webp" in res.headers["content-type"]
    assert _client().get("/assets/flock/theater.css").status_code == 200
    assert _client().get("/assets/flock/kit.css").status_code == 200
    assert _client().get("/assets/flock/dash.css").status_code == 200
    assert _client().get("/assets/flock/dash.js").status_code == 200
    assert _client().get("/assets/flock/../http_api.py").status_code == 404


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
    assert "5997" not in res.text
    assert "₹" not in res.text
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
    assert surfaces["dash"] == "/dash"


def test_dash_is_observatory_not_a_table(monkeypatch) -> None:
    monkeypatch.setattr("app.observe.ledger.list_campaigns", lambda limit=40: [
        {
            "id": "google-listing-eaf57cae",
            "status": "completed",
            "brief": {"businessName": "Glen's Bakehouse"},
            "kitPath": "/k/google-listing-eaf57cae",
        }
    ])
    monkeypatch.setattr(
        "app.observe.ledger.list_receipts",
        lambda _id: [{"step": "scout", "status": "ok"}, {"step": "ad_kit", "status": "ok"}],
    )
    monkeypatch.setattr("app.observe.ledger.list_events", lambda *_a, **_k: [{"kind": "landing_hit"}])
    monkeypatch.setenv("K_SERVICE", "flock-api")
    monkeypatch.setenv("K_REVISION", "flock-api-00028-test")
    monkeypatch.setenv("GCP_REGION", "asia-south1")
    monkeypatch.setattr("app.observe._gcp_get", lambda *_a, **_k: None)
    res = _client().get("/dash")
    assert res.status_code == 200
    assert "observatory" in res.text.lower()
    assert "Cloud Run" in res.text
    assert "flock-api-00028-test" in res.text
    assert "<table" not in res.text.lower()
    assert "₹" not in res.text
    assert "5997" not in res.text
    assert _client().get("/console", follow_redirects=False).status_code == 303
    js = _client().get("/v1/dash")
    assert js.status_code == 200
    body = js.json()
    assert "quotedInr" not in body
    assert body["run"]["revision"] == "flock-api-00028-test"
    assert body["totals"]["campaigns"] == 1
    assert body["hits"][0]["kitPath"] == "/k/google-listing-eaf57cae"
    assert "quotedInr" not in body["totals"]


def test_kit_rebuilds_flock_bento(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.http_api.ledger.get_campaign",
        lambda _id: {
            "id": "google-listing-eaf57cae",
            "brief": {"businessName": "Glen's Bakehouse", "geo": "Indiranagar"},
            "landingPath": "/l/google-listing-eaf57cae",
            "kitHtml": "<html>old paper kit</html>",
        },
    )
    monkeypatch.setattr(
        "app.kit_ui.ledger.list_receipts",
        lambda _id: [
            {
                "step": "inka",
                "payload": {
                    "copy": {
                        "headline": "Courtyard red velvet",
                        "subhead": "Walk in.",
                        "cta": "See the tray",
                        "storyHook": "anti-influencer courtyard",
                        "voEn": "Come in.",
                        "voIndic": "आओ।",
                    },
                    "locale": {"bcp47": "hi-IN", "nativeName": "हिन्दी"},
                    "shelf": [],
                },
            },
            {
                "step": "ad_kit",
                "payload": {
                    "variants": [
                        {
                            "id": "meta_feed",
                            "platform": "meta",
                            "aspect": "4:5",
                            "headline": "H",
                            "primaryText": "P",
                            "utmUrl": "/l/x?utm_content=meta_feed",
                            "still": "/media/x/still-feed",
                            "width": 1080,
                            "height": 1350,
                        }
                    ]
                },
            },
            {"step": "stella", "payload": {"url": "/l/google-listing-eaf57cae"}},
        ],
    )
    res = _client().get("/k/google-listing-eaf57cae")
    assert res.status_code == 200
    assert 'data-theme="flock"' in res.text
    assert "kit.css" in res.text
    assert "bento" in res.text
    assert "old paper kit" not in res.text
    assert "<table" not in res.text.lower()
    assert "₹" not in res.text
    assert "Glen" in res.text
    assert 'target="_top"' in res.text
    assert "copyblock" in res.text
    assert 'class="head"' in res.text


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
