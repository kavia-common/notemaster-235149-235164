from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.notes import router as notes_router
from src.api.routes.tags import router as tags_router

openapi_tags = [
    {"name": "system", "description": "Health and system endpoints."},
    {"name": "notes", "description": "CRUD, search, pin/favorite and tag assignment for notes."},
    {"name": "tags", "description": "CRUD and listing for tags."},
]

app = FastAPI(
    title="NoteMaster API",
    description=(
        "Backend API for the NoteMaster notes application.\n\n"
        "Database: PostgreSQL (tables: notes, tags, note_tags).\n"
        "Provides endpoints for notes CRUD, search, tags, and pin/favorite toggles."
    ),
    version="1.0.0",
    openapi_tags=openapi_tags,
)

# CORS: allow frontend to call the API.
#
# IMPORTANT: Browsers disallow `Access-Control-Allow-Origin: *` when
# `Access-Control-Allow-Credentials: true` is set. The runtime environment for
# this project provides ALLOWED_ORIGINS/HEADERS/METHODS; we honor those here.
import os


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


allowed_origins = _split_csv(os.getenv("ALLOWED_ORIGINS")) or ["http://localhost:3000"]
allowed_methods = _split_csv(os.getenv("ALLOWED_METHODS")) or ["*"]
allowed_headers = _split_csv(os.getenv("ALLOWED_HEADERS")) or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=allowed_methods,
    allow_headers=allowed_headers,
)


@app.get(
    "/",
    tags=["system"],
    summary="Health check",
    description="Simple health check endpoint.",
    operation_id="health_check",
)
def health_check():
    """Health check endpoint.

    Returns:
        JSON object indicating service status.
    """
    return {"message": "Healthy"}


# Include API routers
app.include_router(notes_router)
app.include_router(tags_router)
