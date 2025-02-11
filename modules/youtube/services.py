import yt_dlp
from .models import Video, BatchVideo
import os
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from config.settings import VIDEOS_DIR, BATCH_VIDEOS_DIR

logger = logging.getLogger(__name__)

# 下载配置
ydl_opts = {
    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    'writethumbnail': True,
    'writeinfojson': True,
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
}

def download_video(url: str, db: Session):
    """下载单个视频"""
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 获取视频信息
            info = ydl.extract_info(url, download=False)
            video_id = info['id']
            
            # 构建保存路径
            date_str = datetime.now().strftime('%Y-%m-%d')
            save_dir = os.path.join(VIDEOS_DIR, date_str)
            os.makedirs(save_dir, exist_ok=True)
            
            # 设置下载选项
            ydl_opts.update({
                'outtmpl': os.path.join(save_dir, f'{video_id}.%(ext)s'),
                'progress_hooks': [lambda d: download_progress_hook(d, db)],
            })
            
            # 下载视频
            ydl.download([url])
            
            # 更新数据库
            video = Video(
                title=info.get('title', f'视频 {video_id}'),
                author=info.get('uploader_id', '未知作者'),
                duration=info.get('duration', 0),
                description=info.get('description', '无描述'),
                youtube_url=url,
                file_path=os.path.join(save_dir, f'{video_id}.mp4'),
                audio_path=os.path.join(save_dir, f'{video_id}.m4a'),
                thumbnail_path=os.path.join(save_dir, f'{video_id}.jpg'),
                file_size=os.path.getsize(os.path.join(save_dir, f'{video_id}.mp4')) / (1024 * 1024)  # MB
            )
            db.add(video)
            db.commit()
            
            return video
            
    except Exception as e:
        logger.error(f"下载视频失败: {str(e)}")
        raise

def batch_download(urls: list, db: Session):
    """批量下载视频"""
    try:
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        for url in urls:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    # 获取视频信息
                    info = ydl.extract_info(url, download=False)
                    video_id = info['id']
                    channel_id = info.get('uploader_id', 'unknown')
                    
                    # 构建保存路径
                    save_dir = os.path.join(BATCH_VIDEOS_DIR, date_str, channel_id)
                    os.makedirs(save_dir, exist_ok=True)
                    
                    # 创建数据库记录
                    video = BatchVideo(
                        title=info.get('title', f'视频 {video_id}'),
                        author=info.get('uploader_id', '未知作者'),
                        channel_id=channel_id,
                        duration=info.get('duration', 0),
                        description=info.get('description', '无描述'),
                        youtube_url=url,
                        file_path=os.path.join(save_dir, f'{video_id}.mp4'),
                        audio_path=os.path.join(save_dir, f'{video_id}.m4a'),
                        thumbnail_path=os.path.join(save_dir, f'{video_id}.jpg'),
                        upload_time=info.get('upload_date', ''),
                        download_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        status='downloading'
                    )
                    db.add(video)
                    db.commit()
                    
                    # 设置下载选项
                    ydl_opts.update({
                        'outtmpl': os.path.join(save_dir, f'{video_id}.%(ext)s'),
                        'progress_hooks': [lambda d: batch_progress_hook(d, video.id, db)],
                    })
                    
                    # 下载视频
                    ydl.download([url])
                    
                    # 更新文件大小和状态
                    video.file_size = os.path.getsize(video.file_path) / (1024 * 1024)  # MB
                    video.status = 'completed'
                    db.commit()
                    
            except Exception as e:
                logger.error(f"批量下载单个视频失败: {str(e)}")
                if 'video' in locals():
                    video.status = 'error'
                    video.error_message = str(e)
                    db.commit()
                continue
                
    except Exception as e:
        logger.error(f"批量下载失败: {str(e)}")
        raise

def get_batch_progress(video_id: int, db: Session):
    """获取批量下载进度"""
    try:
        video = db.query(BatchVideo).filter(BatchVideo.id == video_id).first()
        if not video:
            return {"status": "error", "message": "视频不存在"}
            
        return {
            "status": video.status,
            "error_message": video.error_message if video.status == 'error' else None
        }
        
    except Exception as e:
        logger.error(f"获取进度失败: {str(e)}")
        raise

def download_progress_hook(d, db):
    """下载进度回调"""
    if d['status'] == 'downloading':
        # 可以在这里添加进度更新逻辑
        pass
    elif d['status'] == 'error':
        logger.error(f"下载出错: {d.get('error')}")

def batch_progress_hook(d, video_id, db):
    """批量下载进度回调"""
    try:
        video = db.query(BatchVideo).filter(BatchVideo.id == video_id).first()
        if not video:
            return
            
        if d['status'] == 'downloading':
            # 更新下载进度
            pass
        elif d['status'] == 'error':
            video.status = 'error'
            video.error_message = str(d.get('error'))
            db.commit()
            
    except Exception as e:
        logger.error(f"更新进度失败: {str(e)}") 