from http.client import HTTPException
import os
import shutil
import subprocess
from fastapi import FastAPI, Request, Depends, BackgroundTasks, Form, WebSocket
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
import yt_dlp
from database import get_db, get_batch_db, Video, BatchVideo
import asyncio
import logging
from datetime import datetime, timedelta
import uvicorn
import json
from batch_downloader import start_batch_download, get_batch_progress, batch_progress, router as batch_router
from sqlalchemy import desc
from itertools import groupby
from operator import attrgetter
import urllib.parse
from typing import List

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

# 检查ffmpeg是否安装
def check_ffmpeg():
    try:
        import subprocess
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except Exception:
        logger.warning("ffmpeg未安装，某些功能可能受限")
        return False

app = FastAPI(title="媒体效率工具库")

# 创建必要的目录
os.makedirs("static", exist_ok=True)
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/thumbnails", exist_ok=True)
os.makedirs("toolsfile/youtube/videos", exist_ok=True)
os.makedirs("toolsfile/youtube/batch_videos", exist_ok=True)  # 添加批量下载目录

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/toolsfile/youtube/videos", StaticFiles(directory="toolsfile/youtube/videos"), name="videos")
app.mount("/toolsfile/youtube/batch_videos", StaticFiles(directory="toolsfile/youtube/batch_videos"), name="batch_videos")

# 配置模板
templates = Jinja2Templates(directory="templates")

# 添加模板上下文处理器
@app.middleware("http")
async def add_template_context(request: Request, call_next):
    response = await call_next(request)
    return response

# 存储下载进度
download_progress = {}

# 检查ffmpeg
HAS_FFMPEG = check_ffmpeg()

def progress_hook(d):
    # logger.info(f"下载进度回调: {d}")
    """下载进度回调"""
    try:
        if d['status'] == 'downloading':
            video_id = d.get('info_dict', {}).get('id', 'unknown')
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
            
            if total > 0:
                percentage = (downloaded / total) * 100
                download_progress[video_id] = round(percentage, 1)
                logger.debug(f"下载进度 - video_id: {video_id}, progress: {percentage}%")
        elif d['status'] == 'finished':
            video_id = d.get('info_dict', {}).get('id', 'unknown')
            download_progress[video_id] = 100
            logger.info(f"视频 {video_id} 下载完成")
        elif d['status'] == 'error':
            logger.error(f"下载出错: {d.get('error')}")
    except Exception as e:
        logger.error(f"进度处理错误: {str(e)}")

def extract_thumbnail(video_path: str, output_path: str) -> bool:
    """从视频中提取缩略图"""
    try:
        subprocess.run([
            'ffmpeg',
            '-i', video_path,
            '-ss', '00:00:01',  # 从1秒处开始
            '-vframes', '1',    # 只提取1帧
            '-vf', 'scale=640:-1',  # 设置宽度为640，高度自适应
            '-y',
            output_path
        ], check=True, capture_output=True)
        return True
    except Exception as e:
        logger.error(f"提取缩略图失败: {str(e)}")
        return False

def convert_thumbnail(input_path: str, output_path: str) -> bool:
    """转换缩略图格式"""
    try:
        subprocess.run([
            'ffmpeg',
            '-i', input_path,
            '-vf', 'scale=640:-1',  # 统一缩略图尺寸
            '-y',
            output_path
        ], check=True, capture_output=True)
        return True
    except Exception as e:
        logger.error(f"转换缩略图失败: {str(e)}")
        return False

def get_date_folder():
    """获取当前日期的文件夹路径"""
    today = datetime.now().strftime('%Y-%m-%d')
    folder_path = f"toolsfile/youtube/videos/{today}"
    os.makedirs(folder_path, exist_ok=True)
    return folder_path

def get_media_paths(video_id: str, date_folder: str):
    """获取媒体文件路径"""
    return {
        'video': f"{date_folder}/{video_id}.mp4",
        'audio': f"{date_folder}/{video_id}.m4a",
        'thumbnail': f"{date_folder}/thumbnails/{video_id}.jpg",
        'info': f"{date_folder}/{video_id}.info.json"
    }

