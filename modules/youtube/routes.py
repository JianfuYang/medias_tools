from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks, Form
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc
from .models import Video, BatchVideo
from .services import download_video, batch_download, get_batch_progress, get_progress
from core.database import get_db, get_batch_db
import logging
from datetime import datetime, timedelta
import os
import json
import urllib.parse

router = APIRouter()
logger = logging.getLogger(__name__)

# 配置模板
templates = Jinja2Templates(directory="templates")

@router.get("/")
async def youtube_index(request: Request, db: Session = Depends(get_db)):
    """YouTube下载器首页"""
    logger.info("访问YouTube下载器")
    
    today = datetime.now()
    dates = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
    
    videos = db.query(Video).all()
    
    videos_by_date = {}
    for date in dates:
        videos_by_date[date] = []
    
    for video in videos:
        logger.info(f"视频文件路径: {video.file_path}")
        logger.info(f"视频文件路径: {video.thumbnail_path}")
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
            "year": datetime.now().year
        }
    )

@router.get("/batch")
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
                # logger.info(f"batch视频文件路径: {video.file_path}")
                date_str = video.file_path.split('/')[3]  # toolsfile/youtube/batch_videos/2025-01-10/user/video.mp4
                
                # 初始化日期分组
                if date_str not in videos_by_date:
                    videos_by_date[date_str] = {}
                
                # 使用channel_id作为用户分组
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

@router.post("/download")
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

@router.get("/progress/{video_id}")
async def get_download_progress(video_id: str):
    """获取下载进度"""
    return get_progress(video_id)

@router.get("/history")
async def history_page(request: Request, db: Session = Depends(get_db)):
    """下载历史页面"""
    try:
        # 获取最近一周的下载记录
        videos = db.query(Video).order_by(desc(Video.id)).all()
        
        return templates.TemplateResponse(
            "tools/youtube/history.html",
            {
                "request": request,
                "videos": videos,
                "year": datetime.now().year
            }
        )
    except Exception as e:
        logger.error(f"获取历史记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/batch/progress/{channel_id}")
async def check_batch_progress(channel_id: str, db: Session = Depends(get_batch_db)):
    """检查批量下载进度"""
    try:
        # 解码channel_id
        decoded_channel_id = channel_id
        try:
            decoded_channel_id = urllib.parse.unquote(channel_id)
        except Exception as e:
            logger.warning(f"解码channel_id失败: {str(e)}")
        
        logger.info(f"检查进度 - channel_id: {decoded_channel_id}")
        
        # 查找最新的下载记录
        video = db.query(BatchVideo)\
            .filter(BatchVideo.channel_id == decoded_channel_id)\
            .order_by(BatchVideo.id.desc())\
            .first()
            
        if not video:
            return {
                "status": "error",
                "error_message": "未找到下载记录"
            }
            
        return {
            "status": video.status,
            "error_message": video.error_message if video.status == 'error' else None,
            "total_videos": video.total_videos if hasattr(video, 'total_videos') else 0,
            "downloaded_videos": video.downloaded_videos if hasattr(video, 'downloaded_videos') else 0
        }
        
    except Exception as e:
        logger.error(f"检查进度失败: {str(e)}")
        return {
            "status": "error",
            "error_message": f"检查进度失败: {str(e)}"
        }

@router.post("/batch/download")
async def start_batch_download(
    request: Request, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_batch_db)
):
    """开始批量下载"""
    try:
        data = await request.json()
        url = data.get('urls', '')
        
        # 提取channel_id
        channel_id = url
        if '@' in url:
            channel_id = url.split('@')[-1].split('/')[0]
        elif '/channel/' in url:
            channel_id = url.split('/channel/')[-1].split('/')[0]
        elif '/c/' in url:
            channel_id = url.split('/c/')[-1].split('/')[0]
        elif '/user/' in url:
            channel_id = url.split('/user/')[-1].split('/')[0]
            
        logger.info(f"开始批量下载 - URL: {url}, channel_id: {channel_id}")
        
        # 创建初始下载记录
        video = BatchVideo(
            channel_id=channel_id,
            status='downloading',
            youtube_url=url,
            download_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        db.add(video)
        db.commit()
        
        # 启动后台下载任务
        background_tasks.add_task(batch_download, [url], db)
        
        return {"message": "批量下载任务已启动"}
        
    except Exception as e:
        logger.error(f"启动批量下载失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 其他路由... 