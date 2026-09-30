from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from app.core.config import get_settings
from app.core.logging import setup_logging, logger
from app.core.exceptions import (
    AppError,
    AddressNotFoundError,
    AddressDeactivatedError,
    AddressPrivateError,
    RateLimitExceededError
)
from app.database.session import init_db
from app.api.v1 import api_v1_router
from app.web.home import router as web_home_router
from app.web.auth import router as web_auth_router
from app.web.dashboard import router as web_dashboard_router
from app.web.addresses import router as web_address_router
from app.web.resolver import router as web_resolver_router
from app.web.admin import router as web_admin_router

settings = get_settings()
templates = Jinja2Templates(directory="app/templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME}...")
    init_db()
    logger.info("Database initialized successfully.")
    yield
    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}...")


app = FastAPI(
    title=settings.APP_NAME,
    description="Universal Address Resolution Platform - Smart Physical Address Management & Short Unique Public IDs",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Favicon handler to prevent wildcard resolver collision
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


# Static Files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include API v1 Router
app.include_router(api_v1_router)

# Include Web Frontend Routers
app.include_router(web_home_router)
app.include_router(web_auth_router)
app.include_router(web_dashboard_router)
app.include_router(web_address_router)
app.include_router(web_admin_router)
app.include_router(web_resolver_router)


# Global Exception Handlers
@app.exception_handler(AddressNotFoundError)
async def address_not_found_handler(request: Request, exc: AddressNotFoundError):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"detail": exc.message})
    return templates.TemplateResponse(
        request=request,
        name="resolver/error.html",
        context={
            "request": request,
            "status_code": 404,
            "error_title": "Address Not Found",
            "error_message": exc.message,
            "public_id": request.path_params.get("public_id", "")
        },
        status_code=404
    )


@app.exception_handler(AddressDeactivatedError)
async def address_deactivated_handler(request: Request, exc: AddressDeactivatedError):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=410, content={"detail": exc.message})
    return templates.TemplateResponse(
        request=request,
        name="resolver/error.html",
        context={
            "request": request,
            "status_code": 410,
            "error_title": "Address Currently Unavailable",
            "error_message": exc.message,
            "public_id": request.path_params.get("public_id", "")
        },
        status_code=410
    )


@app.exception_handler(AddressPrivateError)
async def address_private_handler(request: Request, exc: AddressPrivateError):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=403, content={"detail": exc.message})
    return templates.TemplateResponse(
        request=request,
        name="resolver/error.html",
        context={
            "request": request,
            "status_code": 403,
            "error_title": "Address Is Private",
            "error_message": exc.message,
            "public_id": request.path_params.get("public_id", "")
        },
        status_code=403
    )


@app.exception_handler(RateLimitExceededError)
async def rate_limit_handler(request: Request, exc: RateLimitExceededError):
    return JSONResponse(status_code=429, content={"detail": exc.message})


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
    return templates.TemplateResponse(
        request=request,
        name="resolver/error.html",
        context={
            "request": request,
            "status_code": exc.status_code,
            "error_title": "Request Error",
            "error_message": exc.message
        },
        status_code=exc.status_code
    )


# WSGI application callable for WSGI web servers (e.g. PythonAnywhere)
try:
    from a2wsgi import ASGIMiddleware
    application = ASGIMiddleware(app)
except ImportError:
    application = app

