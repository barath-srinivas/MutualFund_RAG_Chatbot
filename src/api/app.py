import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src import __version__
from src.config.settings import get_settings
from src.logging_config import configure_logging
from src.observability.metrics import get_chat_metrics
from src.schemes.registry import get_scheme_registry
from src.api.chat import ChatService
from src.api.corpus_status import router as corpus_status_router
from src.api.internal_ingest import router as internal_ingest_router
from src.api.models import ChatRequest, ChatResponse
from src.api.rate_limit import SlidingWindowRateLimiter, client_key_from_request

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    registry = get_scheme_registry()
    _app.state.scheme_registry = registry
    _app.state.chat_service = ChatService(registry=registry)
    logger.info(
        "Loaded scheme registry: amc=%s schemes=%d",
        registry.amc,
        len(registry.list_schemes()),
    )
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="MF RAG ChatBot",
        description="Facts-only FAQ assistant for ICICI Prudential mutual fund schemes.",
        version=__version__,
        lifespan=lifespan,
    )

    rate_limiter = SlidingWindowRateLimiter(requests_per_minute=settings.chat_rate_limit_per_minute)
    app.state.rate_limiter = rate_limiter

    cors_origins = settings.cors_origin_list()
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        )
        logger.info("CORS enabled for origins: %s", ", ".join(cors_origins))

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled API error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error. Check API logs; ensure Phase 1 dependencies and corpus index are set up.",
            },
        )

    app.include_router(internal_ingest_router)
    app.include_router(corpus_status_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/metrics")
    def metrics() -> dict:
        """In-process chat metrics snapshot (Phase 5.2). Resets only on process restart."""
        return get_chat_metrics().snapshot()

    @app.post("/chat", response_model=ChatResponse)
    def chat(http_request: Request, request: ChatRequest) -> ChatResponse:
        limiter: SlidingWindowRateLimiter = app.state.rate_limiter
        client_key = client_key_from_request(http_request)
        if not limiter.allow(client_key):
            retry_after = limiter.retry_after_seconds(client_key)
            raise HTTPException(
                status_code=429,
                detail="Too many chat requests. Please wait and try again.",
                headers={"Retry-After": str(retry_after)},
            )
        service: ChatService = app.state.chat_service
        result = service.chat(message=request.message, explicit_scheme_id=request.scheme_id)
        return ChatResponse.model_validate(result)

    return app


app = create_app()
