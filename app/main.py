from contextlib import asynccontextmanager
import asyncio
import logging
import time
import uuid

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .auth import require_api_key
from .config import get_settings
from .errors import error_response, validation_exception_handler
from .laya_adapter import to_jev_response, to_laya_questions
from .model_manager import MODEL_ALIASES, ModelManager
from .schemas import SystemOneRequest


settings = get_settings()
logger = logging.getLogger("layaservice")
manager = ModelManager(settings)
semaphore = asyncio.Semaphore(max(1, settings.max_inflight))


@asynccontextmanager
async def lifespan(_: FastAPI):
    await manager.startup()
    yield


app = FastAPI(title="Laya Service", version="0.1.0", lifespan=lifespan)
app.add_exception_handler(RequestValidationError, validation_exception_handler)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/readyz")
async def readyz():
    if not manager.ready:
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready"}


@app.get("/v1/models", dependencies=[Depends(require_api_key)])
async def models():
    return {"data": manager.models(), "object": "list"}


@app.post("/v1/systemone", dependencies=[Depends(require_api_key)])
async def systemone(payload: SystemOneRequest, request: Request):
    if len(payload.questions) > settings.max_questions:
        return error_response(422, "too many questions", "questions")
    state_size = len(str(payload.state).encode("utf-8"))
    if state_size > settings.max_state_bytes:
        return error_response(422, "state is too large", "state")
    for key, question in payload.questions.items():
        if question.type == "choice" and len(question.criteria) > settings.max_choice_options:
            return error_response(422, "too many choice options", f"questions.{key}.criteria")
        if question.type == "score" and len(question.criteria) > settings.max_score_levels:
            return error_response(422, "too many score levels", f"questions.{key}.criteria")
    request_id = uuid.uuid4().hex
    started = time.perf_counter()
    try:
        async with semaphore:
            result = await asyncio.wait_for(
                manager.predict(payload.state, to_laya_questions(payload.questions), payload.model),
                timeout=settings.request_timeout_seconds,
            )
    except asyncio.TimeoutError:
        return error_response(529, "model inference timed out")
    except ValueError as exc:
        return error_response(422, str(exc), "model")
    except Exception as exc:
        # Keep the client-facing error stable, but preserve the actionable cause in server logs.
        logger.exception("Laya inference failed: %s", exc)
        return error_response(529, "model is temporarily unavailable")
    response = JSONResponse(content=to_jev_response(result))
    response.headers["X-Request-Id"] = request_id
    response.headers["X-Laya-Latency-Ms"] = str(round((time.perf_counter() - started) * 1000, 2))
    response.headers["X-Laya-Model"] = str(result.get("routing", {}).get("model", result.get("model", "unknown")))
    return response
