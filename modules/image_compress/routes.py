from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from fastapi.templating import Jinja2Templates
from .services import compress_image_service
from datetime import datetime
import logging

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# 图片压缩页面路由
@router.get("/")
async def image_compress_page(request: Request):
    logger.info("访问图片压缩页面")
    return templates.TemplateResponse(
        "tools/image-compress/compress.html",
        {
            "request": request,
            "current_tool": "/tools/image-compress/compress",
            "year": datetime.now().year
        }
    )

# 图片压缩API
@router.post("/compress")
async def compress_image(
    file: UploadFile = File(...),
    quality: int = Form(80),
    max_width: int = Form(None),
    keep_exif: bool = Form(False)
):
    logger.info(f"开始处理图片压缩请求: {file.filename}")
    try:
        result = await compress_image_service(file, quality, max_width, keep_exif)
        logger.info(f"图片压缩成功: {file.filename}, 压缩率: {result['reduction']}%")
        return result
    except Exception as e:
        error_msg = str(e)
        logger.error(f"图片压缩失败: {file.filename}, 错误: {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg) 