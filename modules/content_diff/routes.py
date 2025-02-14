from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/")
async def index(request: Request):
    """代码比较器主页"""
    return templates.TemplateResponse(
        "tools/content-diff/index.html",
        {
            "request": request,
            "current_tool": "/tools/content-diff",
            "year": datetime.now().year
        }
    ) 