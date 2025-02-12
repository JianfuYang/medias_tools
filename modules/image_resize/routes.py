from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/")
async def resize_page(request: Request):
    """图片调整大小页面"""
    return templates.TemplateResponse(
        "tools/image-resize/resize.html",
        {
            "request": request,
            "current_tool": "/tools/image-resize",
            "year": datetime.now().year
        }
    ) 