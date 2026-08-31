# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the governing permissions and limitations under the License.

import logging
import os
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from typing import Any

import pytest
import requests
from requests.exceptions import RequestException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://127.0.0.1:8000"
HEALTH_URL = BASE_URL + "/healthz"


def log_output(pipe: Any, log_func: Any) -> None:
    for line in iter(pipe.readline, ""):
        log_func(line.strip())


def start_server() -> subprocess.Popen[str]:
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.fast_api_app:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
    ]
    env = os.environ.copy()
    env["INTEGRATION_TEST"] = "TRUE"
    env["APP_URL"] = BASE_URL
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=env,
    )
    threading.Thread(
        target=log_output, args=(process.stdout, logger.info), daemon=True
    ).start()
    threading.Thread(
        target=log_output, args=(process.stderr, logger.error), daemon=True
    ).start()
    return process


def wait_for_server(timeout: int = 90, interval: int = 1) -> bool:
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(HEALTH_URL, timeout=10)
            if response.status_code == 200:
                logger.info("Server is ready")
                return True
        except RequestException:
            pass
        time.sleep(interval)
    logger.error(f"Server did not become ready within {timeout} seconds")
    return False


@pytest.fixture(scope="session")
def server_fixture(request: Any) -> Iterator[subprocess.Popen[str]]:
    logger.info("Starting server process")
    server_process = start_server()
    if not wait_for_server():
        pytest.fail("Server failed to start")
    logger.info("Server process started")

    def stop_server() -> None:
        logger.info("Stopping server process")
        server_process.terminate()
        server_process.wait()
        logger.info("Server process stopped")

    request.addfinalizer(stop_server)
    yield server_process


def test_public_lock_keeps_seeded_demo(server_fixture: subprocess.Popen[str]) -> None:
    home = requests.get(BASE_URL + "/", allow_redirects=False, timeout=10)
    assert home.status_code == 303
    assert home.headers.get("location") == "/demo"
    demo = requests.get(BASE_URL + "/demo", timeout=10)
    assert demo.status_code == 200
    assert "Glen" in demo.text
    assert "Hire is closed" in demo.text


def test_adk_and_hire_are_not_published(server_fixture: subprocess.Popen[str]) -> None:
    assert requests.post(BASE_URL + "/run_sse", json={}, timeout=10).status_code == 404
    assert requests.post(
        BASE_URL + "/apps/app/users/lock-test/sessions",
        json={"state": {}},
        timeout=10,
    ).status_code == 404
    assert requests.get(
        BASE_URL + "/a2a/app/.well-known/agent-card.json",
        timeout=10,
    ).status_code == 404
    assert requests.get(BASE_URL + "/docs", timeout=10).status_code == 404
    assert requests.post(
        BASE_URL + "/v1/campaigns",
        json={"url": "https://shop.example/"},
        timeout=10,
    ).status_code == 404
