from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.game_routes import router as game_router
from app.api.character_routes import router as character_router
from app.api.novel_routes import router as novel_router


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(game_router)
app.include_router(character_router)
app.include_router(novel_router)
