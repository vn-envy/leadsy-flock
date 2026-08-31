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
    assert "Hire is closed" in res.text
    assert 'data-locked="1"' in res.text
    assert 'id="hire"' in res.text
    assert 'id="hire" hidden' not in res.text
    assert 'id="cue"' in res.text
    assert "Paste the Google listing" in res.text
    js = _client().get("/assets/flock/theater.js").text
    assert "function playAudition" in js
    assert "function typeUrl" in js
    assert "await beat(1500)" in js
    assert "await beat(3200)" in js
    assert "playSeed(false).then" not in js
    assert "observatory" in res.text
    assert "backend path" in res.text
    assert 'href="/trace"' in res.text
    assert "architecture" in res.text
    assert "blog" in res.text
    assert "neighbourhood shops" in res.text
    assert 'class="story"' in res.text
    assert "Unlock" in res.text
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
    assert "t.me" not in res.text.lower()
    assert 'href="/demo"' in res.text


def test_home_redirects_to_seeded_demo() -> None:
    res = _client().get("/", follow_redirects=False)
    assert res.status_code == 303
    assert res.headers["location"] == "/demo"
    query = _client().get("/?name=Glen&goal=cupcakes&geo=Indiranagar", follow_redirects=False)
    assert query.status_code == 303
    assert query.headers["location"] == "/demo"
    landed = _client().get("/", follow_redirects=True)
    assert landed.status_code == 200
    assert "Glen" in landed.text
    assert "Hire is closed" in landed.text


def test_flock_hero_asset() -> None:
    res = _client().get("/assets/flock/hero.webp")
    assert res.status_code == 200
    assert "image/webp" in res.headers["content-type"]
    assert _client().get("/assets/flock/theater.css").status_code == 200
    assert _client().get("/assets/flock/kit.css").status_code == 200
    assert _client().get("/assets/flock/dash.css").status_code == 200
    assert _client().get("/assets/flock/dash.js").status_code == 200
    assert _client().get("/assets/flock/architecture.png").status_code == 200
    assert _client().get("/assets/flock/../http_api.py").status_code == 404


def test_run_room_is_not_published() -> None:
    res = _client().get("/r/bad")
    assert res.status_code == 404
    assert res.json()["error"] == "not published"


def test_run_room_with_key_is_not_published(monkeypatch) -> None:
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
    assert res.status_code == 404
    assert res.json()["error"] == "not published"


def test_capture_post_is_not_published(monkeypatch) -> None:
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
    assert res.status_code == 404
    assert res.json()["error"] == "not published"


def test_campaign_api_is_not_published() -> None:
    client = _client()
    assert client.post("/v1/campaigns", json={"url": "https://shop.example/"}).status_code == 404
    assert client.get("/v1/campaigns").status_code == 404
    assert client.get("/v1/campaigns/google-listing-eaf57cae").status_code == 404
    assert client.post("/v1/campaigns/google-listing-eaf57cae/approve").status_code == 404
    assert client.post("/v1/screen", json={"text": "hi"}).status_code == 404
    assert client.post(
        "/v1/consents",
        json={
            "campaignId": "google-listing-eaf57cae",
            "name": "Ada",
            "contact": "ada@example.com",
            "consent": True,
        },
    ).status_code == 404
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
    assert client.post("/run_sse", json={}).status_code == 404
    assert client.get("/s/google-listing-eaf57cae?k=secret").status_code == 404
    evil = client.get("/k/google-listing-eaf57cae-evil")
    assert evil.status_code == 404


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


def test_infra_is_not_published() -> None:
    res = _client().get("/v1/infra")
    assert res.status_code == 404
    assert res.json()["error"] == "not published"


