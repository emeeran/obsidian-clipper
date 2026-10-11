"""Tests for the retry utility (covers H7 — previously 0% coverage)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from obsidian_clipper.utils.retry import retry_with_backoff


@pytest.fixture(autouse=True)
def _no_sleep():
    """Keep tests fast — retry_with_backoff sleeps between attempts."""
    with patch("obsidian_clipper.utils.retry.time.sleep"):
        yield


class TestRetryWithBackoff:
    def test_returns_result_on_first_success(self):
        calls = []

        def func():
            calls.append(1)
            return "ok"

        assert retry_with_backoff(func, max_attempts=3) == "ok"
        assert len(calls) == 1

    def test_retries_on_falsy_then_succeeds(self):
        results = iter(["", "", "found"])

        def func():
            return next(results)

        assert retry_with_backoff(func, max_attempts=3, delay=0) == "found"

    def test_returns_last_falsy_result_when_all_attempts_fail(self):
        def func():
            return ""

        # No exception — falsy result returned after exhausting attempts.
        assert retry_with_backoff(func, max_attempts=3, delay=0) == ""

    def test_max_attempts_one_does_not_retry(self):
        calls = []

        def func():
            calls.append(1)
            return ""

        assert retry_with_backoff(func, max_attempts=1, delay=0) == ""
        assert len(calls) == 1

    def test_should_retry_callback_drives_retries(self):
        results = iter(["retry", "retry", "done"])

        def func():
            return next(results)

        # Retry only while the callback says so; "done" is kept.
        assert retry_with_backoff(func, max_attempts=5, should_retry=lambda r: r == "retry") == "done"

    def test_should_retry_false_keeps_result_immediately(self):
        def func():
            return "weird"  # truthy, but callback says don't retry

        assert retry_with_backoff(func, max_attempts=5, should_retry=lambda r: False) == "weird"

    def test_reraises_after_all_attempts_on_exception(self):
        def func():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            retry_with_backoff(func, max_attempts=2, delay=0)

    def test_succeeds_after_intermediate_exception(self):
        results = iter([ValueError("first"), "ok"])

        def func():
            item = next(results)
            if isinstance(item, Exception):
                raise item
            return item

        assert retry_with_backoff(func, max_attempts=3, delay=0) == "ok"
