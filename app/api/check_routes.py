from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.models.check import CheckRequest, get_difficulty_name, get_difficulty_color
from app.services.check_service import CheckService


router = APIRouter()
check_service = CheckService()


@router.post("/api/check")
async def perform_check(request: CheckRequest):
    try:
        result = check_service.perform_check(request)
        return JSONResponse(content={"success": True, "result": result.model_dump()})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"检定失败: {str(e)}"})


@router.get("/api/check/info")
async def get_check_info():
    try:
        info = check_service.get_player_check_info()
        return JSONResponse(content={"success": True, "info": info})
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"error": f"获取检定信息失败: {str(e)}"}
        )


@router.get("/api/check/difficulty/{dc}")
async def get_difficulty_info(dc: int):
    return JSONResponse(
        content={
            "dc": dc,
            "name": get_difficulty_name(dc),
            "color": get_difficulty_color(dc),
        }
    )


@router.get("/api/check/roll")
async def roll_dice(dice: str = "d20"):
    try:
        import random

        if dice.lower() == "d20":
            result = random.randint(1, 20)
        elif dice.lower() == "d12":
            result = random.randint(1, 12)
        elif dice.lower() == "d10":
            result = random.randint(1, 10)
        elif dice.lower() == "d8":
            result = random.randint(1, 8)
        elif dice.lower() == "d6":
            result = random.randint(1, 6)
        elif dice.lower() == "d4":
            result = random.randint(1, 4)
        elif dice.lower() == "d100":
            result = random.randint(1, 100)
        else:
            result = random.randint(1, 20)

        return JSONResponse(content={"dice": dice, "result": result})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"掷骰失败: {str(e)}"})
