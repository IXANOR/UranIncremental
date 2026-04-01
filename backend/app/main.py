from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes.economy import router as economy_router
from app.api.routes.game import router as game_router
from app.api.routes.health import router as health_router
from app.api.routes.test_admin import router as test_admin_router
from app.api.routes.time import router as time_router

app = FastAPI(title="UranIncremental API", version="0.1.0")

app.include_router(health_router)
app.include_router(game_router)
app.include_router(economy_router)
app.include_router(time_router)
app.include_router(test_admin_router)

# Serve built frontend from frontend/dist/ when present (production mode)
_frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
