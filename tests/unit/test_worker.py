# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

from unittest.mock import MagicMock, patch

from app.worker import handle_step


@patch("app.worker.publish_next")
@patch("app.worker.ledger")
def test_handle_step_writes_ok_receipt_and_publishes_next(ledger: MagicMock, publish_next: MagicMock) -> None:
    ledger.get_receipt.return_value = None
    ledger.get_campaign.return_value = {"brief": {"businessName": "Peak Gym", "geo": "Gurgaon"}}
    publish_next.return_value = "msg-2"
    out = handle_step(
        {
            "campaignId": "c1",
            "step": "scout",
            "pipeline": ["scout", "inka"],
            "attempt": 1,
            "idempotencyKey": "c1:scout:1",
        }
    )
    assert out["status"] == "ok"
    assert out["nextMessageId"] == "msg-2"
    statuses = [c.kwargs["status"] for c in ledger.write_receipt.call_args_list]
    assert "started" in statuses
    assert "ok" in statuses


@patch("app.worker.publish_next")
@patch("app.worker.ledger")
def test_handle_step_skips_when_receipt_already_ok(ledger: MagicMock, publish_next: MagicMock) -> None:
    ledger.get_receipt.return_value = {"status": "ok"}
    publish_next.return_value = "msg-next"
    out = handle_step(
        {"campaignId": "c1", "step": "scout", "pipeline": ["scout", "inka"], "attempt": 2}
    )
    assert out["status"] == "already_done"
    ledger.write_receipt.assert_not_called()
    publish_next.assert_called_once()
