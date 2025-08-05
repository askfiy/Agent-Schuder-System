import time
import json
import logging
import typing
from typing import override

from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
    _StreamingResponse,  # pyright: ignore[reportPrivateUsage]
)
from starlette.types import Message


logger = logging.getLogger("middleware-monitor")


class GlobalMonitorMiddleware(BaseHTTPMiddleware):
    FILTER_API_PATH = ["/", "/docs", "/openapi.json", "/heart"]
    CONTENT_TYPE_PREFIXES = ["application/json", "text/"]
    MAX_BODY_LOG_LENGTH = 500

    def get_request_info(self, request: Request) -> str:
        method = request.method
        path = request.url.path
        query = request.url.query
        http_version = request.scope.get("http_version", "unknown")
        full_path = f"{path}?{query}" if query else path
        return f"{method} {full_path} HTTP/{http_version}"

    def get_body_log(self, body: bytes) -> str:
        if not body:
            return ""

        try:
            parsed = json.loads(body)
            return f", JSON: {json.dumps(parsed, ensure_ascii=False)}"
        except json.JSONDecodeError:
            decoded = body.decode(errors="ignore")
            return f", (Non-JSON): {decoded[: self.MAX_BODY_LOG_LENGTH]}{'...' if len(decoded) > self.MAX_BODY_LOG_LENGTH else ''}"

    async def get_response_body(self, response: _StreamingResponse) -> bytes:
        response_body_chunks: list[bytes] = []
        async for chunk in response.body_iterator:
            response_body_chunks.append(typing.cast("bytes", chunk))
        return b"".join(response_body_chunks)

    @override
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.url.path in self.FILTER_API_PATH:
            return await call_next(request)

        request_info = self.get_request_info(request)

        request_body = await request.body()

        async def receive() -> Message:
            return {"type": "http.request", "body": request_body, "more_body": False}

        request_log = self.get_body_log(request_body)
        logger.info(f"Request: '{request_info}'{request_log}")

        # Create a safe-to-read request
        new_request = Request(request.scope, receive)

        start_time = time.perf_counter()
        response: _StreamingResponse = await call_next(new_request)
        duration = (time.perf_counter() - start_time) * 1000
        status_code = response.status_code

        content_type = response.headers.get("content-type", "")

        if any(content_type.startswith(t) for t in self.CONTENT_TYPE_PREFIXES):
            response_body = await self.get_response_body(response)
            response_log = self.get_body_log(response_body)

            logger.info(
                f"Response: '{request_info} {status_code}' ({duration:.2f}ms){response_log}"
            )

            return Response(
                content=response_body,
                status_code=status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        logger.info(f"Response: '{request_info} {status_code}' ({duration:.2f}ms)")
        return response
