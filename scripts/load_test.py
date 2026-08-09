"""Simple concurrent load test for the intent classifier API.

Run while the backend is active:

    python3 scripts/load_test.py --requests 200 --concurrency 50
"""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from statistics import mean
from time import perf_counter
from typing import Any

import httpx


MESSAGES = [
    "ML course er price koto?",
    "course fee koto?",
    "class kobe start hobe?",
    "recording pabo?",
    "ami confused, kon course nibo?",
    "ki ki course available?",
    "thanks",
    "ajke weather kemon?",
]


def percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(round((len(ordered) - 1) * percent), len(ordered) - 1)
    return round(ordered[index], 2)


async def send_one(
    client: httpx.AsyncClient,
    base_url: str,
    text: str,
    semaphore: asyncio.Semaphore,
) -> dict[str, Any]:
    async with semaphore:
        start = perf_counter()
        response = await client.post(
            f"{base_url}/classify",
            json={"text": text, "business_type": "edtech"},
        )
        latency_ms = round((perf_counter() - start) * 1000, 2)
        response.raise_for_status()
        body = response.json()
        return {
            "latency_ms": latency_ms,
            "routing_mode": body.get("routing_mode", "unknown"),
            "status": body.get("status", "unknown"),
            "source": body.get("source", "unknown"),
        }


async def run_load_test(base_url: str, requests: int, concurrency: int) -> dict[str, Any]:
    semaphore = asyncio.Semaphore(concurrency)
    timeout = httpx.Timeout(30.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        tasks = [
            send_one(client, base_url, MESSAGES[index % len(MESSAGES)], semaphore)
            for index in range(requests)
        ]
        results = await asyncio.gather(*tasks)

    latencies = [item["latency_ms"] for item in results]
    return {
        "requests": requests,
        "concurrency": concurrency,
        "avg_ms": round(mean(latencies), 2) if latencies else 0.0,
        "p95_ms": percentile(latencies, 0.95),
        "p99_ms": percentile(latencies, 0.99),
        "routing_modes": dict(Counter(item["routing_mode"] for item in results)),
        "sources": dict(Counter(item["source"] for item in results)),
        "statuses": dict(Counter(item["status"] for item in results)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=20)
    args = parser.parse_args()

    result = asyncio.run(run_load_test(args.base_url, args.requests, args.concurrency))
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
