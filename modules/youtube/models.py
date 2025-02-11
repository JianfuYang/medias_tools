from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from core.database import Base
from datetime import datetime

class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    author = Column(String)
    duration = Column(Integer)  # 视频时长（秒）
    description = Column(Text)
    youtube_url = Column(String)
    file_path = Column(String)  # 视频文件路径
    audio_path = Column(String)  # 音频文件路径
    thumbnail_path = Column(String)  # 缩略图路径
    file_size = Column(Float)  # 文件大小（MB）

class BatchVideo(Base):
    __tablename__ = "batch_videos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    author = Column(String)
    duration = Column(Integer)
    description = Column(Text)
    youtube_url = Column(String)
    file_path = Column(String)
    audio_path = Column(String)
    thumbnail_path = Column(String)
    file_size = Column(Float)
    channel_id = Column(String, index=True)
    upload_time = Column(String)
    download_time = Column(String)
    status = Column(String)
    error_message = Column(Text) 