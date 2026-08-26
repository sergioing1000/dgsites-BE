"""Post-deploy smoke check for Render services.

Waits for a Render deploy to reach the ``live`` state (when a deploy id is
provided) and then verifies the service ``/health`` endpoint returns a healthy
payload. Designed to run in GitHub Actions deploy jobs for both staging and
production.

Configuration is supplied via environment variables (no secrets are
hardcoded):

    RENDER_API_KEY      Render API key (secret) — only needed when a deploy id
                        is supplied to poll deploy status.
    RENDER_SERVICE_ID   Render service id (secret) — only needed with a deploy id.
    RENDER_SERVICE_URL  Public base URL of the service (environment variable,
                        NOT a secret), e.g. https://wind-data-api.onrender.com.
    DEPLOY_ID           Render deploy id returned by the trigger step. Optional;
                        when empty, only the /health probe runs.
    ENV_NAME            GitHub environment name, used only for error messages.
    MAX_WAIT_SECONDS    Total budget for the Render status poll (default 600).
    POLL_INTERVAL       Seconds between Render status polls (default 15).
    HEALTH_TIMEOUT      Seconds budget for the /health probe (default 120).

Exit code 0 on success, 1 on failure. Failures emit ``::error::`` annotations
so they surface clearly in the GitHub Actions run summary.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

RENDER_API = "https://api.render.com/v1"

# Render deploy statuses considered terminal failures.
FAILURE_STATUSES = {
    "build_failed",
    "deploy_failed",
    "failed",
    "canceled",
    "cancelled",
    "deactivated",
    "error",
}


def _get_json(url: str, headers: dict[str, str], timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def wait_for_render_live(deploy_id: str, api_key: str, service_id: str,
                         max_wait: int, interval: int) -> None:
    """Poll Render API until the deploy reaches ``live`` or fails/times out."""
    url = f"{RENDER_API}/services/{service_id}/deploys/{deploy_id}"
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    deadline = time.time() + max_wait
    status = "unknown"
    while time.time() < deadline:
        try:
            data = _get_json(url, headers)
            status = data.get("status", "unknown")
            print(f"Render deploy {deploy_id} status: {status}")
            if status == "live":
                return
            if status in FAILURE_STATUSES:
                print(f"::error::Render deploy {deploy_id} ended in status '{status}'.")
                sys.exit(1)
        except Exception as exc:  # noqa: BLE001 — transient network errors are retried
            print(f"Warning: Render status poll failed ({exc}); retrying in {interval}s.")
        time.sleep(interval)
    print(
        f"::error::Render deploy {deploy_id} did not reach 'live' within "
        f"{max_wait}s (last status: {status})."
    )
    sys.exit(1)


def smoke_health(service_url: str, timeout: int) -> None:
    """Probe ``{service_url}/health`` until it reports healthy or times out."""
    health_url = f"{service_url.rstrip('/')}/health"
    deadline = time.time() + timeout
    last_error = ""
    while time.time() < deadline:
        try:
            req = urllib.request.Request(health_url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            if resp.status == 200 and body.get("status") == "healthy":
                print(f"Smoke check PASSED: {health_url} -> {body}")
                return
            print(f"Health endpoint returned status={resp.status} body={body}")
        except Exception as exc:  # noqa: BLE001 — retried until deadline
            last_error = str(exc)
            print(f"Waiting for {health_url}: {exc}")
        time.sleep(5)
    print(
        f"::error::Smoke check FAILED: {health_url} did not report healthy "
        f"within {timeout}s. Last error: {last_error}"
    )
    sys.exit(1)


def main() -> None:
    service_url = os.environ.get("RENDER_SERVICE_URL", "").strip()
    env_name = os.environ.get("ENV_NAME", "<unset>")
    if not service_url:
        print(
            "::error::RENDER_SERVICE_URL is not set. Add it as an environment "
            "variable (NOT a secret) in the '" + env_name + "' GitHub environment: "
            "Settings -> Environments -> " + env_name + " -> Environment variables -> "
            "RENDER_SERVICE_URL (e.g. https://wind-data-api.onrender.com)."
        )
        sys.exit(1)

    deploy_id = os.environ.get("DEPLOY_ID", "").strip()
    api_key = os.environ.get("RENDER_API_KEY", "").strip()
    service_id = os.environ.get("RENDER_SERVICE_ID", "").strip()
    max_wait = int(os.environ.get("MAX_WAIT_SECONDS", "600"))
    interval = int(os.environ.get("POLL_INTERVAL", "15"))
    health_timeout = int(os.environ.get("HEALTH_TIMEOUT", "120"))

    if deploy_id:
        if not api_key or not service_id:
            print(
                "::error::DEPLOY_ID was provided but RENDER_API_KEY or "
                "RENDER_SERVICE_ID is missing; cannot poll Render deploy status."
            )
            sys.exit(1)
        wait_for_render_live(deploy_id, api_key, service_id, max_wait, interval)
    else:
        print("No DEPLOY_ID provided; skipping Render status poll and probing /health directly.")

    smoke_health(service_url, health_timeout)


if __name__ == "__main__":
    main()
