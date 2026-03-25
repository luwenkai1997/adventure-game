from fastapi import APIRouter
from fastapi.responses import JSONResponse
from typing import Optional
from app.models.player import (
    PlayerCreateRequest,
    PlayerRandomRequest,
    PlayerUpdateRequest,
    PRESET_SKILLS,
    ATTRIBUTE_NAMES_CN,
    ATTRIBUTE_NAMES_EN,
)
from app.services.player_service import PlayerService
from app.utils.file_storage import delete_player as delete_player_file


router = APIRouter()
player_service = PlayerService()


@router.get("/api/player/skills")
async def get_preset_skills():
    return JSONResponse(
        content={"skills": PRESET_SKILLS, "attribute_names": ATTRIBUTE_NAMES_CN}
    )


@router.get("/api/player/attributes")
async def get_attribute_names():
    return JSONResponse(
        content={"en_to_cn": ATTRIBUTE_NAMES_CN, "cn_to_en": ATTRIBUTE_NAMES_EN}
    )


@router.post("/api/player/create")
async def create_player(request: PlayerCreateRequest):
    try:
        player = player_service.create_player(request)
        return JSONResponse(content={"success": True, "player": player.model_dump()})
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"error": f"创建角色失败: {str(e)}"}
        )


@router.post("/api/player/random")
async def random_player(request: Optional[PlayerRandomRequest] = None):
    try:
        player = player_service.random_player(request)
        return JSONResponse(content={"success": True, "player": player.model_dump()})
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"error": f"生成角色失败: {str(e)}"}
        )


@router.post("/api/player/generate")
async def generate_player(request: Optional[PlayerRandomRequest] = None):
    """使用LLM根据世界观生成主角"""
    import asyncio
    
    try:
        world_setting = request.world_setting if request else ""
        
        try:
            player = await asyncio.wait_for(
                player_service.generate_player_with_llm(world_setting),
                timeout=60.0,
            )
            if player:
                return JSONResponse(content={"success": True, "player": player.model_dump()})
            else:
                # LLM生成失败，回退到随机生成
                player = player_service.random_player(request)
                return JSONResponse(content={
                    "success": True, 
                    "player": player.model_dump(),
                    "warning": "LLM生成失败，已使用随机角色"
                })
        except asyncio.TimeoutError:
            # 超时，回退到随机生成
            player = player_service.random_player(request)
            return JSONResponse(content={
                "success": True, 
                "player": player.model_dump(),
                "warning": "LLM生成超时，已使用随机角色"
            })
    except Exception as e:
        import traceback
        print(f"生成主角时出错: {str(e)}")
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500, content={"error": f"生成角色失败: {str(e)}"}
        )


@router.get("/api/player")
async def get_player():
    try:
        player = player_service.get_player()
        if not player:
            return JSONResponse(content={"exists": False, "player": None})
        return JSONResponse(content={"exists": True, "player": player.model_dump()})
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"error": f"获取角色失败: {str(e)}"}
        )


@router.put("/api/player")
async def update_player(request: PlayerUpdateRequest):
    try:
        updates = request.model_dump(exclude_none=True)
        player = player_service.update_player(updates)
        if not player:
            return JSONResponse(status_code=404, content={"error": "玩家角色不存在"})
        return JSONResponse(content={"success": True, "player": player.model_dump()})
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"error": f"更新角色失败: {str(e)}"}
        )


@router.get("/api/player/summary")
async def get_player_summary():
    try:
        summary = player_service.get_player_summary()
        return JSONResponse(content={"summary": summary})
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"error": f"获取角色摘要失败: {str(e)}"}
        )


@router.post("/api/player/skill/{skill_name}")
async def add_skill(skill_name: str):
    try:
        player = player_service.add_skill(skill_name)
        if not player:
            return JSONResponse(status_code=404, content={"error": "角色或技能不存在"})
        return JSONResponse(content={"success": True, "player": player.model_dump()})
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"error": f"添加技能失败: {str(e)}"}
        )


@router.delete("/api/player/skill/{skill_name}")
async def remove_skill(skill_name: str):
    try:
        player = player_service.remove_skill(skill_name)
        if not player:
            return JSONResponse(status_code=404, content={"error": "角色不存在"})
        return JSONResponse(content={"success": True, "player": player.model_dump()})
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"error": f"移除技能失败: {str(e)}"}
        )


@router.post("/api/player/hp")
async def update_hp(delta: int):
    try:
        player = player_service.update_hp(delta)
        if not player:
            return JSONResponse(status_code=404, content={"error": "角色不存在"})
        return JSONResponse(content={"success": True, "player": player.model_dump()})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"更新HP失败: {str(e)}"})


@router.delete("/api/player")
async def delete_player():
    try:
        if delete_player_file():
            return JSONResponse(content={"success": True})
        return JSONResponse(status_code=404, content={"error": "玩家角色不存在"})
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"error": f"删除角色失败: {str(e)}"}
        )
