from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/")
async def svg_editor_page(request: Request):
    """SVG编辑器页面"""
    return templates.TemplateResponse(
        "tools/svg-editor/editor.html",
        {
            "request": request,
            "current_tool": "tools/svg-editor",
            "year": datetime.now().year
        }
    ) 