from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.models.save import SaveCreateRequest
from app.services.save_service import SaveService


router = APIRouter()
save_service = SaveService()


@router.get("/api/save/list")
async def list_saves():
    try:
        saves = save_service.list_saves()
        return JSONResponse(
            content={"success": True, "saves": saves, "total": len(saves)}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"error": f"获取存档列表失败: {str(e)}"}
        )


@router.get("/api/save/{slot_id}")
async def get_save(slot_id: str):
    try:
        save = save_service.get_save(slot_id)
        if not save:
            return JSONResponse(status_code=404, content={"error": "存档不存在"})
        return JSONResponse(content={"success": True, "save": save})
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"error": f"获取存档失败: {str(e)}"}
        )


@router.post("/api/save/{slot_id}")
async def save_game(slot_id: str, request: SaveCreateRequest):
    try:
        request.slot_id = slot_id
        result = save_service.save_game(request)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"保存失败: {str(e)}"})


@router.delete("/api/save/{slot_id}")
async def delete_save(slot_id: str):
    try:
        if save_service.delete_save(slot_id):
            return JSONResponse(content={"success": True})
        return JSONResponse(status_code=404, content={"error": "存档不存在"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"删除失败: {str(e)}"})


@router.get("/api/save/load/{slot_id}")
async def load_save_get(slot_id: str):
    try:
        save = save_service.load_save(slot_id)
        if not save:
            return JSONResponse(status_code=404, content={"error": "存档不存在"})
        save_service.restore_history(save.get("history") or [])
        return JSONResponse(content={"success": True, "save": save})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"加载失败: {str(e)}"})


@router.post("/api/save/load/{slot_id}")
async def load_save(slot_id: str):
    try:
        save = save_service.load_save(slot_id)
        if not save:
            return JSONResponse(status_code=404, content={"error": "存档不存在"})
        # Restore the undo history that was active when this save was created.
        # Falls back to clearing history if the save predates history snapshots.
        save_service.restore_history(save.get("history") or [])
        return JSONResponse(content={"success": True, "save": save})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"加载失败: {str(e)}"})


@router.get("/api/history")
async def get_history():
    try:
        history = save_service.get_history()
        return JSONResponse(
            content={"success": True, "history": history, "count": len(history)}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"error": f"获取历史失败: {str(e)}"}
        )


@router.post("/api/history")
async def push_history(snapshot: dict):
    try:
        save_service.push_history(snapshot)
        return JSONResponse(content={"success": True})
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"error": f"保存历史失败: {str(e)}"}
        )


@router.post("/api/history/undo")
async def undo():
    try:
        snapshot = save_service.undo()
        if not snapshot:
            return JSONResponse(status_code=404, content={"error": "没有可回退的历史"})
        return JSONResponse(content={"success": True, "snapshot": snapshot})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"回退失败: {str(e)}"})


@router.delete("/api/history")
async def clear_history():
    try:
        save_service.clear_history()
        return JSONResponse(content={"success": True})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"清空失败: {str(e)}"})


@router.get("/api/history/count")
async def get_history_count():
    try:
        count = save_service.get_history_count()
        return JSONResponse(content={"success": True, "count": count})
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"error": f"获取数量失败: {str(e)}"}
        )
