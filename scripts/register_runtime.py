#!/usr/bin/env python3
"""Create (or reuse) Vertex Agent Engine Memory Bank + Agent Registry entries.

Honest about failures: asia-south1 may not host Agent Engine; Gemini Enterprise
registry may require an org app. Writes infra/runtime-extras.json either way.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT = os.environ.get("GCP_PROJECT_ID", "leadsy-flock")
REGION = os.environ.get("GCP_REGION", "asia-south1")
RUNTIME = os.environ.get("VERTEX_RUNTIME_REGION", "us-central1")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "infra" / "runtime-extras.json"


def _gcloud(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    path = env.get("PATH", "")
    extra = os.path.expanduser("~/.local/bin") + ":/tmp/google-cloud-sdk/bin:"
    env["PATH"] = extra + path
    return subprocess.run(
        ["gcloud", *args],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def create_memory_bank() -> dict:
    """Try Vertex Agent Engine in us-central1, then asia-south1."""
    try:
        import vertexai
        from vertexai import agent_engines
    except ImportError as exc:
        return {"ok": False, "error": f"import: {exc}"}

    last_error = None
    for loc in (RUNTIME, REGION):
        try:
            vertexai.init(project=PROJECT, location=loc)
            existing = []
            try:
                for engine in agent_engines.list():
                    name = getattr(engine, "display_name", "") or ""
                    if name == "leadsy-flock-memory":
                        resource = getattr(engine, "resource_name", None) or getattr(
                            engine, "name", None
                        )
                        return {
                            "ok": True,
                            "reused": True,
                            "location": loc,
                            "resourceName": resource,
                            "id": str(resource).rsplit("/", 1)[-1] if resource else None,
                        }
                    existing.append(name)
            except Exception as exc:  # noqa: BLE001
                last_error = f"list@{loc}: {exc}"

            engine = agent_engines.create(display_name="leadsy-flock-memory")
            resource = getattr(engine, "resource_name", None) or getattr(engine, "name", None)
            return {
                "ok": True,
                "reused": False,
                "location": loc,
                "resourceName": resource,
                "id": str(resource).rsplit("/", 1)[-1] if resource else None,
                "listed": existing,
            }
        except Exception as exc:  # noqa: BLE001
            last_error = f"create@{loc}: {exc}"
    return {"ok": False, "error": last_error}


def register_agent(api_url: str) -> dict:
    """Register Flo in Agent Registry. Try asia-south1 then us-central1."""
    card = f"{api_url.rstrip('/')}/a2a/app/.well-known/agent-card.json"
    attempts = []
    for loc in (REGION, RUNTIME):
        listed = _gcloud(
            "agent-registry",
            "services",
            "list",
            f"--location={loc}",
            f"--project={PROJECT}",
            "--format=json",
        )
        attempts.append(
            {"op": "list", "location": loc, "code": listed.returncode, "err": (listed.stderr or "")[-400]}
        )
        if listed.returncode == 0:
            try:
                rows = json.loads(listed.stdout or "[]")
            except json.JSONDecodeError:
                rows = []
            for row in rows:
                name = (row.get("displayName") or row.get("name") or "")
                if "flock" in str(name).lower() or "flo" in str(name).lower():
                    return {"ok": True, "reused": True, "location": loc, "service": row}

        created = _gcloud(
            "agent-registry",
            "services",
            "create",
            "leadsy-flock",
            f"--location={loc}",
            f"--project={PROJECT}",
            "--display-name=Leadsy Flock (Flo)",
            "--description=Director of the Leadsy Flock — ADK agent on Cloud Run for All Things Agentic.",
            "--agent-spec-type=no-spec",
            f"--interfaces=protocolBinding=http-json,url={card}",
        )
        attempts.append(
            {
                "op": "create",
                "location": loc,
                "code": created.returncode,
                "out": (created.stdout or "")[-400],
                "err": (created.stderr or "")[-800],
            }
        )
        if created.returncode == 0:
            return {"ok": True, "reused": False, "location": loc, "stdout": created.stdout, "card": card}
    return {"ok": False, "attempts": attempts, "card": card}


def main() -> int:
    api_url = os.environ.get("FLOCK_API_URL", "").strip()
    if not api_url:
        described = _gcloud(
            "run",
            "services",
            "describe",
            "flock-api",
            f"--project={PROJECT}",
            f"--region={REGION}",
            "--format=value(status.url)",
        )
        api_url = (described.stdout or "").strip()

    doc = {
        "project": PROJECT,
        "apiUrl": api_url,
        "memoryBank": create_memory_bank(),
        "agentRegistry": register_agent(api_url) if api_url else {"ok": False, "error": "no api url"},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2) + "\n")
    print(json.dumps(doc, indent=2))
    # Non-zero only if both failed; infra can still ship without registry.
    if not doc["memoryBank"].get("ok") and not doc["agentRegistry"].get("ok"):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
