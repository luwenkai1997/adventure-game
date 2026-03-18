import os
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from app.models.novel import ChatRequest, UpdateMemoryRequest, MemoryRequest
from app.services.game_service import GameService
from app.utils.file_storage import save_memory
from app.config import BASE_DIR


router = APIRouter()
game_service = GameService()


@router.get("/", response_class=HTMLResponse)
async def index():
    html_path = os.path.join(BASE_DIR, 'index.html')
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return content


@router.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        content = game_service.chat(request.messages, request.extraPrompt)
        return JSONResponse(content={'content': content})
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': f'服务器错误: {str(e)}'})


@router.post("/api/save-memory")
async def api_save_memory(request: MemoryRequest):
    try:
        memory_path = save_memory(request.worldSetting, request.storySummary)
        return JSONResponse(content={'success': True, 'memory_path': memory_path})
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': f'保存失败: {str(e)}'})


@router.post("/api/update-memory")
async def api_update_memory(request: UpdateMemoryRequest):
    try:
        game_service.update_memory(
            request.scene,
            request.selectedChoice,
            request.logSummary,
            request.endingType
        )
        return JSONResponse(content={'success': True})
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': f'更新失败: {str(e)}'})