def test_worker_pubsub_still_reaches_handler() -> None:
    res = _client().post("/internal/pubsub/campaign-steps", json={})
    assert res.status_code in {400, 404}
    assert res.json().get("error") != "not published"


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
        lambda _id: [
            {
                "step": "scout",
                "status": "ok",
                "payload": {
                    "groundingUris": ["https://maps.google.com/?q=glens"],
                    "usage": [
                        {
                            "model": "gemini-3.5-flash",
                            "kind": "text",
                            "inputTokens": 1800,
                            "outputTokens": 420,
                            "usd": 0.0065,
                        }
                    ],
                },
            },
            {
                "step": "inka_harvest",
                "status": "ok",
                "payload": {
                    "clip": {
                        "gcs": "gs://bucket/clip.mp4",
                        "voices": {"en": {"ok": True}, "indic": {"ok": True}},
                    },
                    "clipProof": {
                        "gcs": "gs://bucket/proof.mp4",
                        "voices": {"en": {"ok": True}, "indic": {"ok": True}},
                    },
                },
            },
            {"step": "stella", "status": "ok"},
            {"step": "ad_kit", "status": "ok"},
        ],
    )
    monkeypatch.setattr(
        "app.observe.ledger.get_campaign",
        lambda _id: {
            "id": "google-listing-eaf57cae",
            "brief": {"businessName": "Glen's Bakehouse"},
            "kitPath": "/k/google-listing-eaf57cae",
        },
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
    assert "5997" not in res.text
    assert "seed" in res.text.lower()
    assert "Vertex list-price" in res.text or "list price" in res.text.lower()
    assert _client().get("/console", follow_redirects=False).status_code == 303
    js = _client().get("/v1/dash")
    assert js.status_code == 200
    body = js.json()
    assert "quotedInr" not in body
    assert "quotedInr" not in (body.get("seed") or {})
    assert body["run"]["revision"] == "flock-api-00028-test"
    assert body["totals"]["campaigns"] == 1
    assert body["hits"][0]["kitPath"] == "/k/google-listing-eaf57cae"
    assert "quotedInr" not in body["totals"]
    seed = body["seed"]
    assert seed["campaignId"] == "google-listing-eaf57cae"
    assert seed["tokens"]["total"] >= 1800
    assert seed["calls"] >= 3
    assert seed["estimatedUsd"] >= 6.4
    assert any(t["id"] == "google_search" for t in seed["tools"])
    assert any(t["id"] == "veo" for t in seed["tools"])
    assert any(t["id"] == "ffmpeg" for t in seed["tools"])
    path = body["path"]
    assert path["campaignId"] == "google-listing-eaf57cae"
    assert "quotedInr" not in path
    hops = {h["step"]: h for h in path["hops"]}
    assert hops["scout"]["span"] == "engine.scout"
    assert hops["scout"]["service"] == "flock-worker"
    assert hops["plan"]["span"] == "campaign.plan"
    assert hops["inka_harvest"]["span"] == "engine.inka_harvest"
    assert "/trace" in res.text
    assert "backend path" in res.text.lower()


def test_trace_page_is_the_backend_path(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.observe.ledger.list_receipts",
        lambda _id: [
            {
                "step": "plan",
                "status": "ok",
                "engine": "bri",
                "service": "flock-api",
                "payload": {"model": "gemini-3.5-flash"},
            },
            {
                "step": "approve",
                "status": "ok",
                "engine": "flo",
                "service": "flock-api",
            },
            {
                "step": "scout",
                "status": "ok",
                "engine": "scout",
                "service": "flock-worker",
                "attempt": 3,
                "payload": {"traceId": "abc123", "model": "gemini-3.5-flash"},
            },
            {"step": "inka", "status": "ok", "service": "flock-worker"},
            {"step": "inka_harvest", "status": "ok", "service": "flock-worker"},
            {"step": "creative_gate", "status": "ok", "service": "flock-worker"},
            {"step": "stella", "status": "ok", "service": "flock-worker"},
            {"step": "ad_kit", "status": "ok", "service": "flock-worker"},
        ],
    )
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "leadsy-flock")
    monkeypatch.setenv("GCP_REGION", "asia-south1")
    monkeypatch.setattr("app.observe._gcp_get", lambda *_a, **_k: None)
    res = _client().get("/trace")
    assert res.status_code == 200
    assert "Glen" in res.text
    assert "engine.scout" in res.text
    assert "flock-worker" in res.text
    assert "campaign.plan" in res.text
    assert "campaign.approve" in res.text
    assert "engine.inka_harvest" in res.text
    assert "engine.creative_gate" in res.text
    assert "google-listing-eaf57cae" in res.text
    assert "console.cloud.google.com/run/detail/asia-south1/flock-worker" in res.text
    assert "console.cloud.google.com/traces/explorer" in res.text
    assert "<table" not in res.text.lower()
    assert "5997" not in res.text
    js = _client().get("/v1/trace")
    assert js.status_code == 200
    body = js.json()
    hops = body["path"]["hops"]
    assert [h["step"] for h in hops] == [
        "plan",
        "approve",
        "scout",
        "inka",
        "inka_harvest",
        "creative_gate",
        "stella",
        "ad_kit",
    ]
    assert hops[2]["span"] == "engine.scout"
    assert hops[2]["service"] == "flock-worker"
    assert hops[2]["traceId"] == "abc123"
    assert "quotedInr" not in body["path"]
    assert body["path"]["console"]["workerTraces"].endswith("project=leadsy-flock")
    assert "5997" not in str(body)


