import pytest

from scripts.load_test import percentile, run_load_test


def test_percentile_calculates_value() -> None:
    assert percentile([1, 2, 3, 4, 5], 0.95) == 5


@pytest.mark.asyncio
async def test_load_test_summary_with_mocked_send(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_send_one(client, base_url, text, semaphore):
        return {
            "latency_ms": 1.0,
            "routing_mode": "local_direct",
            "source": "local",
            "status": "success",
        }

    monkeypatch.setattr("scripts.load_test.send_one", fake_send_one)

    summary = await run_load_test("http://example.test", requests=3, concurrency=2)

    assert summary["requests"] == 3
    assert summary["routing_modes"] == {"local_direct": 3}
    assert summary["avg_ms"] == 1.0
