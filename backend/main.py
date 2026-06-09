"""
FastAPI application entry point.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

from backend.config import settings
from backend.database.connection import init_db
from backend.api import words, agents, review, stats

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered vocabulary learning system with Agent workflows",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    print("Starting AI Vocabulary Assistant...")
    init_db()
    print("Database initialized")
    print(f"App: {settings.APP_NAME} v{settings.APP_VERSION}")

app.include_router(words.router)
app.include_router(agents.router)
app.include_router(review.router)
app.include_router(stats.router)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "app_url": "/app"
    }

# Serve frontend
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
frontend_path = os.path.abspath(frontend_path)

if os.path.exists(frontend_path):
    print(f"Serving frontend from: {frontend_path}")
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/app", response_class=HTMLResponse)
    async def serve_frontend():
        index_path = os.path.join(frontend_path, "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()

    @app.get("/style.css")
    async def serve_css():
        return FileResponse(
            os.path.join(frontend_path, "style.css"),
            media_type="text/css"
        )

    @app.get("/app.js")
    async def serve_js():
        return FileResponse(
            os.path.join(frontend_path, "app.js"),
            media_type="application/javascript"
        )

@app.post("/webhook")
async def telegram_webhook(update: dict):
    from backend.telegram.bot import handle_update
    await handle_update(update)
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)