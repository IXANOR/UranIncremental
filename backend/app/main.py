from fastapi import FastAPI

from app.api.routes.economy import router as economy_router
from app.api.routes.game import router as game_router
from app.api.routes.health import router as health_router
from app.api.routes.time import router as time_router

app = FastAPI(title="UranIncremental API", version="0.1.0")

app.include_router(health_router)
app.include_router(game_router)
app.include_router(economy_router)
app.include_router(time_router)
