import os
import re
import yt_dlp
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Optional
import json
import asyncio
from database import BatchVideo, get_batch_db
from sqlalchemy.orm import Session
import subprocess
import urllib.parse
from urllib.parse import unquote
from fastapi import HTTPException, APIRouter
from starlette.responses import FileResponse

# 创建路由器
router = APIRouter()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('batch_downloader.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 存储下载进度
batch_progress: Dict[str, Dict] = {}

def get_date_folder(date_str: str, channel_id: str):
    """获取日期和用户的文件夹路径"""
    # 对channel_id进行URL解码，以支持中文用户名
    decoded_channel_id = urllib.parse.unquote(channel_id)
    # 创建文件夹路径
    folder_path = f"batch_videos/{date_str}/{decoded_channel_id}"
    os.makedirs(folder_path, exist_ok=True)
    return folder_path

def get_media_paths(video_id: str, date_folder: str):
    """获取媒体文件路径"""
    return {
        'video': f"{date_folder}/{video_id}.mp4",
        'audio': f"{date_folder}/{video_id}.f140.m4a",
        'thumbnail': f"{date_folder}/{video_id}.jpg",
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

def format_upload_time(upload_date: str, upload_time: Optional[str] = None) -> str:
    """格式化上传时间"""
    try:
        if upload_time:
            # 如果有具体时间，使用完整格式
            dt = datetime.strptime(f"{upload_date} {upload_time}", "%Y%m%d %H:%M:%S")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        else:
            # 只有日期的情况
            dt = datetime.strptime(upload_date, "%Y%m%d")
            return dt.strftime("%Y-%m-%d")
    except Exception as e:
        logger.error(f"格式化上传时间失败: {str(e)}")
        return upload_date

async def download_batch_video(video_url: str, channel_id: str, db: Session):
    """下载单个视频的异步函数"""
    video_id = None
    try:
        # 获取当前日期
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 创建日期文件夹
        date_folder = get_date_folder(today, channel_id)
        
        # yt-dlp配置
        ydl_opts = {
            'format': 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'merge_output_format': 'mp4',
            'outtmpl': f'{date_folder}/%(id)s.%(ext)s',
            'progress_hooks': [progress_hook],
            'quiet': False,
            'no_warnings': False,
            'writethumbnail': True,
            'writeinfojson': True,
            'retries': 10,
            'fragment_retries': 10,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
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
            ]
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 获取视频信息
            info = ydl.extract_info(video_url, download=False)
            if not info:
                raise Exception("无法获取视频信息")
            
            video_id = info['id']
            
            # 格式化上传时间
            upload_time = format_upload_time(
                info.get('upload_date', ''),
                info.get('upload_time', None)
            )
            
            # 初始化进度信息
            batch_progress[video_id] = {
                'channel_id': channel_id,
                'progress': 0,
                'status': 'downloading',
                'title': info.get('title', f'视频 {video_id}'),
                'error': None,
                'upload_time': upload_time
            }
            
            logger.info(f"开始下载视频: {info.get('title')} ({video_id})")
            logger.info(f"上传时间: {upload_time}")
            
            # 获取文件路径
            paths = get_media_paths(video_id, date_folder)
            
            # 下载视频
            result = ydl.download([video_url])
            if result != 0:
                raise Exception("下载失败，返回码非0")
            
            # 检查文件是否存在
            if not os.path.exists(paths['video']):
                raise Exception("下载完成但找不到视频文件")
                
            # 生成缩略图
            if not os.path.exists(paths['thumbnail']):
                logger.info("从视频中提取缩略图...")
                if not extract_thumbnail(paths['video'], paths['thumbnail']):
                    logger.warning("无法从视频中提取缩略图")
            
            # 计算文件大小
            file_size = os.path.getsize(paths['video']) / (1024 * 1024)  # MB
            
            # 保存到数据库
            video = BatchVideo(
                title=info.get('title', f'视频 {video_id}'),
                author=info.get('uploader', '未知作者'),
                duration=info.get('duration', 0),
                description=info.get('description', '无描述'),
                youtube_url=video_url,
                file_path=paths['video'],
                audio_path=paths['audio'],
                thumbnail_path=paths['thumbnail'],
                file_size=round(file_size, 2),
                channel_id=channel_id,
                upload_time=upload_time,
                download_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                status='completed'
            )
            
            db.add(video)
            db.commit()
            
            # 更新进度信息
            batch_progress[video_id].update({
                'status': 'completed',
                'progress': 100,
                'error': None
            })
            
            logger.info(f"视频下载完成: {info.get('title')} ({video_id})")
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"下载视频失败: {error_msg}")
        if video_id:
            batch_progress[video_id].update({
                'status': 'error',
                'error': error_msg,
                'progress': 0
            })
            
            # 更新数据库中的错误状态
            try:
                video = db.query(BatchVideo).filter(BatchVideo.youtube_url == video_url).first()
                if video:
                    video.status = 'error'
                    video.error_message = error_msg
                    db.commit()
            except Exception as db_error:
                logger.error(f"更新数据库错误状态失败: {str(db_error)}")
                
        raise Exception(f"下载失败: {error_msg}")

def progress_hook(d):
    """下载进度回调函数"""
    video_id = d.get('info_dict', {}).get('id')
    if not video_id or video_id not in batch_progress:
        return

    if d['status'] == 'downloading':
        try:
            total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
            downloaded = d.get('downloaded_bytes', 0)
            if total > 0:
                progress = int((downloaded / total) * 100)
                batch_progress[video_id].update({
                    'progress': progress,
                    'status': 'downloading'
                })
        except Exception as e:
            logger.error(f"更新下载进度失败: {str(e)}")
    elif d['status'] == 'error':
        batch_progress[video_id].update({
            'status': 'error',
            'error': d.get('error', '未知错误'),
            'progress': 0
        })
    elif d['status'] == 'finished':
        batch_progress[video_id].update({
            'status': 'processing',
            'progress': 95  # 下载完成，等待处理
        }) 

async def get_channel_shorts(channel_url: str) -> List[Dict]:
    """获取YouTube频道的所有Shorts视频链接和信息"""
    try:
        logger.info(f"开始获取频道视频: {channel_url}")
        
        # 处理各种可能的URL格式
        if '@' not in channel_url and 'channel/' not in channel_url and 'c/' not in channel_url:
            raise Exception("无效的频道URL格式")
        
        # 清理URL
        base_url = channel_url.split('?')[0].rstrip('/')
        if '/shorts/' in base_url:
            base_url = base_url.split('/shorts/')[0]
        elif '/videos/' in base_url:
            base_url = base_url.split('/videos/')[0]
            
        logger.info(f"处理后的基础URL: {base_url}")
        
        # 尝试不同的URL组合
        urls_to_try = [
            # f"{base_url}/shorts",
            # f"{base_url}/videos",
            base_url
        ]
        
        # 配置yt-dlp选项，获取更详细的视频信息
        ydl_opts = {
            'extract_flat': 'in_playlist',
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls'],
                    'player_skip': ['js', 'configs', 'webpage']
                }
            },
            'extractor_retries': 3,
            'retries': 3
        }
        
        # 获取详细信息的配置
        detail_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'ignoreerrors': True
        }
        
        all_shorts_info = []
        two_months_ago = datetime.now() - timedelta(days=60)
        
        logger.info("=" * 50)
        logger.info("开始获取视频信息")
        logger.info(f"时间范围: {two_months_ago.strftime('%Y-%m-%d')} 至今")
        logger.info("=" * 50)
        
        for url in urls_to_try:
            logger.info(f"尝试URL: {url}")
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    channel_info = ydl.extract_info(url, download=False)
                    
                    if not channel_info:
                        logger.warning(f"无法从 {url} 获取频道信息")
                        continue
                    
                    entries = channel_info.get('entries', [])
                    logger.info(f"从 {url} 找到 {len(entries)} 个视频条目")
                    
                    for entry in entries:
                        if not entry:
                            continue
                            
                        video_id = entry.get('id')
                        video_url = entry.get('url', '')
                        
                        # 获取详细的视频信息
                        try:
                            with yt_dlp.YoutubeDL(detail_opts) as detail_ydl:
                                video_info = detail_ydl.extract_info(
                                    f"https://www.youtube.com/watch?v={video_id}", 
                                    download=False
                                )
                                
                                if not video_info:
                                    logger.warning(f"无法获取视频 {video_id} 的详细信息")
                                    continue
                                
                                title = video_info.get('title', '未知标题')
                                duration = video_info.get('duration', 0)
                                upload_date = video_info.get('upload_date')
                                description = video_info.get('description', '')
                                
                                logger.info(f"发现视频: {title}")
                                logger.info(f"  - ID: {video_id}")
                                
                                # 处理上传时间
                                if upload_date:
                                    try:
                                        upload_datetime = datetime.strptime(upload_date, '%Y%m%d')
                                        logger.info(f"  - 上传时间: {upload_datetime.strftime('%Y-%m-%d')}")
                                    except ValueError:
                                        logger.warning(f"视频 {video_id} 时间格式错误: {upload_date}")
                                        continue
                                else:
                                    # 尝试从描述或其他字段获取时间信息
                                    publish_date = video_info.get('publish_date')
                                    if publish_date:
                                        upload_datetime = publish_date
                                    else:
                                        # 如果没有时间信息，使用当前时间
                                        logger.warning(f"视频 {video_id} 无法获取上传时间，使用当前时间")
                                        upload_datetime = datetime.now()
                                
                                logger.info(f"  - 时长: {duration}秒")
                                
                                # 判断是否是shorts视频
                                is_shorts = False
                                shorts_reasons = []
                                
                                # 通过URL判断
                                if '/shorts/' in video_url.lower() or 'shorts%2F' in video_url.lower():
                                    is_shorts = True
                                    shorts_reasons.append('URL包含shorts')
                                    
                                # 通过时长判断
                                if duration and duration <= 60:
                                    is_shorts = True
                                    shorts_reasons.append('视频时长<=60秒')
                                    
                                # 通过页面URL判断
                                if url.endswith('/shorts'):
                                    is_shorts = True
                                    shorts_reasons.append('来自shorts页面')
                                    
                                # 通过标题或描述判断
                                if '#shorts' in (description + title).lower():
                                    is_shorts = True
                                    shorts_reasons.append('标题或描述包含#shorts')
                                
                                # 记录判断结果
                                if is_shorts:
                                    logger.info(f"  - 类型: Shorts ({', '.join(shorts_reasons)})")
                                    
                                    # 检查是否在时间范围内
                                    if upload_datetime >= two_months_ago:
                                        shorts_url = f"https://youtube.com/shorts/{video_id}"
                                        # 避免重复添加
                                        if not any(s['url'] == shorts_url for s in all_shorts_info):
                                            all_shorts_info.append({
                                                'url': shorts_url,
                                                'title': title,
                                                'upload_date': upload_datetime,
                                                'duration': duration,
                                                'description': description
                                            })
                                            logger.info(f"  - 状态: 已添加到下载列表")
                                    else:
                                        logger.info(f"  - 状态: 超出时间范围")
                                else:
                                    logger.info(f"  - 状态: 不是Shorts视频")
                                
                        except Exception as e:
                            logger.warning(f"获取视频 {video_id} 详细信息时出错: {str(e)}")
                            continue
                            
                        logger.info("-" * 30)
            
            except Exception as e:
                logger.warning(f"处理URL {url} 时出错: {str(e)}")
                continue
        
        # 按上传时间降序排序
        all_shorts_info.sort(key=lambda x: x['upload_date'], reverse=True)
        
        # 限制下载数量为20个
        if len(all_shorts_info) > 20:
            logger.info(f"找到 {len(all_shorts_info)} 个视频，限制下载前20个最新视频")
            all_shorts_info = all_shorts_info[:20]
        
        logger.info("=" * 50)
        logger.info(f"总共找到 {len(all_shorts_info)} 个符合条件的Shorts视频")
        if all_shorts_info:
            logger.info("将下载以下视频:")
            for idx, info in enumerate(all_shorts_info, 1):
                logger.info(f"{idx}. {info['title']} ({info['upload_date'].strftime('%Y-%m-%d')})")
        logger.info("=" * 50)
        
        if not all_shorts_info:
            logger.warning("未找到任何符合条件的Shorts视频")
            logger.warning("没有找到任何可下载的视频，可能是因为:")
            logger.warning("1. 频道最近2个月没有发布shorts视频")
            logger.warning("2. 频道URL格式不正确")
            logger.warning("3. 视频可能无法访问")
            return []
        
        return all_shorts_info
            
    except Exception as e:
        logger.error(f"获取Shorts列表失败: {str(e)}")
        logger.exception("详细错误信息:")
        raise

