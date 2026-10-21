from __future__ import annotations

import argparse
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote

import httpx


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(int(round((len(ordered) - 1) * fraction)), len(ordered) - 1)
    return ordered[index]


def validate(endpoint: str, response: httpx.Response) -> None:
    if response.status_code != 200:
        raise RuntimeError(f"HTTP {response.status_code}")
    content_type = response.headers.get("content-type", "")
    if endpoint == "pdf" and "application/pdf" not in content_type:
        raise RuntimeError(f"content-type inesperado: {content_type}")
    if endpoint == "qr" and "image/png" not in content_type:
        raise RuntimeError(f"content-type inesperado: {content_type}")
    if endpoint in ("health", "verify") and "application/json" not in content_type:
        raise RuntimeError(f"content-type inesperado: {content_type}")
    if endpoint == "pdf" and not response.content.startswith(b"%PDF-"):
        raise RuntimeError("arquivo PDF inválido")


def main() -> int:
    parser = argparse.ArgumentParser(description="Teste de carga local dos endpoints públicos.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--code", default="", help="Código de certificado para verify/pdf/qr.")
    parser.add_argument(
        "--endpoint",
        choices=["health", "verify", "pdf", "qr", "mixed"],
        default="mixed",
    )
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=20)
    args = parser.parse_args()

    if args.endpoint in {"verify", "pdf", "qr", "mixed"} and not args.code.strip():
        parser.error("--code é obrigatório para verify, pdf, qr e mixed")

    code = quote(args.code.strip().upper(), safe="")
    base = args.base_url.rstrip("/")
    paths = {
        "health": "/api/health",
        "verify": f"/api/certificates/verify/{code}",
        "pdf": f"/api/certificates/verify/{code}/pdf",
        "qr": f"/api/certificates/verify/{code}/qr.png",
    }
    sequence = (
        ["health", "verify", "qr", "pdf"] if args.endpoint == "mixed" else [args.endpoint]
    )

    latencies: list[float] = []
    failures: list[str] = []
    statuses: dict[int, int] = {}

    with httpx.Client(base_url=base, timeout=30.0, follow_redirects=True) as client:
        for index in range(min(8, args.requests)):
            endpoint = sequence[index % len(sequence)]
            response = client.get(paths[endpoint])
            validate(endpoint, response)
            response.read()

        def run(index: int) -> tuple[str, float, int]:
            endpoint = sequence[index % len(sequence)]
            started = time.perf_counter()
            response = client.get(paths[endpoint])
            elapsed = (time.perf_counter() - started) * 1000
            response.read()
            validate(endpoint, response)
            return endpoint, elapsed, response.status_code

        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            futures = [executor.submit(run, index) for index in range(args.requests)]
            for future in as_completed(futures):
                try:
                    _endpoint, elapsed, status_code = future.result()
                except Exception as exc:  # noqa: BLE001 - relatório de carga
                    failures.append(str(exc))
                    continue
                latencies.append(elapsed)
                statuses[status_code] = statuses.get(status_code, 0) + 1
        total_seconds = time.perf_counter() - started

    print(f"URL: {base}")
    print(f"Endpoint: {args.endpoint} | requisições: {args.requests} | concorrência: {args.concurrency}")
    print(f"Sucesso: {len(latencies)} | falhas: {len(failures)} | status: {statuses}")
    if latencies:
        print(f"Taxa: {len(latencies) / total_seconds:.1f} req/s | duração: {total_seconds:.2f}s")
        print(
            "Latência ms: "
            f"p50={percentile(latencies, 0.50):.1f} "
            f"p95={percentile(latencies, 0.95):.1f} "
            f"p99={percentile(latencies, 0.99):.1f} "
            f"max={max(latencies):.1f} "
            f"média={statistics.fmean(latencies):.1f}"
        )
    if failures:
        print("Falhas:")
        for failure in failures[:10]:
            print(f"- {failure}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