def test_architecture_page_is_the_judge_diagram() -> None:
    html = _client().get("/architecture")
    assert html.status_code == 200
    assert "architecture.png" in html.text
    assert "never autopost" in html.text.lower()
    assert "Gemini 3.5" in html.text
    assert "Google ADK" in html.text
    assert "Model Armor" in html.text
    assert "Memory Bank" in html.text
    assert "Veo 3.1" in html.text
    assert "<table" not in html.text.lower()
    assert "5997" not in html.text
    asset = _client().get("/assets/flock/architecture.png")
    assert asset.status_code == 200
    assert "image/png" in asset.headers["content-type"]
    png = _client().get("/architecture.png")
    assert png.status_code == 200
    assert "image/png" in png.headers["content-type"]
    assert png.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert b"quotedInr" not in png.content


def test_blog_is_hackathon_essay() -> None:
    res = _client().get("/blog")
    assert res.status_code == 200
    text = res.text
    assert "purposes of entering" in text
    assert "All Things Agentic" in text
    assert "neighbourhood" in text.lower() or "grass roots" in text.lower() or "grass-roots" in text.lower()
    assert "Google pointed the models" in text or "courtyard" in text.lower()
    assert "Gemini 3.5" in text
    assert "Google ADK" in text
    assert "Veo 3.1" in text
    assert "Cloud Run" in text
    assert "Pub/Sub" in text
    assert "Model Armor" in text
    assert "never autopost" in text.lower() or "do not autopost" in text.lower()
    assert "5997" not in text
    assert "<table" not in text.lower()
    md = _client().get("/blog.md")
    assert md.status_code == 200
    assert b"purposes of entering" in md.content


def test_video_bible_is_readable() -> None:
    res = _client().get("/video")
    assert res.status_code == 200
    text = res.text
    assert "You already live on Google" in text
    assert "engine.scout" in text
    assert "/trace" in text
    assert "5997" not in text
    assert "<table" in text.lower()
    assert "<blockquote" in text.lower()
    md = _client().get("/video.md")
    assert md.status_code == 200
    assert b"You already live on Google" in md.content


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
    css = _client().get("/assets/flock/kit.css").text
    assert "object-fit: cover" in css
    assert ".still .thumb" in css
    assert "position: absolute" in css


def test_ops_requires_token(monkeypatch) -> None:
    monkeypatch.delenv("OPS_TOKEN", raising=False)
    res = _client().get("/ops")
    assert res.status_code == 501


def test_telegram_webhook_is_not_published(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "shh")
    res = _client().post("/v1/telegram/webhook", json={"update_id": 1})
    assert res.status_code == 404
    assert res.json()["error"] == "not published"


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
