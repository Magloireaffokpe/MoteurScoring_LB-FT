from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Gère les erreurs de validation Pydantic (422).
    Retourne un message clair plutôt que le format verbose FastAPI par défaut.
    """
    errors = []
    for error in exc.errors():
        field = " → ".join(str(e) for e in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"],
        })

    logger.warning("Validation error on %s %s: %s", request.method, request.url, errors)

    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation failed",
            "detail": errors,
        }
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """
    Gère les erreurs base de données (500).
    Ne renvoie jamais les détails internes en réponse.
    """
    logger.error(
        "Database error on %s %s: %s",
        request.method, request.url, str(exc),
        exc_info=True
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Database error",
            "detail": "An internal database error occurred. Please try again later.",
        }
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """
    Gère toutes les exceptions non catchées (500).
    """
    logger.error(
        "Unhandled exception on %s %s: %s",
        request.method, request.url, str(exc),
        exc_info=True
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred. Please try again later.",
        }
    )