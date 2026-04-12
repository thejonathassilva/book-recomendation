from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.handlers import register_exception_handlers
from src.api.routes import admin_console, auth, catalog, purchases, recommendations, users
from src.monitoring.metrics import API_ERROR_COUNT, metrics_response

app = FastAPI(title="Bookstore ML API", version="1.0.0")
register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(catalog.router, prefix="/api/v1")
app.include_router(recommendations.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(purchases.router, prefix="/api/v1")
app.include_router(admin_console.router, prefix="/api/v1")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    data, ctype = metrics_response()
    from fastapi.responses import Response

    return Response(content=data, media_type=ctype)


@app.middleware("http")
async def count_errors(request, call_next):
    try:
        response = await call_next(request)
        if response.status_code >= 400:
            API_ERROR_COUNT.labels(endpoint=request.url.path, code=str(response.status_code)).inc()
        return response
    except Exception:
        API_ERROR_COUNT.labels(endpoint=request.url.path, code="500").inc()
        raise
