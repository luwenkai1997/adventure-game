from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.container import container
from app.models.save import SaveCreateRequest


router = APIRouter()


@router.get("/api/save/list")
async def list_saves(request: Request):
    try:
        ctx = container.context_resolver.resolve_required(request)
        saves = container.save_service.list_saves(ctx)
        return JSONResponse(content={"success": True, "saves": saves, "total": len(saves)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"获取存档列表失败: {str(e)}"})


@router.get("/api/save/{slot_id}")
async def get_save(request: Request, slot_id: str):
    try:
        ctx = container.context_resolver.resolve_required(request)
        save = container.save_service.get_save(ctx, slot_id)
        if not save:
            return JSONResponse(status_code=404, content={"error": "存档不存在"})
        return JSONResponse(content={"success": True, "save": save})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"获取存档失败: {str(e)}"})


@router.post("/api/save/{slot_id}")
async def save_game(request: Request, slot_id: str, body: SaveCreateRequest):
    try:
        ctx = container.context_resolver.resolve_required(request)
        body.slot_id = slot_id
        result = container.save_service.save_game(ctx, body)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"保存失败: {str(e)}"})


@router.delete("/api/save/{slot_id}")
async def delete_save(request: Request, slot_id: str):
    try:
        ctx = container.context_resolver.resolve_required(request)
        if container.save_service.delete_save(ctx, slot_id):
            return JSONResponse(content={"success": True})
        return JSONResponse(status_code=404, content={"error": "存档不存在"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"删除失败: {str(e)}"})


@router.get("/api/save/load/{slot_id}")
async def load_save_get(request: Request, slot_id: str):
    try:
        ctx = container.context_resolver.resolve_required(request)
        save = container.save_service.load_save(ctx, slot_id)
        if not save:
            return JSONResponse(status_code=404, content={"error": "存档不存在"})
        container.save_service.restore_history(ctx, save.get("history") or [])
        return JSONResponse(content={"success": True, "save": save})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"加载失败: {str(e)}"})


@router.post("/api/save/load/{slot_id}")
async def load_save(request: Request, slot_id: str):
    try:
        ctx = container.context_resolver.resolve_required(request)
        save = container.save_service.load_save(ctx, slot_id)
        if not save:
            return JSONResponse(status_code=404, content={"error": "存档不存在"})
        container.save_service.restore_history(ctx, save.get("history") or [])
        return JSONResponse(content={"success": True, "save": save})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"加载失败: {str(e)}"})


@router.get("/api/history")
async def get_history(request: Request):
    try:
        ctx = container.context_resolver.resolve_required(request)
        history = container.save_service.get_history(ctx)
        return JSONResponse(content={"success": True, "history": history, "count": len(history)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"获取历史失败: {str(e)}"})


@router.post("/api/history")
async def push_history(request: Request, snapshot: dict):
    try:
        ctx = container.context_resolver.resolve_required(request)
        container.save_service.push_history(ctx, snapshot)
        return JSONResponse(content={"success": True})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"保存历史失败: {str(e)}"})


@router.post("/api/history/undo")
async def undo(request: Request):
    try:
        ctx = container.context_resolver.resolve_required(request)
        snapshot = container.save_service.undo(ctx)
        if not snapshot:
            return JSONResponse(status_code=404, content={"error": "没有可回退的历史"})
        return JSONResponse(content={"success": True, "snapshot": snapshot})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"回退失败: {str(e)}"})


@router.delete("/api/history")
async def clear_history(request: Request):
    try:
        ctx = container.context_resolver.resolve_required(request)
        container.save_service.clear_history(ctx)
        return JSONResponse(content={"success": True})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"清空失败: {str(e)}"})


@router.get("/api/history/count")
async def get_history_count(request: Request):
    try:
        ctx = container.context_resolver.resolve_required(request)
        count = container.save_service.get_history_count(ctx)
        return JSONResponse(content={"success": True, "count": count})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"获取数量失败: {str(e)}"})
