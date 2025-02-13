from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/")
async def text_card_page(request: Request):
    """文字卡片生成器页面"""
    return templates.TemplateResponse(
        "tools/text-card/generator.html",
        {
            "request": request,
            "current_tool": "tools/text-card",
            "year": datetime.now().year
        }
    ) 