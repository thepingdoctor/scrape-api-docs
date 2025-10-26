"""
Custom Middleware for FastAPI Application
=========================================

Includes logging, rate limiting, and request tracking middleware.
"""

import time
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Tuple
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Request/Response logging middleware.

    Logs all HTTP requests with timing information.
    """

    async def dispatch(self, request: Request, call_next):
        """Process request and log details."""
        request_id = f"{int(time.time() * 1000)}-{id(request)}"
        start_time = time.time()

        # Log request
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"from {request.client.host}"
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log response
            logger.info(
                f"[{request_id}] {response.status_code} "
                f"completed in {duration:.3f}s"
            )

            # Add custom headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{duration:.3f}"

            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"[{request_id}] Error after {duration:.3f}s: {e}",
                exc_info=True
            )
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.

    Implements token bucket algorithm per client IP.
    For production, use Redis-based rate limiting.
    """

    def __init__(self, app, requests_per_minute: int = 60):
        """
        Initialize rate limiter.

        Args:
            app: FastAPI application
            requests_per_minute: Max requests per minute per IP
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_size = 60  # seconds

        # Store: {ip: [(timestamp, count)]}
        self.request_history: Dict[str, list] = defaultdict(list)

    def _clean_old_requests(self, ip: str, current_time: float):
        """Remove requests outside the time window."""
        cutoff_time = current_time - self.window_size
        self.request_history[ip] = [
            (timestamp, count)
            for timestamp, count in self.request_history[ip]
            if timestamp > cutoff_time
        ]

    def _get_request_count(self, ip: str, current_time: float) -> int:
        """Get total requests in current window."""
        self._clean_old_requests(ip, current_time)
        return sum(count for _, count in self.request_history[ip])

    async def dispatch(self, request: Request, call_next):
        """Check rate limit and process request."""
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/api/v1/system/health"]:
            return await call_next(request)

        client_ip = request.client.host
        current_time = time.time()

        # Get current request count
        request_count = self._get_request_count(client_ip, current_time)

        # Check limit
        if request_count >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for {client_ip}")

            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": (
                            f"Rate limit exceeded. Maximum {self.requests_per_minute} "
                            f"requests per minute allowed."
                        ),
                        "retry_after": self.window_size
                    }
                },
                headers={
                    "Retry-After": str(self.window_size),
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(current_time + self.window_size))
                }
            )

        # Record request
        self.request_history[client_ip].append((current_time, 1))

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        remaining = self.requests_per_minute - request_count - 1
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(
            int(current_time + self.window_size)
        )

        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Add unique request ID to each request.

    Useful for tracing requests across logs.
    """

    async def dispatch(self, request: Request, call_next):
        """Add request ID header."""
        request_id = request.headers.get(
            "X-Request-ID",
            f"req_{int(time.time() * 1000)}_{id(request)}"
        )

        # Store in request state
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add to response
        response.headers["X-Request-ID"] = request_id

        return response