async def download_video(url: str, db: Session):
    """后台下载视频"""
    try:
        logger.info(f"开始下载视频: {url}")
        
        # 创建日期文件夹
        date_folder = get_date_folder()
        os.makedirs(f"{date_folder}/thumbnails", exist_ok=True)
        
        # yt-dlp基础配置
        ydl_opts = {
            'format': 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'merge_output_format': 'mp4',
            'outtmpl': f'{date_folder}/%(id)s.%(ext)s',
            'progress_hooks': [progress_hook],
            'quiet': False,
            'no_warnings': False,
            'ignoreerrors': True,
            'writethumbnail': True,
            'writeinfojson': True,
            'retries': 10,
            'fragment_retries': 10,
            'skip_unavailable_fragments': True,
            'force_generic_extractor': False,
            'sleep_interval': 3,
            'max_sleep_interval': 6,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate',
            },
            'nocheckcertificate': True,
            'outtmpl_thumbnail': f'{date_folder}/thumbnails/%(id)s.%(ext)s',
            'keepvideo': True,
            'postprocessors': [
                {
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                },
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'm4a',
                    'preferredquality': '192',
                }
            ],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # 获取视频信息
                logger.info("正在获取视频信息...")
                info = ydl.extract_info(url, download=False)
                if info is None:
                    raise Exception("无法获取视频信息")
                
                video_id = info['id']
                logger.debug(f"视频信息: {info.get('title', 'Unknown Title')}")
                
                # 获取所有相关文件路径
                paths = get_media_paths(video_id, date_folder)
                
                # 重置进度
                download_progress[video_id] = 10
                
                # 下载视频
                logger.info("开始下载文件...")
                result = ydl.download([url])
                if result != 0:
                    raise Exception("下载失败，返回码非0")
                logger.info("文件下载完成")
                
                # 检查文件是否存在并获取实际文件大小
                if not os.path.exists(paths['video']):
                    raise Exception("下载完成但找不到视频文件")
                
                # 计算实际文件大小
                actual_size = os.path.getsize(paths['video']) / (1024 * 1024)  # 转换为MB
                logger.info(f"计算文件大小: {actual_size}MB")
                
                # 准备视频信息
                video = Video(
                    title=info.get('title', f'视频 {video_id}'),
                    author=info.get('uploader', '未知作者'),
                    duration=info.get('duration', 0),
                    description=info.get('description', '无描述'),
                    youtube_url=url,
                    file_path=paths['video'],
                    audio_path=paths['audio'],
                    thumbnail_path=paths['thumbnail'],
                    file_size=round(actual_size, 2)
                )
                
                # 处理缩略图
                if os.path.exists(paths['thumbnail']):
                    logger.info(f"缩略图已存在: {paths['thumbnail']}")
                else:
                    logger.info("从视频中提取缩略图...")
                    extract_thumbnail(paths['video'], paths['thumbnail'])
                
                # 保存到数据库
                db.add(video)
                db.commit()
                db.refresh(video)
                logger.info(f"视频信息已保存到数据库，文件大小: {video.file_size}MB")
                
                # 设置进度为100%
                download_progress[video_id] = 100
                    
            except yt_dlp.utils.DownloadError as e:
                logger.error(f"yt-dlp下载错误: {str(e)}")
                if "Requested format is not available" in str(e):
                    raise Exception("请求的视频格式不可用，可能是YouTube限制或视频不支持下载")
                elif "Signature extraction failed" in str(e):
                    raise Exception("签名验证失败，可能需要更新yt-dlp")
                else:
                    raise Exception(f"视频下载失败: {str(e)}")
            except Exception as e:
                logger.error(f"处理视频时出错: {str(e)}")
                raise
                
    except Exception as e:
        error_msg = str(e)
        logger.error(f"下载失败: {error_msg}")
        raise Exception(f"下载失败: {error_msg}")
    finally:
        # 清理进度信息
        if 'video_id' in locals():
            if video_id in download_progress:
                del download_progress[video_id]

