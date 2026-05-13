import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware de logging des requêtes HTTP.
    Log : méthode, URL, status code, durée d'exécution.
    Exclut les routes de health check pour ne pas polluer les logs.
    """

    EXCLUDED_PATHS = {"/", "/docs", "/redoc", "/openapi.json"}

    async def dispatch(self, request: Request, call_next):
        # Ignore les routes de santé et docs
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"

        try:
            response = await call_next(request)
            duration = (time.time() - start_time) * 1000  # ms

            logger.info(
                "%s %s — %d — %.1fms — %s",
                request.method,
                request.url.path,
                response.status_code,
                duration,
                client_ip,
            )

            # Ajoute le temps de réponse dans les headers
            response.headers["X-Process-Time"] = f"{duration:.1f}ms"
            response.headers["X-RiskGuard-Version"] = "1.0.0"

            return response

        except Exception as exc:
            duration = (time.time() - start_time) * 1000
            logger.error(
                "%s %s — ERROR — %.1fms — %s — %s",
                request.method,
                request.url.path,
                duration,
                client_ip,
                str(exc),
            )
            raise