from app.campaigns import decode_pubsub_push
from app.http_api import _safe_campaign_id


def test_safe_campaign_id() -> None:
    assert _safe_campaign_id("peak-gym-71d02b5c")
    assert _safe_campaign_id("noya-salon-a1b2c3d4")
    assert not _safe_campaign_id("../etc/passwd")
    assert not _safe_campaign_id("still.png")


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
