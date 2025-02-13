from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/")
async def format_page(request: Request):
    """图片格式转换页面"""
    return templates.TemplateResponse(
        "tools/image-format/convert.html",
        {
            "request": request,
            "current_tool": "tools/image-format",
            "year": datetime.now().year
        }
    ) 