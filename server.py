from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response

from app.api.game_routes import router as game_router
from app.api.character_routes import router as character_router
from app.api.novel_routes import router as novel_router
from app.api.player_routes import router as player_router
from app.api.check_routes import router as check_router
from app.api.save_routes import router as save_router
from app.middleware.session_middleware import SessionMiddleware
from app.config import BASE_DIR
from app.http_client import init_http_client, close_http_client
from app.utils.file_storage import load_session_games_from_disk
from app.errors import AppError, app_error_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_session_games_from_disk()
    await init_http_client()
    yield
    await close_http_client()


app = FastAPI(lifespan=lifespan)

app.add_exception_handler(AppError, app_error_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware)

app.include_router(game_router)
app.include_router(character_router)
app.include_router(novel_router)
app.include_router(player_router)
app.include_router(check_router)
app.include_router(save_router)

_static_dir = os.path.join(BASE_DIR, "static")
if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")


@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)
