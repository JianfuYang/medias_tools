from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from modules.youtube.routes import router as youtube_router
from modules.youtube.services import check_ffmpeg
from config.settings import VIDEOS_DIR, BATCH_VIDEOS_DIR, STATIC_DIR
from config.tools import TOOLS_CONFIG
import logging
from datetime import datetime
import os
import uvicorn
from modules.chatgpt.routes import router as chatgpt_router
from core.database import init_db
from PIL import Image
import io
import base64
from modules.image_compress.routes import router as image_compress_router

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('youtube_downloader.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 检查ffmpeg
HAS_FFMPEG = check_ffmpeg()

app = FastAPI(title="媒体效率工具库")

# 创建必要的目录
for dir_path in [STATIC_DIR, "static/css", "static/thumbnails", VIDEOS_DIR, BATCH_VIDEOS_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# 挂载静态文件
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/toolsfile/youtube/videos", StaticFiles(directory=VIDEOS_DIR), name="videos")
app.mount("/toolsfile/youtube/batch_videos", StaticFiles(directory=BATCH_VIDEOS_DIR), name="batch_videos")

# 配置模板
templates = Jinja2Templates(directory="templates")

# 初始化数据库
init_db()

# 首页路由
@app.get("/", name="index")
async def index(request: Request):
    return templates.TemplateResponse(
        "home/index.html",
        {
            "request": request,
            "current_tool": "/",
            "year": datetime.now().year
        }
    )

# 注册YouTube模块路由
app.include_router(youtube_router, prefix="/tools/youtube", tags=["youtube"])
app.include_router(chatgpt_router, prefix="/tools/chatgpt", tags=["chatgpt"])

# 注册图片压缩模块路由
app.include_router(
    image_compress_router, 
    prefix="/tools/image-compress",
    tags=["image_compress"]
)

# 工具路由 - 处理其他工具的待开发页面
@app.get("/tools/{tool_id}")
async def tool_page(request: Request, tool_id: str):
    """通用工具页面路由"""
    # 检查工具是否存在
    if tool_id not in TOOLS_CONFIG:
        return templates.TemplateResponse(
            "common/404.html",
            {"request": request, "current_tool": None},
            status_code=404
        )
    
    # 如果是YouTube下载器或ChatGPT助手，重定向到专门的路由
    if tool_id in ['youtube', 'chatgpt']:
        return RedirectResponse(url=f"/tools/{tool_id}/")
    
    # 其他工具显示开发中页面
    tool_config = TOOLS_CONFIG[tool_id]
    return templates.TemplateResponse(
        "common/developing.html",
        {
            "request": request,
            "current_tool": f"/tools/{tool_id}",
            "tool_name": tool_config["name"],
            "features": tool_config["features"],
            "progress": tool_config["progress"],
            "year": datetime.now().year
        }
    )

# 404错误处理
@app.exception_handler(404)
async def not_found(request: Request, exc):
    return templates.TemplateResponse(
        "common/404.html",
        {
            "request": request,
            "current_tool": None
        },
        status_code=404
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug",
        access_log=True
    )