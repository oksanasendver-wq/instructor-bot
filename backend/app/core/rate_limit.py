"""Bounded per-worker throttling. Configure a shared edge limit when scaling workers."""

from collections import OrderedDict, deque
from time import monotonic
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.buckets = OrderedDict()

    async def dispatch(self, request, call_next):
        path = request.url.path
        limit = 12 if path.endswith("/ai-draft") else 60 if "/auth/" in path else 0
        if limit and request.method == "POST":
            now = monotonic()
            key = (
                request.client.host if request.client else "unknown",
                "ai" if path.endswith("/ai-draft") else "auth",
            )
            queue = self.buckets.setdefault(key, deque())
            self.buckets.move_to_end(key)
            while queue and queue[0] < now - 60:
                queue.popleft()
            if len(queue) >= limit:
                return JSONResponse(
                    {"detail": "Слишком много попыток. Повторите через минуту."},
                    status_code=429,
                    headers={"Retry-After": "60"},
                )
            queue.append(now)
            while len(self.buckets) > 10000:
                self.buckets.popitem(last=False)
        return await call_next(request)
