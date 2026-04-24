import json
import os
import uuid

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Any, Optional

from app.config import BASE_DIR, STORY_EXPANSION_PROMPT
from app.container import container
from app.errors import AppError
from app.models.chat import ChatRequestV2, ChatResponseV2


router = APIRouter()


class CreateGameRequest(BaseModel):
    world_setting: str = ""


class UpdateGameRequest(BaseModel):
    status: Optional[str] = None
    world_setting: Optional[str] = None


class MemoryRequest(BaseModel):
    worldSetting: str
    storySummary: str = ""


class UpdateMemoryRequest(BaseModel):
    scene: str
    selectedChoice: str
    logSummary: str
    endingType: str = ""
    checkResult: Optional[Any] = None
    relationshipChanges: Optional[Any] = None
    routeScores: Optional[Any] = None
    currentRound: Optional[int] = None


class StoryExpansionRequest(BaseModel):
    user_input: str


@router.get("/", response_class=HTMLResponse)
async def index():
    html_path = os.path.join(BASE_DIR, "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()


@router.post("/api/chat")
async def chat(request: Request, body: ChatRequestV2):
    ctx = container.context_resolver.resolve_optional(request)
    request_id = str(uuid.uuid4())
    parsed_content, raw_content, repaired = await container.game_service.chat(
        ctx,
        body.messages,
        body.extraPrompt,
        body.turn_context,
    )

    if parsed_content.relationship_changes:
        await container.game_service.apply_relationship_changes(
            ctx, parsed_content.relationship_changes
        )

    if parsed_content.inventory_changes:
        container.game_service.apply_inventory_changes(
            ctx, parsed_content.inventory_changes
        )

    response = ChatResponseV2(
        success=True,
        content=parsed_content,
        raw_content=raw_content,
        meta={"request_id": request_id, "repaired": repaired},
    )
    return JSONResponse(content=response.model_dump())


@router.post("/api/save-memory")
async def api_save_memory(request: Request, body: MemoryRequest):
    ctx = container.context_resolver.resolve_required(request)
    memory_path = container.memory_repository.save_initial(
        ctx, body.worldSetting, body.storySummary
    )
    return JSONResponse(content={"success": True, "memory_path": memory_path})


@router.post("/api/update-memory")
async def api_update_memory(request: Request, body: UpdateMemoryRequest):
    ctx = container.context_resolver.resolve_required(request)
    await container.game_service.update_memory(
        ctx,
        body.scene,
        body.selectedChoice,
        body.logSummary,
        body.endingType,
        check_result=body.checkResult,
        relationship_changes=body.relationshipChanges,
        route_scores=body.routeScores,
        current_round=body.currentRound,
    )
    return JSONResponse(content={"success": True})


@router.post("/api/story/expand")
async def api_expand_story(body: StoryExpansionRequest):
    if not body.user_input or not body.user_input.strip():
        raise AppError(code="validation_error", message="请输入故事设定", status_code=400)

    expanded_story = await container.llm_adapter.generate_text(
        ctx=None,
        prompt=STORY_EXPANSION_PROMPT.format(user_input=body.user_input),
        system_prompt="你是一个专业的游戏世界观设计师，擅长创造丰富、引人入胜的故事设定。",
        timeout=120,
        method_name="expand_story",
    )
    return JSONResponse(content={"success": True, "expanded_story": expanded_story})


@router.post("/api/games/create")
async def api_create_game(request: Request, body: CreateGameRequest):
    paths = container.game_repository.create(body.world_setting)
    game_id = os.path.basename(paths["game_dir"])
    session_id = container.context_resolver.get_session_id_from_request(request)
    container.session_repository.set_active_game(session_id, game_id)
    return JSONResponse(
        content={
            "success": True,
            "game_id": game_id,
            "paths": {key: value for key, value in paths.items() if key != "game_info"},
        }
    )


@router.get("/api/games")
async def api_list_games():
    games = container.game_repository.list_all()
    return JSONResponse(content={"games": games, "count": len(games)})


@router.get("/api/games/current")
async def api_get_current_game(request: Request):
    ctx = container.context_resolver.resolve_optional(request)
    if ctx:
        game_info = container.game_repository.get_game_info(ctx.game_id)
        return JSONResponse(content={"current_game": ctx.game_id, "game_info": game_info})
    return JSONResponse(content={"current_game": None, "game_info": None})


@router.post("/api/games/load/{game_id}")
async def api_load_game(request: Request, game_id: str):
    if not container.game_repository.exists(game_id):
        return JSONResponse(status_code=404, content={"error": f"游戏不存在: {game_id}"})
    session_id = container.context_resolver.get_session_id_from_request(request)
    container.session_repository.set_active_game(session_id, game_id)
    game_info = container.game_repository.get_game_info(game_id)
    return JSONResponse(content={"success": True, "game_id": game_id, "game_info": game_info})


@router.get("/api/games/{game_id}")
async def api_get_game(game_id: str):
    game_info = container.game_repository.get_game_info(game_id)
    if game_info:
        return JSONResponse(content={"game_info": game_info})
    return JSONResponse(status_code=404, content={"error": "游戏不存在"})


@router.put("/api/games/{game_id}")
async def api_update_game(game_id: str, body: UpdateGameRequest):
    updates = {key: value for key, value in body.model_dump().items() if value is not None}
    game_info = container.game_repository.update_game_info(game_id, updates)
    return JSONResponse(content={"success": True, "game_info": game_info})


@router.delete("/api/games/{game_id}")
async def api_delete_game(game_id: str):
    if container.game_repository.delete(game_id):
        container.session_repository.remove_game_references(game_id)
        return JSONResponse(content={"success": True})
    return JSONResponse(status_code=404, content={"error": "游戏不存在"})


@router.post("/api/chat/stream")
async def chat_stream(request: Request, body: ChatRequestV2):
    ctx = container.context_resolver.resolve_optional(request)
    full_messages = container.prompt_composer.compose(
        ctx=ctx,
        messages=body.messages,
        extra_prompt=body.extraPrompt,
        turn_context=body.turn_context,
        tendency_data=body.turn_context.get("tendency") if body.turn_context else None,
    )
    request_id = str(uuid.uuid4())

    async def event_generator():
        async for event in container.llm_adapter.stream_chat_turn(
            ctx, full_messages, request_id=request_id
        ):
            if event.type == "chunk":
                yield f"data: {json.dumps({'type': 'chunk', 'content': event.content}, ensure_ascii=False)}\n\n"
            elif event.type == "cancelled":
                yield 'data: {"type": "cancelled"}\n\n'
            elif event.type == "done":
                if ctx and ctx.game_id:
                    try:
                        turn_num = len(body.messages) // 2 + 1
                        container.character_service.create_snapshot(ctx, turn_num)
                    except Exception as e:
                        print(f"Failed to create snapshot: {e}")

                # Apply side effects
                if ctx is not None and event.payload:
                    payload = event.payload
                    rel_changes = payload.get("relationship_changes") or []
                    inv_changes_raw = payload.get("inventory_changes") or []
                    if rel_changes:
                        try:
                            from app.models.chat import RelationshipChange
                            changes = [RelationshipChange(**c) if isinstance(c, dict) else c for c in rel_changes]
                            await container.game_service.apply_relationship_changes(ctx, changes)
                        except Exception:
                            pass
                    if inv_changes_raw:
                        try:
                            from app.models.chat import InventoryChange
                            changes = [InventoryChange(**c) if isinstance(c, dict) else c for c in inv_changes_raw]
                            container.game_service.apply_inventory_changes(ctx, changes)
                        except Exception:
                            pass

                yield (
                    "data: "
                    + json.dumps(
                        {
                            "type": "done",
                            "success": True,
                            "content": event.payload,
                            "request_id": request_id,
                            "repaired": event.repaired,
                        },
                        ensure_ascii=False,
                    )
                    + "\n\n"
                )
            elif event.type == "error":
                yield (
                    "data: "
                    + json.dumps(
                        {
                            "type": "error",
                            "success": False,
                            "error": event.error,
                            "request_id": request_id,
                        },
                        ensure_ascii=False,
                    )
                    + "\n\n"
                )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.websocket("/ws/chat/stream")
async def ws_chat_stream(websocket: WebSocket):
    ctx = container.context_resolver.resolve_optional_websocket(websocket)
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        body = ChatRequestV2.model_validate(data)
    except Exception as e:
        await websocket.send_json({"type": "error", "success": False, "error": f"无效请求: {e}"})
        await websocket.close()
        return

    request_id = str(uuid.uuid4())
    full_messages = container.prompt_composer.compose(
        ctx=ctx,
        messages=body.messages,
        extra_prompt=body.extraPrompt,
        turn_context=body.turn_context,
        tendency_data=body.turn_context.get("tendency") if body.turn_context else None,
    )

    try:
        async for event in container.llm_adapter.stream_chat_turn(
            ctx, full_messages, request_id=request_id
        ):
            if event.type == "chunk":
                await websocket.send_json({"type": "chunk", "content": event.content})
            elif event.type == "cancelled":
                await websocket.send_json({"type": "cancelled", "request_id": request_id})
                return
            elif event.type == "done":
                if ctx and ctx.game_id:
                    try:
                        turn_num = len(body.messages) // 2 + 1
                        container.character_service.create_snapshot(ctx, turn_num)
                    except Exception as e:
                        print(f"Failed to create snapshot: {e}")
                await websocket.send_json(
                    {
                        "type": "done",
                        "success": True,
                        "content": event.payload,
                        "request_id": request_id,
                        "repaired": event.repaired,
                    }
                )
            elif event.type == "error":
                await websocket.send_json(
                    {
                        "type": "error",
                        "success": False,
                        "error": event.error,
                        "request_id": request_id,
                    }
                )
    except WebSocketDisconnect:
        container.llm_adapter.cancel_request(request_id)
    except Exception as e:
        await websocket.send_json(
            {"type": "error", "success": False, "error": str(e), "request_id": request_id}
        )


@router.post("/api/chat/cancel/{request_id}")
async def cancel_chat(request_id: str):
    container.llm_adapter.cancel_request(request_id)
    return JSONResponse(content={"success": True, "request_id": request_id})
