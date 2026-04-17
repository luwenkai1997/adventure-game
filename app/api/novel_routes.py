from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.container import container


router = APIRouter()


class ChapterRequest(BaseModel):
    novel_folder: str
    chapter_num: int
    chapter_title: str
    chapter_summary: str = ""
    ending_type: str = ""


class IncrementalRequest(BaseModel):
    ending_type: str = ""
    custom_description: str = ""
    current_round: int = 0


@router.post("/api/novel/incremental")
async def generate_incremental(
    request: Request, body: IncrementalRequest = IncrementalRequest()
):
    try:
        ctx = container.context_resolver.resolve_required(request)
        result = await container.novel_service.generate_incremental(
            ctx,
            ending_type=body.ending_type,
            custom_description=body.custom_description,
            current_round=body.current_round,
        )
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"生成小说失败: {str(e)}"})


@router.get("/api/novel/progress")
async def get_novel_progress(request: Request, current_round: int = 0):
    try:
        ctx = container.context_resolver.resolve_required(request)
        result = container.novel_service.get_novel_progress(ctx, current_round=current_round)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"获取进度失败: {str(e)}"})


@router.delete("/api/novel/reset")
async def reset_novel(request: Request):
    """Delete the current novel directory so the next generate starts fresh."""
    try:
        ctx = container.context_resolver.resolve_required(request)
        result = container.novel_service.reset_novel(ctx)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"error": f"重置小说失败: {str(e)}"}
        )


@router.get("/api/novel/content")
async def get_novel_content(request: Request):
    try:
        ctx = container.context_resolver.resolve_required(request)
        result = container.novel_service.get_novel_content(ctx)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"获取小说失败: {str(e)}"})


@router.post("/api/generate-novel")
async def generate_novel(request: Request):
    try:
        ctx = container.context_resolver.resolve_required(request)
        result = await container.novel_service.generate_full_novel(ctx)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"服务器错误: {str(e)}"})


@router.post("/api/novel/plan")
async def plan_novel(request: Request):
    try:
        ctx = container.context_resolver.resolve_required(request)
        result = await container.novel_service.plan_novel(ctx)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"规划小说失败: {str(e)}"})


@router.post("/api/novel/chapter")
async def generate_chapter(request: Request, body: ChapterRequest):
    try:
        ctx = container.context_resolver.resolve_required(request)
        result = await container.novel_service.generate_chapter(
            ctx,
            body.novel_folder,
            body.chapter_num,
            body.chapter_title,
            body.chapter_summary,
            body.ending_type,
        )
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"生成章节失败: {str(e)}"})


@router.post("/api/novel/merge")
async def merge_novel(request: Request, novel_folder: str = Query(...)):
    try:
        ctx = container.context_resolver.resolve_required(request)
        result = container.novel_service.merge_novel(ctx, novel_folder)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"合并小说失败: {str(e)}"})


@router.get("/api/novel/status/{novel_folder}")
async def get_novel_status(request: Request, novel_folder: str):
    try:
        ctx = container.context_resolver.resolve_required(request)
        result = container.novel_service.get_novel_status(ctx, novel_folder)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"获取状态失败: {str(e)}"})
