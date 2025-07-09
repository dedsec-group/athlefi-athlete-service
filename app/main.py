"""FastAPI application with basic endpoints."""

from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import text
import logfire
from app.config import create_db_and_tables, engine
from app.router import router as athlete_router


logfire.configure(
    service_name="athlete-service",
    send_to_logfire=False,
)


@asynccontextmanager
async def lifespan(_fastapi_app: FastAPI):
    """Create the database and tables on startup."""
    await create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(athlete_router)


@app.get("/health")
async def health_check():
    """Health check endpoint to verify API and database status."""
    try:
        # Check database connection
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))

        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "service": "athlete-service",
                "database": "connected",
                "timestamp": datetime.now().isoformat()
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "service": "athlete-service",
                "database": "disconnected",
                "error": str(e)
            }
        ) from e

logfire.instrument_fastapi(app)
