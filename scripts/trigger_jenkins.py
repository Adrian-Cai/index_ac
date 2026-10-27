#!/usr/bin/env python3
"""Trigger the Jenkins SCM job for an image and wait for its deployment result."""

import base64
import json
import os
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

WAIT_TIMEOUT_SECONDS = 1800
POLL_INTERVAL_SECONDS = 5
REQUEST_TIMEOUT_SECONDS = 15


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, file, code, message, headers, new_url):
        return None


OPENER = build_opener(NoRedirect)


def required_env(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"Required environment variable is missing: {name}")
    return value


def validate_job_url(value):
    parts = urlsplit(value)
    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username
        or parts.password
        or parts.query
        or parts.fragment
    ):
        raise ValueError("JENKINS_JOB_URL must be an HTTPS job URL without credentials or query")
    return value.rstrip("/")


def ensure_same_origin(url, base_url):
    target = urlsplit(url)
    base = urlsplit(base_url)
    if (target.scheme, target.netloc) != (base.scheme, base.netloc):
        raise RuntimeError("Jenkins returned a URL on a different origin")
    return url


def request(url, username, token, method="GET", data=None):
    encoded_auth = base64.b64encode(f"{username}:{token}".encode()).decode()
    req = Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Basic {encoded_auth}",
            "Accept": "application/json",
        },
    )
    try:
        with OPENER.open(req, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return response.status, response.headers, response.read()
    except HTTPError as error:
        return error.code, error.headers, error.read()
    except (URLError, TimeoutError, OSError) as error:
        raise RuntimeError(f"Jenkins request failed: {error}") from error


def get_json(url, username, token, base_url):
    ensure_same_origin(url, base_url)
    status, _, body = request(url, username, token)
    if status != 200:
        raise RuntimeError(f"Jenkins API returned HTTP {status}")
    try:
        return json.loads(body)
    except json.JSONDecodeError as error:
        raise RuntimeError("Jenkins returned invalid JSON") from error


def wait_for_deployment(queue_url, username, token, base_url, deadline):
    poll_count = 0
    while time.monotonic() < deadline:
        queue = get_json(
            urljoin(queue_url.rstrip("/") + "/", "api/json"),
            username,
            token,
            base_url,
        )
        if queue.get("cancelled"):
            raise RuntimeError("Jenkins canceled the deployment before it started")
        executable = queue.get("executable")
        if executable and executable.get("url"):
            build_url = ensure_same_origin(executable["url"], base_url)
            break
        poll_count += 1
        if poll_count % 12 == 0:
            print("Jenkins deployment is still running.", flush=True)
        time.sleep(min(POLL_INTERVAL_SECONDS, max(0, deadline - time.monotonic())))
    else:
        raise TimeoutError("Timed out waiting for Jenkins to start the deployment")

    while time.monotonic() < deadline:
        build = get_json(
            urljoin(build_url.rstrip("/") + "/", "api/json"),
            username,
            token,
            base_url,
        )
        result = build.get("result")
        if result:
            if result != "SUCCESS":
                raise RuntimeError(f"Jenkins deployment finished with result: {result}")
            return build_url
        if not build.get("building", True):
            raise RuntimeError("Jenkins deployment stopped without a result")
        poll_count += 1
        if poll_count % 12 == 0:
            print("Jenkins deployment is still running.", flush=True)
        time.sleep(min(POLL_INTERVAL_SECONDS, max(0, deadline - time.monotonic())))
    raise TimeoutError("Timed out waiting for Jenkins deployment to finish")


def main():
    try:
        job_url = validate_job_url(required_env("JENKINS_JOB_URL"))
        username = required_env("JENKINS_USER")
        token = required_env("JENKINS_API_TOKEN")
        image_tag = required_env("CNB_COMMIT_SHORT")
        if not re.fullmatch(r"[0-9a-f]{8}", image_tag):
            raise ValueError("CNB_COMMIT_SHORT must be an 8-character lowercase SHA")

        status, headers, _ = request(
            f"{job_url}/buildWithParameters",
            username,
            token,
            method="POST",
            data=urlencode({"IMAGE_TAG": image_tag}).encode(),
        )
        if status not in (200, 201, 202, 302, 303):
            raise RuntimeError(f"Jenkins rejected the deployment request (HTTP {status})")
        location = headers.get("Location")
        if not location:
            raise RuntimeError("Jenkins accepted no queue URL for the deployment")
        queue_url = ensure_same_origin(urljoin(f"{job_url}/", location), job_url)
        print("Jenkins deployment queued.")

        # shortcut: 30-minute cap, raise if deployments routinely exceed it.
        deadline = time.monotonic() + WAIT_TIMEOUT_SECONDS
        build_url = wait_for_deployment(queue_url, username, token, job_url, deadline)
        print(f"Jenkins deployment succeeded: {build_url}")
        return 0
    except (ValueError, RuntimeError, TimeoutError) as error:
        print(f"Jenkins deployment failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
