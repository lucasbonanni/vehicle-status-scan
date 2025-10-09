"""HTTP request/response logging middleware for FastAPI."""

import time
import logging
from typing import Callable, Set
from fastapi import Request, Response
from fastapi.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ....infrastructure.logging import (
    generate_correlation_id,
    set_correlation_id,
    get_correlation_id,
    clear_correlation_id,
    get_logger
)

logger = get_logger(__name__)

# Headers to exclude from logging (sensitive information)
EXCLUDED_HEADERS = {
    'authorization',
    'cookie',
    'set-cookie',
    'x-api-key',
    'x-auth-token',
    'proxy-authorization',
    'www-authenticate',
    'proxy-authenticate'
}

# Content types to exclude from body logging (large/binary content)
EXCLUDED_CONTENT_TYPES = {
    'application/octet-stream',
    'image/',
    'video/',
    'audio/',
    'application/pdf',
    'application/zip',
    'multipart/form-data'
}


class RequestResponseLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log HTTP requests and responses with correlation IDs."""

    def __init__(
        self,
        app: ASGIApp,
        log_request_body: bool = False,
        log_response_body: bool = False,
        max_body_size: int = 1024,  # Maximum body size to log (in bytes)
        exclude_paths: Set[str] = None
    ):
        """
        Initialize the logging middleware.

        Args:
            app: The ASGI application
            log_request_body: Whether to log request bodies
            log_response_body: Whether to log response bodies
            max_body_size: Maximum body size to log in bytes
            exclude_paths: Set of paths to exclude from logging
        """
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.max_body_size = max_body_size
        self.exclude_paths = exclude_paths or {
            '/health',
            '/docs',
            '/redoc',
            '/openapi.json',
            '/favicon.ico'
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and response with logging."""
        # Skip logging for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Generate and set correlation ID
        correlation_id = self._get_or_generate_correlation_id(request)
        set_correlation_id(correlation_id)

        try:
            # Log the incoming request
            await self._log_request(request, correlation_id)

            # Record start time
            start_time = time.time()

            # Process the request
            response = await call_next(request)

            # Calculate response time
            process_time = time.time() - start_time
            duration_ms = process_time * 1000

            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id

            # Log the response
            await self._log_response(request, response, duration_ms, correlation_id)

            return response

        except Exception as exc:
            # Log the exception
            process_time = time.time() - start_time
            duration_ms = process_time * 1000

            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "correlation_id": correlation_id,
                    "request_method": request.method,
                    "request_path": request.url.path,
                    "request_query": str(request.query_params),
                    "duration_ms": duration_ms,
                    "error": str(exc),
                    "error_type": type(exc).__name__
                },
                exc_info=True
            )
            raise

        finally:
            # Clear correlation ID from context
            clear_correlation_id()

    def _get_or_generate_correlation_id(self, request: Request) -> str:
        """Get correlation ID from request header or generate a new one."""
        # Check for existing correlation ID in headers
        correlation_id = request.headers.get("X-Correlation-ID")

        if not correlation_id:
            # Generate new correlation ID
            correlation_id = generate_correlation_id()

        return correlation_id

    async def _log_request(self, request: Request, correlation_id: str) -> None:
        """Log the incoming HTTP request."""
        # Sanitize headers
        sanitized_headers = self._sanitize_headers(dict(request.headers))

        # Prepare request body if enabled
        request_body = None
        if self.log_request_body:
            request_body = await self._get_request_body(request)

        # Extract client information
        client_host = getattr(request.client, 'host', 'unknown') if request.client else 'unknown'
        user_agent = request.headers.get('user-agent', 'unknown')

        # Log the request
        logger.info(
            f"HTTP Request: {request.method} {request.url.path}",
            extra={
                "correlation_id": correlation_id,
                "request_method": request.method,
                "request_path": request.url.path,
                "request_query": str(request.query_params) if request.query_params else None,
                "request_headers": sanitized_headers,
                "request_body": request_body,
                "client_host": client_host,
                "user_agent": user_agent,
                "content_type": request.headers.get('content-type'),
                "content_length": request.headers.get('content-length')
            }
        )

    async def _log_response(
        self,
        request: Request,
        response: Response,
        duration_ms: float,
        correlation_id: str
    ) -> None:
        """Log the HTTP response."""
        # Sanitize response headers
        sanitized_headers = self._sanitize_headers(dict(response.headers))

        # Prepare response body if enabled
        response_body = None
        if self.log_response_body and not isinstance(response, StreamingResponse):
            response_body = await self._get_response_body(response)

        # Determine log level based on status code
        if response.status_code >= 500:
            log_level = logging.ERROR
        elif response.status_code >= 400:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO

        # Log the response
        logger.log(
            log_level,
            f"HTTP Response: {request.method} {request.url.path} -> {response.status_code} ({duration_ms:.2f}ms)",
            extra={
                "correlation_id": correlation_id,
                "request_method": request.method,
                "request_path": request.url.path,
                "response_status": response.status_code,
                "response_headers": sanitized_headers,
                "response_body": response_body,
                "duration_ms": round(duration_ms, 2),
                "content_type": response.headers.get('content-type'),
                "content_length": response.headers.get('content-length')
            }
        )

    def _sanitize_headers(self, headers: dict) -> dict:
        """Remove sensitive headers from logging."""
        sanitized = {}
        for key, value in headers.items():
            key_lower = key.lower()
            if key_lower in EXCLUDED_HEADERS:
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        return sanitized

    async def _get_request_body(self, request: Request) -> str:
        """Get request body for logging if appropriate."""
        try:
            # Check content type
            content_type = request.headers.get('content-type', '').lower()

            # Skip binary/large content types
            for excluded_type in EXCLUDED_CONTENT_TYPES:
                if excluded_type in content_type:
                    return "[BINARY_CONTENT]"

            # Get body
            body = await request.body()

            # Check size
            if len(body) > self.max_body_size:
                return f"[BODY_TOO_LARGE:{len(body)}_bytes]"

            # Try to decode as text
            try:
                return body.decode('utf-8')[:self.max_body_size]
            except UnicodeDecodeError:
                return "[BINARY_CONTENT]"

        except Exception as e:
            logger.debug(f"Failed to read request body: {e}")
            return "[BODY_READ_ERROR]"

    async def _get_response_body(self, response: Response) -> str:
        """Get response body for logging if appropriate."""
        try:
            # Check content type
            content_type = response.headers.get('content-type', '').lower()

            # Skip binary/large content types
            for excluded_type in EXCLUDED_CONTENT_TYPES:
                if excluded_type in content_type:
                    return "[BINARY_CONTENT]"

            # Get body if it's a simple response
            if hasattr(response, 'body') and response.body:
                body = response.body

                # Check size
                if len(body) > self.max_body_size:
                    return f"[BODY_TOO_LARGE:{len(body)}_bytes]"

                # Try to decode as text
                try:
                    if isinstance(body, bytes):
                        return body.decode('utf-8')[:self.max_body_size]
                    else:
                        return str(body)[:self.max_body_size]
                except UnicodeDecodeError:
                    return "[BINARY_CONTENT]"

            return None

        except Exception as e:
            logger.debug(f"Failed to read response body: {e}")
            return "[BODY_READ_ERROR]"


def create_logging_middleware(
    log_request_body: bool = False,
    log_response_body: bool = False,
    max_body_size: int = 1024,
    exclude_paths: Set[str] = None
) -> Callable[[ASGIApp], RequestResponseLoggingMiddleware]:
    """
    Factory function to create logging middleware with configuration.

    Args:
        log_request_body: Whether to log request bodies
        log_response_body: Whether to log response bodies
        max_body_size: Maximum body size to log in bytes
        exclude_paths: Set of paths to exclude from logging

    Returns:
        Middleware factory function
    """
    def middleware_factory(app: ASGIApp) -> RequestResponseLoggingMiddleware:
        return RequestResponseLoggingMiddleware(
            app=app,
            log_request_body=log_request_body,
            log_response_body=log_response_body,
            max_body_size=max_body_size,
            exclude_paths=exclude_paths
        )

    return middleware_factory
