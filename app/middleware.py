"""Request correlation-ID middleware.

Inspects the incoming ``X-Request-ID`` header: if present, it is
propagated; otherwise a new UUID4 is generated.  The resolved ID is:

* Bound to ``structlog``'s contextvars so every ``logger.info(...)`` etc.
  automatically includes ``request_id``.
* Returned in the ``X-Request-ID`` response header for traceability.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_REQUEST_ID_VAR = "request_id"


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that manages a per-request correlation ID.

    The middleware runs on **every** request, including ``/health``.
    It reads / generates the ID *before* the route handler executes so
    that ``structlog`` contextvars are already populated when the
    handler logs.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process a single request lifecycle.

        Args:
            request: Incoming ASGI request.
            call_next: Callable that invokes the next middleware / route.

        Returns:
            The downstream response with ``X-Request-ID`` header set.
        """
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Bind to structlog context so all loggers in this request emit it.
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(**{_REQUEST_ID_VAR: request_id})

        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
