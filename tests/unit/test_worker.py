# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

from unittest.mock import MagicMock, patch

from app.worker import handle_step


@patch("app.worker.run_engine")
@patch("app.worker.publish_next")
@patch("app.worker.ledger")
def test_handle_step_writes_ok_receipt_and_publishes_next(
    ledger: MagicMock, publish_next: MagicMock, run_engine: MagicMock
) -> None:
    ledger.get_receipt.return_value = None
    ledger.get_campaign.return_value = {"brief": {"businessName": "Peak Gym", "geo": "Gurgaon"}}
    publish_next.return_value = "msg-2"
    run_engine.return_value = {"evidence": []}
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


@patch("app.worker.publish_step")
@patch("app.worker.run_engine")
@patch("app.worker.ledger")
def test_creative_gate_reject_republishes_inka(
    ledger: MagicMock, run_engine: MagicMock, publish_step: MagicMock
) -> None:
    ledger.get_receipt.return_value = None
    ledger.get_campaign.return_value = {"inkaRevisions": 1}
    run_engine.return_value = {"verdict": "reject"}
    publish_step.return_value = "retry"
    out = handle_step(
        {
            "campaignId": "c1",
            "step": "creative_gate",
            "pipeline": ["scout", "inka", "creative_gate", "stella"],
            "attempt": 1,
        }
    )
    assert out["status"] == "revise"
    publish_step.assert_called_once()
    assert publish_step.call_args.kwargs["step"] == "inka"
    assert publish_step.call_args.kwargs["force_retry"] is True


@patch("app.worker.publish_next")
@patch("app.worker.run_engine")
@patch("app.worker.ledger")
def test_handle_step_engine_exception_still_acks(
    ledger: MagicMock, run_engine: MagicMock, publish_next: MagicMock
) -> None:
    ledger.get_receipt.return_value = None
    ledger.get_campaign.return_value = {}
    publish_next.return_value = "msg-2"
    run_engine.side_effect = RuntimeError("vertex down")
    out = handle_step(
        {
            "campaignId": "c1",
            "step": "inka",
            "pipeline": ["inka", "creative_gate"],
            "attempt": 1,
        }
    )
    assert out["status"] == "ok"
    assert out["result"]["ok"] is False
    statuses = [c.kwargs["status"] for c in ledger.write_receipt.call_args_list]
    assert "ok" in statuses


@patch("app.worker.time.sleep")
@patch("app.worker.publish_step")
@patch("app.worker.run_engine")
@patch("app.worker.ledger")
def test_harvest_sidecar_polls_without_completing_campaign(
    ledger: MagicMock, run_engine: MagicMock, publish_step: MagicMock, sleep: MagicMock
) -> None:
    ledger.get_receipt.return_value = None
    ledger.get_campaign.return_value = {}
    run_engine.return_value = {"retry": True, "clip": {"status": "polling"}}
    publish_step.return_value = "msg-h"
    out = handle_step(
        {
            "campaignId": "c1",
            "step": "inka_harvest",
            "pipeline": ["scout", "inka", "creative_gate", "stella"],
            "attempt": 2,
        }
    )
    assert out["status"] == "polling"
    sleep.assert_called_once()
    publish_step.assert_called_once()
    assert publish_step.call_args.kwargs["step"] == "inka_harvest"
    assert publish_step.call_args.kwargs["attempt"] == 3
    assert publish_step.call_args.kwargs["force_retry"] is True
    completed = [
        c
        for c in ledger.upsert_campaign.call_args_list
        if len(c.args) > 1 and isinstance(c.args[1], dict) and c.args[1].get("status") == "completed"
    ]
    assert completed == []
    statuses = [c.kwargs["status"] for c in ledger.write_receipt.call_args_list]
    assert "polling" in statuses


@patch("app.worker.publish_next")
@patch("app.worker.publish_step")
@patch("app.worker.run_engine")
@patch("app.worker.ledger")
def test_inka_kicks_off_harvest_sidecar(
    ledger: MagicMock, run_engine: MagicMock, publish_step: MagicMock, publish_next: MagicMock
) -> None:
    ledger.get_receipt.return_value = None
    ledger.get_campaign.return_value = {}
    publish_next.return_value = "msg-2"
    publish_step.return_value = "msg-h"
    run_engine.return_value = {
        "ok": True,
        "assets": {"clip": {"operation": "ops/abc"}, "jingle": {"pending": True}},
    }
    out = handle_step(
        {
            "campaignId": "c1",
            "step": "inka",
            "pipeline": ["inka", "creative_gate"],
            "attempt": 1,
        }
    )
    assert out["status"] == "ok"
    publish_step.assert_called_once()
    assert publish_step.call_args.kwargs["step"] == "inka_harvest"
    publish_next.assert_called_once()


@patch("app.worker.publish_next")
@patch("app.worker.publish_step")
@patch("app.worker.run_engine")
@patch("app.worker.ledger")
def test_inka_starts_harvest_when_only_proof_clip_is_pending(
    ledger: MagicMock, run_engine: MagicMock, publish_step: MagicMock, publish_next: MagicMock
) -> None:
    ledger.get_receipt.return_value = None
    ledger.get_campaign.return_value = {}
    publish_next.return_value = "msg-2"
    publish_step.return_value = "msg-h"
    run_engine.return_value = {
        "ok": True,
        "assets": {
            "clip": {"ok": False},
            "clipProof": {"operation": "ops/proof"},
            "jingle": {"pending": False},
        },
    }
    out = handle_step(
        {
            "campaignId": "c1",
            "step": "inka",
            "pipeline": ["inka", "creative_gate"],
            "attempt": 1,
        }
    )
    assert out["status"] == "ok"
    publish_step.assert_called_once()
    assert publish_step.call_args.kwargs["step"] == "inka_harvest"


@patch("app.worker.publish_next")
@patch("app.worker.ledger")
def test_harvest_already_ok_does_not_advance_pipeline(
    ledger: MagicMock, publish_next: MagicMock
) -> None:
    ledger.get_receipt.return_value = {"status": "ok"}
    out = handle_step(
        {
            "campaignId": "c1",
            "step": "inka_harvest",
            "pipeline": ["inka", "creative_gate"],
            "attempt": 4,
        }
    )
    assert out["status"] == "already_done"
    publish_next.assert_not_called()
