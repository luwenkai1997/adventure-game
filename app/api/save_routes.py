from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.container import container
from app.models.save import SaveCreateRequest


router = APIRouter()


@router.get("/api/save/list")
async def list_saves(request: Request):
    ctx = container.context_resolver.resolve_required(request)
    saves = container.save_service.list_saves(ctx)
    return JSONResponse(content={"success": True, "saves": saves, "total": len(saves)})


@router.get("/api/save/{slot_id}")
async def get_save(request: Request, slot_id: str):
    ctx = container.context_resolver.resolve_required(request)
    save = container.save_service.get_save(ctx, slot_id)
    if not save:
        return JSONResponse(status_code=404, content={"error": "存档不存在"})
    return JSONResponse(content={"success": True, "save": save})


@router.post("/api/save/{slot_id}")
async def save_game(request: Request, slot_id: str, body: SaveCreateRequest):
    ctx = container.context_resolver.resolve_required(request)
    body.slot_id = slot_id
    result = container.save_service.save_game(ctx, body)
    return JSONResponse(content=result)


@router.delete("/api/save/{slot_id}")
async def delete_save(request: Request, slot_id: str):
    ctx = container.context_resolver.resolve_required(request)
    if container.save_service.delete_save(ctx, slot_id):
        return JSONResponse(content={"success": True})
    return JSONResponse(status_code=404, content={"error": "存档不存在"})


@router.get("/api/save/load/{slot_id}")
async def load_save_get(request: Request, slot_id: str):
    ctx = container.context_resolver.resolve_required(request)
    save = container.save_service.load_save(ctx, slot_id)
    if not save:
        return JSONResponse(status_code=404, content={"error": "存档不存在"})
    container.save_service.restore_history(ctx, save.get("history") or [])
    return JSONResponse(content={"success": True, "save": save})


@router.post("/api/save/load/{slot_id}")
async def load_save(request: Request, slot_id: str):
    ctx = container.context_resolver.resolve_required(request)
    save = container.save_service.load_save(ctx, slot_id)
    if not save:
        return JSONResponse(status_code=404, content={"error": "存档不存在"})
    container.save_service.restore_history(ctx, save.get("history") or [])
    return JSONResponse(content={"success": True, "save": save})


@router.get("/api/history")
async def get_history(request: Request):
    ctx = container.context_resolver.resolve_required(request)
    history = container.save_service.get_history(ctx)
    return JSONResponse(content={"success": True, "history": history, "count": len(history)})


@router.post("/api/history")
async def push_history(request: Request, snapshot: dict):
    ctx = container.context_resolver.resolve_required(request)
    container.save_service.push_history(ctx, snapshot)
    return JSONResponse(content={"success": True})


@router.post("/api/history/undo")
async def undo(request: Request):
    ctx = container.context_resolver.resolve_required(request)
    snapshot = container.save_service.undo(ctx)
    if not snapshot:
        return JSONResponse(status_code=404, content={"error": "没有可回退的历史"})
    return JSONResponse(content={"success": True, "snapshot": snapshot})


@router.delete("/api/history")
async def clear_history(request: Request):
    ctx = container.context_resolver.resolve_required(request)
    container.save_service.clear_history(ctx)
    return JSONResponse(content={"success": True})


@router.get("/api/history/count")
async def get_history_count(request: Request):
    ctx = container.context_resolver.resolve_required(request)
    count = container.save_service.get_history_count(ctx)
    return JSONResponse(content={"success": True, "count": count})
