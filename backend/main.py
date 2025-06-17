from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import router as api_router
from app.core.config import settings, logger

# Initialize the FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0",
    description="An AI agent for planning trips, powered by LangGraph, Gemini, and FastAPI.",
)

# Set up CORS (Cross-Origin Resource Sharing)
# This is crucial for allowing your frontend application to communicate with this backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, you should restrict this to your frontend's domain.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the API router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up AI Trip Planner API...")

@app.get("/", tags=["Root"])
def read_root():
    """A simple health check endpoint to confirm the API is running."""
    return {"status": "ok", "message": f"Welcome to the {settings.PROJECT_NAME} API!"}