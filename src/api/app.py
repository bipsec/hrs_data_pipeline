"""FastAPI application for HRS data pipeline API."""

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ..database.mongodb_client import get_global_mongo, close_global_mongo

from .routes import (
    general_router,
    codebooks_router,
    variables_router,
    sections_router,
    search_router,
    utilities_router,
    categorizer_router,
    exit_router,
    post_exit_router,
)

app = FastAPI(
    title="HRS Data Pipeline API",
    description="API for querying HRS (Health and Retirement Study) codebook data",
    version="1.0.0",
)

# Mount static files for UI
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (no prefix so paths stay /codebooks, /variables, etc.)
app.include_router(general_router)
app.include_router(codebooks_router)
app.include_router(variables_router)
app.include_router(sections_router)
app.include_router(search_router)
app.include_router(utilities_router)
app.include_router(categorizer_router)
app.include_router(exit_router)
app.include_router(post_exit_router)


def main() -> None:
    """Run the API server (used by `uv run hrs-dev`)."""
    import uvicorn
    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


@app.on_event("startup")
def _startup():
    get_global_mongo()  # connect once

@app.on_event("shutdown")
def _shutdown():
    close_global_mongo()



if __name__ == "__main__":
    main()
