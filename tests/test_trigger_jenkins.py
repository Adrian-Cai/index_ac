import time
import unittest
from unittest.mock import patch

from scripts.trigger_jenkins import (
    ensure_same_origin,
    validate_job_url,
    wait_for_deployment,
)


class JenkinsTriggerTests(unittest.TestCase):
    def test_job_url_requires_https_without_embedded_credentials(self):
        self.assertEqual(
            validate_job_url("https://jenkins.example.com/job/portfolio/"),
            "https://jenkins.example.com/job/portfolio",
        )
        with self.assertRaises(ValueError):
            validate_job_url("http://jenkins.example.com/job/portfolio")
        with self.assertRaises(ValueError):
            validate_job_url("https://user:token@jenkins.example.com/job/portfolio")

    def test_rejects_cross_origin_queue_urls(self):
        with self.assertRaises(RuntimeError):
            ensure_same_origin(
                "https://other.example.com/queue/item/1/",
                "https://jenkins.example.com/job/portfolio",
            )

    @patch("scripts.trigger_jenkins.get_json")
    @patch("scripts.trigger_jenkins.time.sleep")
    def test_waits_for_successful_deployment(self, sleep, get_json):
        build_url = "https://jenkins.example.com/job/portfolio/42/"
        get_json.side_effect = [
            {"executable": {"url": build_url}},
            {"building": False, "result": "SUCCESS"},
        ]
        result = wait_for_deployment(
            "https://jenkins.example.com/queue/item/1/",
            "deploy-bot",
            "token",
            "https://jenkins.example.com/job/portfolio",
            time.monotonic() + 30,
        )
        self.assertEqual(result, build_url)
        sleep.assert_not_called()

    @patch("scripts.trigger_jenkins.get_json")
    @patch("scripts.trigger_jenkins.time.sleep")
    def test_fails_when_jenkins_deployment_fails(self, sleep, get_json):
        get_json.side_effect = [
            {"executable": {"url": "https://jenkins.example.com/job/portfolio/42/"}},
            {"building": False, "result": "FAILURE"},
        ]
        with self.assertRaisesRegex(RuntimeError, "FAILURE"):
            wait_for_deployment(
                "https://jenkins.example.com/queue/item/1/",
                "deploy-bot",
                "token",
                "https://jenkins.example.com/job/portfolio",
                time.monotonic() + 30,
            )
        sleep.assert_not_called()

    @patch("scripts.trigger_jenkins.get_json")
    @patch("scripts.trigger_jenkins.time.sleep")
    @patch("builtins.print")
    def test_reports_progress_during_long_wait(self, print_output, sleep, get_json):
        build_url = "https://jenkins.example.com/job/portfolio/42/"
        get_json.side_effect = [{} for _ in range(12)] + [
            {"executable": {"url": build_url}},
            {"building": False, "result": "SUCCESS"},
        ]
        wait_for_deployment(
            "https://jenkins.example.com/queue/item/1/",
            "deploy-bot",
            "token",
            "https://jenkins.example.com/job/portfolio",
            time.monotonic() + 30,
        )
        print_output.assert_any_call("Jenkins deployment is still running.", flush=True)


if __name__ == "__main__":
    unittest.main()
