from __future__ import annotations

import time
from collections import Counter
from threading import Lock

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class MetricsStore:
    def __init__(self) -> None:
        self.started_at = time.time()
        self.http_requests: Counter[tuple[str, str, int]] = Counter()
        self.http_request_seconds: Counter[tuple[str, str]] = Counter()
        self.events: Counter[str] = Counter()
        self.lock = Lock()

    def record_http(self, method: str, path: str, status_code: int, duration_seconds: float) -> None:
        route = normalize_path(path)
        with self.lock:
            self.http_requests[(method, route, status_code)] += 1
            self.http_request_seconds[(method, route)] += duration_seconds

    def record_event(self, event: str) -> None:
        with self.lock:
            self.events[event] += 1

    def prometheus(self) -> str:
        lines = [
            "# HELP admanager_uptime_seconds Process uptime in seconds.",
            "# TYPE admanager_uptime_seconds gauge",
            f"admanager_uptime_seconds {time.time() - self.started_at:.3f}",
            "# HELP admanager_http_requests_total HTTP requests by method, route and status.",
            "# TYPE admanager_http_requests_total counter",
        ]
        with self.lock:
            for (method, route, status_code), count in sorted(self.http_requests.items()):
                lines.append(
                    'admanager_http_requests_total'
                    f'{{method="{method}",route="{route}",status="{status_code}"}} {count}'
                )
            lines.extend(
                [
                    "# HELP admanager_http_request_seconds_total HTTP request duration total.",
                    "# TYPE admanager_http_request_seconds_total counter",
                ]
            )
            for (method, route), seconds in sorted(self.http_request_seconds.items()):
                lines.append(
                    'admanager_http_request_seconds_total'
                    f'{{method="{method}",route="{route}"}} {seconds:.6f}'
                )
            lines.extend(
                [
                    "# HELP admanager_events_total Application events.",
                    "# TYPE admanager_events_total counter",
                ]
            )
            for event, count in sorted(self.events.items()):
                lines.append(f'admanager_events_total{{event="{event}"}} {count}')
        return "\n".join(lines) + "\n"


def normalize_path(path: str) -> str:
    parts = [part for part in path.split("/") if part]
    normalized: list[str] = []
    for part in parts:
        if len(part) > 24 or "." in part or "," in part:
            normalized.append("{id}")
        else:
            normalized.append(part)
    return "/" + "/".join(normalized) if normalized else "/"


metrics_store = MetricsStore()


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        started_at = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - started_at
        metrics_store.record_http(request.method, request.url.path, response.status_code, duration)
        return response
