# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

from app.agent import MODEL, root_agent


def test_root_agent_is_flo() -> None:
    assert root_agent.name == "flo"
    assert MODEL == "gemini-3.5-flash"
    tool_names = {getattr(t, "name", None) or getattr(t, "__name__", None) for t in root_agent.tools}
    # ADK wraps functions; accept either the raw name or the FunctionTool name.
    joined = " ".join(str(x) for x in tool_names if x)
    assert "list_flock" in joined or any("flock" in str(t).lower() for t in root_agent.tools)
