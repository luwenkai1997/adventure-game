from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.container import container

router = APIRouter()


@router.post("/api/item/use/{item_id}")
async def use_item(request: Request, item_id: str):
    ctx = container.context_resolver.resolve_required(request)
    result = container.item_service.use_item(ctx, item_id)
    return JSONResponse(content=result)


@router.post("/api/item/equip/{item_id}")
async def equip_item(request: Request, item_id: str):
    ctx = container.context_resolver.resolve_required(request)
    result = container.item_service.toggle_equip(ctx, item_id)
    return JSONResponse(content=result)


@router.get("/api/item/equipment")
async def get_equipment(request: Request):
    ctx = container.context_resolver.resolve_required(request)
    equipment = container.item_service.get_equipment(ctx)
    return JSONResponse(content={"success": True, "equipment": equipment})
