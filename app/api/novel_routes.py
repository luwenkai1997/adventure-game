from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.services.novel_service import NovelService


router = APIRouter()
novel_service = NovelService()


class ChapterRequest(BaseModel):
    novel_folder: str
    chapter_num: int
    chapter_title: str
    chapter_summary: str
    ending_type: str = ""


@router.post("/api/generate-novel")
async def generate_novel():
    try:
        result = await novel_service.generate_full_novel()
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': f'服务器错误: {str(e)}'})


@router.post("/api/novel/plan")
async def plan_novel():
    try:
        result = await novel_service.plan_novel()
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': f'规划小说失败: {str(e)}'})


@router.post("/api/novel/chapter")
async def generate_chapter(request: ChapterRequest):
    try:
        result = await novel_service.generate_chapter(
            request.novel_folder,
            request.chapter_num,
            request.chapter_title,
            request.chapter_summary,
            request.ending_type
        )
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': f'生成章节失败: {str(e)}'})


@router.post("/api/novel/merge")
async def merge_novel(novel_folder: str = Query(...)):
    try:
        result = novel_service.merge_novel(novel_folder)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': f'合并小说失败: {str(e)}'})


@router.get("/api/novel/status/{novel_folder}")
async def get_novel_status(novel_folder: str):
    try:
        result = novel_service.get_novel_status(novel_folder)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': f'获取状态失败: {str(e)}'})
