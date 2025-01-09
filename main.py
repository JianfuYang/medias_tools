import os
import shutil
import subprocess
from fastapi import FastAPI, Request, Depends, BackgroundTasks, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import yt_dlp
from database import get_db, Video
import asyncio
import logging
from datetime import datetime, timedelta
import uvicorn
import json

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

app = FastAPI()

# 创建必要的目录
os.makedirs("static", exist_ok=True)
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/thumbnails", exist_ok=True)
os.makedirs("videos", exist_ok=True)

# 挂载静态文件和模板
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/videos", StaticFiles(directory="videos"), name="videos")
templates = Jinja2Templates(directory="templates")

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
    folder_path = f"videos/{today}"
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

@app.get("/")
async def home(request: Request, db: Session = Depends(get_db)):
    """主页"""
    logger.info("访问主页")
    
    # 获取最近一周的日期范围
    today = datetime.now()
    dates = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
    
    # 获取所有视频
    videos = db.query(Video).all()
    
    # 按日期分组视频
    videos_by_date = {}
    for date in dates:
        videos_by_date[date] = []
    
    for video in videos:
        # 从文件路径中提取日期
        video_date = '/'.join(video.file_path.split('/')[1:2])  # videos/2024-01-09/xxx.mp4 -> 2024-01-09
        if video_date in dates:  # 只保留最近一周的视频
            videos_by_date[video_date].append(video)
    
    # 移除空的日期组
    videos_by_date = {k: v for k, v in videos_by_date.items() if v}
    
    # 创建一个简化的日期字典用于JavaScript
    dates_for_js = {date: True for date in videos_by_date.keys()}
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request, 
            "videos_by_date": videos_by_date,
            "dates_for_js": json.dumps(dates_for_js),  # 预先序列化为JSON字符串
            "today": today.strftime('%Y-%m-%d')
        }
    )

@app.post("/download")
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

@app.get("/progress/{video_id}")
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

@app.get("/batch")
async def batch_page(request: Request):
    """批量下载页面"""
    return templates.TemplateResponse("batch.html", {"request": request})

@app.get("/history")
async def history_page(request: Request):
    """下载历史页面"""
    return templates.TemplateResponse("history.html", {
        "request": request,
        "message": "下载历史功能即将推出！"
    })

@app.get("/settings")
async def settings_page(request: Request):
    """设置页面"""
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "message": "设置功能即将推出！"
    })

if __name__ == "__main__":
    # 设置调试配置
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,  # 启用热重载
        log_level="debug",  # 设置日志级别
        access_log=True  # 显示访问日志
    ) 