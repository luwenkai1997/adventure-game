from fastapi import APIRouter
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import os
import uuid
import json
from app.config import BASE_DIR, STORY_EXPANSION_PROMPT, API_STREAMING_ENABLED
from app.utils.game_manager import (
    create_game_structure,
    list_all_games,
    get_game_info,
    delete_game,
    update_game_info,
    get_game_dir,
)
from app.utils.file_storage import (
    set_current_game,
    get_current_game,
    init_new_game,
    save_memory,
    save_memory_text,
    load_memory,
)
from app.services.game_service import GameService
from app.services.prompt_composer import PromptComposer
from app.services.chat_parser import (
    parse_chat_output,
    get_repair_prompt,
    ParseError,
    ChatTurnContent,
)
from app.services.llm_gateway import (
    stream_llm,
    cancel_request,
    is_cancelled,
)
from app.models.chat import ChatRequestV2, ChatResponseV2, ChatTurnContent
from app.utils.llm_client import call_llm


router = APIRouter()
game_service = GameService()
composer = PromptComposer()


class CreateGameRequest(BaseModel):
    world_setting: str = ""


class UpdateGameRequest(BaseModel):
    status: Optional[str] = None
    world_setting: Optional[str] = None


class ChatRequest(BaseModel):
    messages: List[dict]
    extraPrompt: str = ""


class MemoryRequest(BaseModel):
    worldSetting: str
    storySummary: str = ""


class UpdateMemoryRequest(BaseModel):
    scene: str
    selectedChoice: str
    logSummary: str
    endingType: str = ""


class StoryExpansionRequest(BaseModel):
    user_input: str


@router.get("/", response_class=HTMLResponse)
async def index():
    html_path = os.path.join(BASE_DIR, 'index.html')
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return content


@router.post("/api/chat")
async def chat(request: ChatRequestV2):
    try:
        request_id = str(uuid.uuid4())
        parsed_content, raw_content = game_service.chat(
            request.messages,
            request.extraPrompt,
            request.turn_context,
        )
        response = ChatResponseV2(
            success=True,
            content=parsed_content,
            raw_content=raw_content,
            meta={
                "request_id": request_id,
                "repaired": False,
            }
        )
        return JSONResponse(content=response.model_dump())
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={'success': False, 'error': f'服务器错误: {str(e)}'})


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


@router.post("/api/story/expand")
async def api_expand_story(request: StoryExpansionRequest):
    try:
        if not request.user_input or not request.user_input.strip():
            return JSONResponse(status_code=400, content={'error': '请输入故事设定'})
        
        prompt = STORY_EXPANSION_PROMPT.format(user_input=request.user_input)
        
        expanded_story = call_llm(
            prompt, 
            "你是一个专业的游戏世界观设计师，擅长创造丰富、引人入胜的故事设定。",
            timeout=120
        )
        
        return JSONResponse(content={
            'success': True,
            'expanded_story': expanded_story
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={'error': f'故事补全失败: {str(e)}'})


@router.post("/api/games/create")
async def api_create_game(request: CreateGameRequest):
    try:
        paths = init_new_game(request.world_setting)
        game_id = paths["game_dir"].split("/")[-1]
        return JSONResponse(content={
            "success": True,
            "game_id": game_id,
            "paths": {k: v for k, v in paths.items() if k != "game_info"}
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"创建游戏失败: {str(e)}"})


@router.get("/api/games")
async def api_list_games():
    try:
        games = list_all_games()
        return JSONResponse(content={"games": games, "count": len(games)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"获取游戏列表失败: {str(e)}"})


@router.get("/api/games/current")
async def api_get_current_game():
    try:
        game_id = get_current_game()
        if game_id:
            game_info = get_game_info(game_id)
            return JSONResponse(content={"current_game": game_id, "game_info": game_info})
        return JSONResponse(content={"current_game": None, "game_info": None})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"获取当前游戏失败: {str(e)}"})


@router.post("/api/games/load/{game_id}")
async def api_load_game(game_id: str):
    try:
        game_dir = get_game_dir(game_id)
        set_current_game(game_id)
        game_info = get_game_info(game_id)
        return JSONResponse(content={
            "success": True,
            "game_id": game_id,
            "game_info": game_info
        })
    except FileNotFoundError:
        return JSONResponse(status_code=404, content={"error": f"游戏不存在: {game_id}"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"加载游戏失败: {str(e)}"})


@router.get("/api/games/{game_id}")
async def api_get_game(game_id: str):
    try:
        game_info = get_game_info(game_id)
        if game_info:
            return JSONResponse(content={"game_info": game_info})
        return JSONResponse(status_code=404, content={"error": "游戏不存在"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"获取游戏信息失败: {str(e)}"})


@router.put("/api/games/{game_id}")
async def api_update_game(game_id: str, request: UpdateGameRequest):
    try:
        updates = {k: v for k, v in request.model_dump().items() if v is not None}
        game_info = update_game_info(game_id, updates)
        return JSONResponse(content={"success": True, "game_info": game_info})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"更新游戏失败: {str(e)}"})


@router.delete("/api/games/{game_id}")
async def api_delete_game(game_id: str):
    try:
        if delete_game(game_id):
            return JSONResponse(content={"success": True})
        return JSONResponse(status_code=404, content={"error": "游戏不存在"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"删除游戏失败: {str(e)}"})


@router.post("/api/chat/stream")
async def chat_stream(request: ChatRequestV2):
    request_id = str(uuid.uuid4())
    full_messages = composer.compose(
        messages=request.messages,
        extra_prompt=request.extraPrompt,
        turn_context=request.turn_context,
    )
    prompt = "\n".join([msg["content"] for msg in full_messages])
    system_prompt = None

    def event_generator():
        full_content = ""
        for chunk in stream_llm(prompt, system_prompt, request_id):
            full_content += chunk
            if is_cancelled(request_id):
                yield f"data: {{\"type\": \"cancelled\"}}\n\n"
                break
            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk}, ensure_ascii=False)}\n\n"

        if not is_cancelled(request_id):
            try:
                parsed_content, _ = parse_chat_output(full_content)
                result = {
                    "type": "done",
                    "success": True,
                    "content": parsed_content.model_dump(),
                    "request_id": request_id,
                }
            except ParseError as e:
                result = {
                    "type": "error",
                    "success": False,
                    "error": f"解析失败: {e.message}",
                    "request_id": request_id,
                }
            yield f"data: {json.dumps(result, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/api/chat/cancel/{request_id}")
async def cancel_chat(request_id: str):
    cancel_request(request_id)
    return JSONResponse(content={"success": True, "request_id": request_id})
