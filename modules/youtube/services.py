import yt_dlp
import os
import logging
import subprocess
from datetime import datetime
from sqlalchemy.orm import Session
from config.settings import VIDEOS_DIR, BATCH_VIDEOS_DIR
from .models import Video, BatchVideo

logger = logging.getLogger(__name__)

# 存储下载进度
download_progress = {}

# yt-dlp基础配置
YDL_OPTS = {
    'format': 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    'merge_output_format': 'mp4',
    'writethumbnail': True,
    'writeinfojson': True,
    'quiet': False,
    'no_warnings': False,
    'ignoreerrors': True,
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

def progress_hook(d):
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

def check_ffmpeg():
    """检查ffmpeg是否安装"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except Exception:
        logger.warning("ffmpeg未安装，某些功能可能受限")
        return False

def get_date_folder():
    """获取当前日期的文件夹路径"""
    today = datetime.now().strftime('%Y-%m-%d')
    folder_path = os.path.join(VIDEOS_DIR, today)
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

async def download_video(url: str, db: Session):
    """后台下载视频"""
    try:
        logger.info(f"开始下载视频: {url}")
        
        # 创建日期文件夹
        date_str = datetime.now().strftime('%Y-%m-%d')
        save_dir = os.path.join(VIDEOS_DIR, date_str)  # VIDEOS_DIR 是 toolsfile/youtube/videos
        thumbnails_dir = os.path.join(save_dir, "thumbnails")
        os.makedirs(thumbnails_dir, exist_ok=True)
        
        # 复制基础配置并添加特定配置
        ydl_opts = YDL_OPTS.copy()
        ydl_opts.update({
            'outtmpl': os.path.join(save_dir, '%(id)s.%(ext)s'),
            'progress_hooks': [progress_hook],
            'writethumbnail': True,  # 确保开启缩略图下载
            'postprocessors': [
                {
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                },
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'm4a',
                    'preferredquality': '192',
                },
                {
                    # 添加缩略图处理器
                    'key': 'FFmpegThumbnailsConvertor',
                    'format': 'jpg',
                },
            ],
        })

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 获取视频信息
            info = ydl.extract_info(url, download=False)
            video_id = info['id']
            
            # 下载视频
            ydl.download([url])
            
            # 检查并处理缩略图
            thumbnail_path = os.path.join(thumbnails_dir, f'{video_id}.jpg')
            webp_path = os.path.join(save_dir, f'{video_id}.webp')
            
            # 如果存在webp格式的缩略图，转换为jpg
            if os.path.exists(webp_path):
                convert_thumbnail(webp_path, thumbnail_path)
                # 删除webp文件
                os.remove(webp_path)
            # 如果没有缩略图，从视频中提取
            elif not os.path.exists(thumbnail_path):
                video_path = os.path.join(save_dir, f'{video_id}.mp4')
                extract_thumbnail(video_path, thumbnail_path)
            
            # 构建数据库存储的路径（相对于VIDEOS_DIR的路径）
            relative_path = os.path.join(date_str, f'{video_id}.mp4')
            relative_audio_path = os.path.join(date_str, f'{video_id}.m4a')
            relative_thumbnail_path = os.path.join(date_str, 'thumbnails', f'{video_id}.jpg')
            
            # 更新数据库
            video = Video(
                title=info.get('title', f'视频 {video_id}'),
                author=info.get('uploader_id', '未知作者'),
                duration=info.get('duration', 0),
                description=info.get('description', '无描述'),
                youtube_url=url,
                file_path=os.path.join('toolsfile/youtube/videos', relative_path),
                audio_path=os.path.join('toolsfile/youtube/videos', relative_audio_path),
                thumbnail_path=os.path.join('toolsfile/youtube/videos', relative_thumbnail_path),
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
                with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
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
                    YDL_OPTS.update({
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

def get_progress(video_id: str):
    """获取下载进度"""
    if video_id in download_progress:
        # 存在则说明还没下载完成或失败
        progress = download_progress.get(video_id, 0)
    else:
        # 不存在则说明下载完成
        progress = 100
    logger.info(f"进度查询 - 视频ID: {video_id}, 进度: {progress}%")
    return {"progress": progress} 