# 定义工具配置
TOOLS_CONFIG = {
    'ai-image': {
        'name': 'AI文生图',
        'features': [
            {
                'title': '智能生成',
                'desc': '通过文字描述智能生成高质量图像，支持多种风格和场景'
            },
            {
                'title': '风格调整',
                'desc': '提供丰富的风格预设和参数调整，实现个性化创作'
            },
            {
                'title': '批量导出',
                'desc': '支持批量生成和导出，满足批量创作需求'
            }
        ],
        'progress': 35
    },
    'text-card': {
        'name': '文字卡片生成',
        'features': [
            {
                'title': '模板选择',
                'desc': '提供多种精美模板，一键生成精美文字卡片'
            },
            {
                'title': '自定义样式',
                'desc': '支持自定义字体、颜色、布局等样式'
            },
            {
                'title': '批量生成',
                'desc': '支持批量生成多张卡片，提高效率'
            }
        ],
        'progress': 20
    },
    'image-compress': {
        'name': '图片压缩',
        'features': [
            {
                'title': '智能压缩',
                'desc': '自动分析图片特征，选择最佳压缩方案'
            },
            {
                'title': '批量处理',
                'desc': '支持多图片同时压缩，提高工作效率'
            },
            {
                'title': '质量控制',
                'desc': '可调节压缩质量，平衡大小和画质'
            }
        ],
        'progress': 15
    },
    'resize': {
        'name': '调整大小',
        'features': [
            {
                'title': '精确调整',
                'desc': '支持像素级精确调整图片尺寸'
            },
            {
                'title': '等比缩放',
                'desc': '智能保持图片比例，避免变形'
            },
            {
                'title': '批量处理',
                'desc': '一次性调整多张图片尺寸'
            }
        ],
        'progress': 10
    },
    'convert': {
        'name': '格式转换',
        'features': [
            {
                'title': '多格式支持',
                'desc': '支持常见图片格式间的相互转换'
            },
            {
                'title': '参数调整',
                'desc': '可设置转换参数，优化输出效果'
            },
            {
                'title': '批量转换',
                'desc': '支持批量转换不同格式图片'
            }
        ],
        'progress': 25
    },
    'svg-editor': {
        'name': 'SVG编辑器',
        'features': [
            {
                'title': '可视化编辑',
                'desc': '直观的界面操作，轻松编辑SVG'
            },
            {
                'title': '代码同步',
                'desc': '实时预览代码变化，支持手动编辑'
            },
            {
                'title': '组件库',
                'desc': '提供常用SVG组件，快速创建图形'
            }
        ],
        'progress': 30
    },
    'svg-to-ppt': {
        'name': 'SVG to PPT',
        'features': [
            {
                'title': '一键转换',
                'desc': '将SVG快速转换为PPT可编辑元素'
            },
            {
                'title': '样式保持',
                'desc': '完整保留SVG样式和动画效果'
            },
            {
                'title': '批量导入',
                'desc': '支持批量SVG导入PPT模板'
            }
        ],
        'progress': 40
    },
    'logo-design': {
        'name': '极简Logo设计',
        'features': [
            {
                'title': '模板系统',
                'desc': '提供专业Logo模板，快速设计'
            },
            {
                'title': '个性定制',
                'desc': '支持颜色、字体、布局等深度定制'
            },
            {
                'title': '多格式导出',
                'desc': '支持多种格式导出，满足不同需求'
            }
        ],
        'progress': 20
    }
}

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

# YouTube下载器路由
@app.get("/tools/youtube", name="youtube")
async def youtube_page(request: Request, db: Session = Depends(get_db)):
    logger.info("访问YouTube下载器")
    
    today = datetime.now()
    dates = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
    
    videos = db.query(Video).all()
    
    videos_by_date = {}
    for date in dates:
        videos_by_date[date] = []
    
    for video in videos:
        logger.info(f"视频文件路径: {video.file_path}")
        video_date = '/'.join(video.file_path.split('/')[3:4])
        if video_date in dates:
            videos_by_date[video_date].append(video)
    
    videos_by_date = {k: v for k, v in videos_by_date.items() if v}
    dates_for_js = {date: True for date in videos_by_date.keys()}
    
    return templates.TemplateResponse(
        "tools/youtube/youtube_index.html",
        {
            "request": request,
            "current_tool": "/tools/youtube",
            "videos_by_date": videos_by_date,
            "dates_for_js": json.dumps(dates_for_js),
            "today": today.strftime('%Y-%m-%d'),
            "year": datetime.now().year  # 添加年份变量用于页脚
        }
    )