async def start_batch_download(channel_url: str, db: Session):
    """开始批量下载"""
    try:
        # 获取频道ID
        # channel_id = channel_url.split('/')[-1]
        pattern = r"@(.+?)/shorts"
        channel_id = re.search(pattern, channel_url).group(1)
        if not channel_id:
            channel_id = channel_url.split('@')[-1].split('/')[0]
        if not channel_id:
            raise Exception("无法获取频道ID")
        
        # 获取所有Shorts视频信息
        shorts_info = await get_channel_shorts(channel_url)
        if not shorts_info:
            logger.warning("没有找到任何可下载的视频，可能是因为:")
            logger.warning("1. 频道最近2个月没有发布shorts视频")
            logger.warning("2. 频道URL格式不正确")
            logger.warning("3. 视频可能无法访问")
            return {"message": "未找到可下载的视频"}
        
        logger.info(f"找到 {len(shorts_info)} 个可下载的视频")
        
        # 创建下载任务
        tasks = []
        for info in shorts_info:
            task = asyncio.create_task(download_batch_video(info['url'], channel_id, db))
            tasks.append(task)
        
        # 等待所有任务完成
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return {"message": f"批量下载完成，共 {len(shorts_info)} 个视频"}
        
    except Exception as e:
        logger.error(f"批量下载失败: {str(e)}")
        raise Exception(f"批量下载失败: {str(e)}")

def get_batch_progress(channel_id: str = None):
    """获取批量下载进度"""
    if not channel_id:
        return list(batch_progress.values())
    
    # 返回指定频道的下载进度
    return [
        progress for progress in batch_progress.values()
        if progress.get('channel_id') == channel_id
    ] 

@router.get("/batch_videos/{date}/{username}/{filename}")
async def get_batch_video(date: str, username: str, filename: str):
    # 解码URL编码的路径参数
    decoded_username = unquote(username)
    file_path = os.path.join("batch_videos", date, decoded_username, filename)
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(file_path) 