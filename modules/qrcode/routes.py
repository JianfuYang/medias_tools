from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/")
async def qrcode_page(request: Request):
    """二维码生成器页面"""
    return templates.TemplateResponse(
        "tools/qrcode/generator.html",
        {
            "request": request,
            "current_tool": "/tools/qrcode",
            "year": datetime.now().year
        }
    ) 