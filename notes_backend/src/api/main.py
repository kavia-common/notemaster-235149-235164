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

# CORS: allow frontend to call the API. In production, set allow_origins to your frontend URL(s).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