# 工具页面路由
@app.get("/tools/{tool_name}")
async def tool_page(request: Request, tool_name: str):
    if tool_name not in TOOLS_CONFIG:
        return templates.TemplateResponse(
            "common/404.html",
            {
                "request": request,
                "current_tool": None
            },
            status_code=404
        )
    
    tool_config = TOOLS_CONFIG[tool_name]
    tool_path = f"/tools/{tool_name}"
    
    # 获取当前年份
    current_year = datetime.now().year
    
    # 返回模板，并传递year参数
    return templates.TemplateResponse(
        "common/developing.html",
        {
            "request": request,
            "current_tool": tool_path,
            "tool_name": tool_config["name"],
            "features": tool_config["features"],
            "progress": tool_config["progress"],
            "year": current_year  # 添加year参数
        }
    )

# AI文生图路由
@app.get("/tools/ai-image", name="ai_image")
async def ai_image(request: Request):
    tool_config = TOOLS_CONFIG['ai-image']
    return templates.TemplateResponse(
        "common/developing.html",
        {
            "request": request,
            "current_tool": "/tools/ai-image",
            "tool_name": tool_config["name"],
            "features": tool_config["features"],
            "progress": tool_config["progress"]
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

@app.post("/tools/youtube/download")
async def start_download(url: str = Form(...), background_tasks: BackgroundTasks = None, db: Session = Depends(get_db)):
    """开始下载视频"""
    try:
        logger.info(f"收到下载请求: {url}")
        background_tasks.add_task(download_video, url, db)
        return {"message": "开始下载"}
    except Exception as e:
        logger.error(f"下载请求失败: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={"message": f"下载失败: {str(e)}"}
        )

@app.get("/tools/youtube/progress/{video_id}")
async def get_progress(video_id: str):
    """获取下载进度"""
    if video_id in download_progress:
        # 存在则说明还没下载完成或失败
        progress = download_progress.get(video_id, 0)
    else:
        # 不存在则说明下载完成
        progress = 100
    logger.info(f"进度查询 - 视频ID: {video_id}, 进度: {progress}%")
    return {"progress": progress} 

@app.get("/tools/youtube/batch")
async def batch_page(request: Request, db: Session = Depends(get_batch_db)):
    """批量下载页面"""
    try:
        # 获取所有视频记录
        videos = db.query(BatchVideo).all()
        
        # 按日期和用户分组的视频字典
        videos_by_date = {}
        
        for video in videos:
            try:
                # 从文件路径中提取日期
                logger.info(f"batch视频文件路径: {video.file_path}")
                date_str = video.file_path.split('/')[3]  # toolsfile/youtube/batch_videos/2025-01-10/user/video.mp4
                
                # 初始化日期分组
                if date_str not in videos_by_date:
                    videos_by_date[date_str] = {}
                
                # 使用channel_id作为用户分组（确保以@开头）
                username = video.channel_id
                
                if username not in videos_by_date[date_str]:
                    videos_by_date[date_str][username] = []
                
                # 构建文件路径 - 参考单视频下载功能的路径结构
                file_path = video.file_path
                if file_path and not file_path.startswith('/toolsfile'):
                    file_path = f"/toolsfile/youtube/batch_videos/{date_str}/{username}/{os.path.basename(file_path)}"
                
                audio_path = video.audio_path
                if audio_path and not audio_path.startswith('/toolsfile'):
                    audio_path = f"/toolsfile/youtube/batch_videos/{date_str}/{username}/{os.path.basename(audio_path)}"
                
                thumbnail_path = video.thumbnail_path
                if thumbnail_path and not thumbnail_path.startswith('/toolsfile'):
                    thumbnail_path = f"/toolsfile/youtube/batch_videos/{date_str}/{username}/{os.path.basename(thumbnail_path)}"
                
                # 添加视频信息
                video_info = {
                    'id': video.id,
                    'title': video.title,
                    'youtube_url': video.youtube_url,
                    'file_path': file_path,
                    'audio_path': audio_path,
                    'thumbnail_path': thumbnail_path,
                    'duration': video.duration,
                    'file_size': video.file_size,
                    'author': username,
                    'upload_time': video.upload_time,
                    'description': video.description,
                    'status': video.status,
                    'error_message': video.error_message
                }
                videos_by_date[date_str][username].append(video_info)
                
            except Exception as e:
                logger.error(f"处理视频记录时出错: {str(e)}")
                continue
        
        # 对日期进行排序（降序）
        sorted_dates = sorted(videos_by_date.keys(), reverse=True)
        
        # 构建排序后的数据结构
        sorted_videos = {}
        for date_str in sorted_dates:
            sorted_videos[date_str] = {}
            # 对每个日期下的用户进行排序
            sorted_authors = sorted(videos_by_date[date_str].keys())
            for author in sorted_authors:
                # 对每个用户的视频按上传时间排序（如果有）
                sorted_videos[date_str][author] = sorted(
                    videos_by_date[date_str][author],
                    key=lambda x: x.get('upload_time', ''),
                    reverse=True
                )
        
        return templates.TemplateResponse(
            "tools/youtube/batch.html",
            {
                "request": request,
                "videos_by_date": sorted_videos,
                "year": datetime.now().year
            }
        )
    except Exception as e:
        logger.error(f"获取批量下载页面失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/youtube/batch/download")
async def start_batch(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_batch_db)
):
    """开始批量下载"""
    try:
        data = await request.json()
        channel_url = data.get('channel_url')
        channel_url = urllib.parse.unquote(channel_url)
        
        if not channel_url:
            return JSONResponse(
                status_code=400,
                content={"message": "请提供YouTube用户主页链接"}
            )
        
        # 启动批量下载任务
        background_tasks.add_task(start_batch_download, channel_url, db)
        return {"message": "开始批量下载"}
        
    except Exception as e:
        logger.error(f"批量下载请求失败: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={"message": f"批量下载失败: {str(e)}"}
        )

@app.get("/tools/youtube/batch/progress/{channel_id}")
async def get_batch_progress_route(channel_id: str):
    """获取批量下载进度"""
    try:
        # 从数据库获取该频道的所有视频
        db = next(get_batch_db())
        total_videos = db.query(BatchVideo).filter(BatchVideo.channel_id == channel_id).count()
        completed_videos = db.query(BatchVideo).filter(
            BatchVideo.channel_id == channel_id,
            BatchVideo.status == 'completed'
        ).count()

        # 获取当前正在下载的视频进度
        current_progress = await get_batch_progress(channel_id)

        return {
            'total_videos': total_videos,
            'downloaded_videos': completed_videos,
            'videos': current_progress
        }
    except Exception as e:
        logger.error(f"获取下载进度失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tools/youtube/history")
async def history_page(request: Request):
    """下载历史页面"""
    return templates.TemplateResponse("tools/youtube/history.html", {
        "request": request,
        "message": "下载历史功能即将推出！"
    })

@app.get("/tools/youtube/settings")
async def settings_page(request: Request):
    """设置页面"""
    return templates.TemplateResponse("tools/youtube/settings.html", {
        "request": request,
        "message": "设置功能即将推出！"
    })

@app.get("/tools/developing")
async def developing(request: Request):
    """开发中页面"""
    return templates.TemplateResponse("common/developing.html", {
        "request": request,
        "message": "该功能正在开发中，敬请期待！"
    })

# 注册batch_downloader的路由器
app.include_router(batch_router)

# 工具路由生成器
def create_tool_route(tool_id: str):
    async def route_handler(request: Request):
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
    return route_handler

# 注册所有工具路由
for tool_id in TOOLS_CONFIG.keys():
    if tool_id != 'youtube':  # 跳过YouTube下载器，因为它有专门的路由处理
        app.add_route(f"/tools/{tool_id}", create_tool_route(tool_id), methods=["GET"], name=tool_id)

if __name__ == "__main__":
    # 设置调试配置
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 启用热重载
        log_level="debug",  # 设置日志级别
        access_log=True  # 显示访问日志
    ) 