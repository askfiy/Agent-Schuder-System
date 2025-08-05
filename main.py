import uuid
import logging
from contextlib import asynccontextmanager
from collections.abc import Awaitable, Callable

import uvicorn
import fastapi
from fastapi import Request, Response, Depends

from core.router import api_router
from core.logger import setup_logging
from core.handle import exception_handler, service_exception_handler
from core.shared.globals import g
from core.shared.exceptions import ServiceException
from core.shared.dependencies import global_headers
from core.shared.middleware import GlobalContextMiddleware, GlobalMonitorMiddleware

name = "Agent-Scheduler-System"

logger = logging.getLogger(name)


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    setup_logging()
    yield


app = fastapi.FastAPI(
    title=name,
    lifespan=lifespan,
    dependencies=[Depends(global_headers)],
)

app.add_middleware(GlobalContextMiddleware)
app.add_middleware(GlobalMonitorMiddleware)
app.add_exception_handler(Exception, exception_handler)
app.add_exception_handler(ServiceException, service_exception_handler)


@app.middleware("http")
async def g_trace(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    g.trace_id = request.headers.get("X-Trace-Id") or str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Trace-Id"] = g.trace_id
    return response


@app.get(
    path="/heart",
    name="心跳检测",
    status_code=fastapi.status.HTTP_200_OK,
)
async def heart():
    return {"success": True}


app.include_router(api_router, prefix="/api/v1")


def main():
    uvicorn.run(app="main:app", host="0.0.0.0", port=9091)


if __name__ == "__main__":
    main()
