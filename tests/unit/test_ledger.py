from app.ledger import merge_receipt


def test_merge_receipt_does_not_regress_ok_to_started() -> None:
    prev = {
        "status": "ok",
        "payload": {"resolvedName": "Glen's Bakehouse", "vertical": "food"},
    }
    body = {
        "status": "started",
        "attempt": 5,
        "payload": {"idempotencyKey": "c:scout:5"},
        "updatedAt": "now",
    }
    out = merge_receipt(prev, body)
    assert out["status"] == "ok"
    assert out["payload"]["resolvedName"] == "Glen's Bakehouse"
    assert "idempotencyKey" not in out["payload"]


def test_merge_receipt_started_keeps_in_progress_payload() -> None:
    prev = {"status": "started", "payload": {"resolvedName": "Glen's Bakehouse"}}
    body = {"status": "started", "payload": {"idempotencyKey": "k"}, "updatedAt": "now"}
    out = merge_receipt(prev, body)
    assert out["status"] == "started"
    assert out["payload"]["resolvedName"] == "Glen's Bakehouse"
    assert out["payload"]["idempotencyKey"] == "k"


def test_merge_receipt_ok_replaces_payload() -> None:
    prev = {"status": "started", "payload": {"idempotencyKey": "k"}}
    body = {"status": "ok", "payload": {"resolvedName": "Glen's Bakehouse"}}
    out = merge_receipt(prev, body)
    assert out["status"] == "ok"
    assert out["payload"] == {"resolvedName": "Glen's Bakehouse"}
