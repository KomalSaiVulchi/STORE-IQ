"""Logging and tracing middleware."""

from __future__ import annotations

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from prometheus_client import Counter, Histogram
from pythonjsonlogger import jsonlogger
import logging


# Prometheus metrics (used by the middleware)
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)
REQUEST_LATENCY = Histogram(
    "http_request_latency_ms",
    "HTTP request latency in milliseconds",
    ["method", "endpoint"],
    buckets=[5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000],
)


def configure_logger(service_name: str) -> logging.Logger:
    """Configure structured JSON logging."""
    logger = logging.getLogger(service_name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


async def logging_middleware(request: Request, call_next: Callable[[Request], Response]) -> Response:
    """Attach trace id, emit structured logs, and record Prometheus metrics for each request."""
    trace_id = str(uuid.uuid4())
    request.state.trace_id = trace_id
    start = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception as exc:
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger: logging.Logger = request.app.state.logger
        logger.error(
            {
                "trace_id": trace_id,
                "method": request.method,
                "endpoint": request.url.path,
                "status_code": 500,
                "latency_ms": latency_ms,
                "error": str(exc),
                "service": "storeiq-api",
            }
        )
        REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path, status_code="500").inc()
        REQUEST_LATENCY.labels(method=request.method, endpoint=request.url.path).observe(latency_ms)
        raise

    latency_ms = int((time.perf_counter() - start) * 1000)
    logger: logging.Logger = request.app.state.logger

    # Extract store_id from the path if present
    store_id = None
    if "/stores/" in request.url.path:
        parts = request.url.path.split("/")
        try:
            store_idx = parts.index("stores")
            if store_idx + 1 < len(parts):
                store_id = parts[store_idx + 1]
        except ValueError:
            pass

    # Skip logging for health checks and prometheus scrapes to reduce noise
    if request.url.path not in {"/health", "/metrics/prometheus"}:
        log_payload = {
            "trace_id": trace_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "method": request.method,
            "endpoint": request.url.path,
            "status_code": response.status_code,
            "latency_ms": latency_ms,
            "service": "storeiq-api",
        }
        if store_id:
            log_payload["store_id"] = store_id
        logger.info(log_payload)

    # Prometheus metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status_code=str(response.status_code),
    ).inc()
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path,
    ).observe(latency_ms)

    response.headers["x-trace-id"] = trace_id
    return response
