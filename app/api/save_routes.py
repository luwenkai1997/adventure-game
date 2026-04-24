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


@router.post("/api/save/auto")
async def auto_save(request: Request, body: SaveCreateRequest):
    ctx = container.context_resolver.resolve_required(request)
    body.slot_id = "auto"
    result = container.save_service.save_game(ctx, body)
    return JSONResponse(content=result)


@router.get("/api/save/auto")
async def get_auto_save(request: Request):
    ctx = container.context_resolver.resolve_required(request)
    save = container.save_service.get_save(ctx, "auto")
    if not save:
        return JSONResponse(status_code=404, content={"error": "自动存档不存在"})
    return JSONResponse(content={"success": True, "save": save})


@router.get("/api/save/{slot_id}/export")
async def export_save(request: Request, slot_id: str):
    ctx = container.context_resolver.resolve_required(request)
    save = container.save_service.get_save(ctx, slot_id)
    if not save:
        return JSONResponse(status_code=404, content={"error": "存档不存在"})

    import json as _json
    export_data = _json.dumps(save, ensure_ascii=False, indent=2)
    return JSONResponse(
        content={"success": True, "save": save, "export_json": export_data},
        headers={
            "Content-Disposition": f"attachment; filename=adventure_save_{slot_id}.json"
        },
    )


@router.post("/api/save/import")
async def import_save(request: Request):
    ctx = container.context_resolver.resolve_required(request)
    body = await request.json()

    save_data = body.get("save") or body
    if isinstance(save_data, str):
        import json as _json
        save_data = _json.loads(save_data)

    original_slot = save_data.get("slot_id", "imported")
    if original_slot == "auto":
        original_slot = "imported"

    existing = container.save_service.get_save(ctx, original_slot)
    target_slot = original_slot
    if existing:
        import uuid as _uuid
        target_slot = f"imported_{_uuid.uuid4().hex[:6]}"

    save_data["slot_id"] = target_slot
    container.save_repository.save_game_state(ctx, target_slot, save_data)

    return JSONResponse({"success": True, "slot_id": target_slot})
