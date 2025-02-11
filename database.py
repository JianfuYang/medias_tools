from sqlalchemy import create_engine, Column, Integer, String, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 单个视频下载数据库
SQLALCHEMY_DATABASE_URL = "sqlite:///./dbfile/youtube/youtube_videos.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 批量下载视频数据库
BATCH_DATABASE_URL = "sqlite:///./dbfile/youtube/batch_videos.db"
batch_engine = create_engine(
    BATCH_DATABASE_URL, connect_args={"check_same_thread": False}
)
BatchSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=batch_engine)

Base = declarative_base()

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
    duration = Column(Integer)  # 视频时长（秒）
    description = Column(Text)
    youtube_url = Column(String)
    file_path = Column(String)  # 视频文件路径
    audio_path = Column(String)  # 音频文件路径
    thumbnail_path = Column(String)  # 缩略图路径
    file_size = Column(Float)  # 文件大小（MB）
    channel_id = Column(String, index=True)  # 频道ID
    upload_time = Column(String)  # 视频上传时间
    download_time = Column(String)  # 下载时间
    status = Column(String)  # 下载状态: pending, downloading, completed, error
    error_message = Column(Text)  # 错误信息

# 创建数据库表
Base.metadata.create_all(bind=engine)
Base.metadata.create_all(bind=batch_engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_batch_db():
    db = BatchSessionLocal()
    try:
        yield db
    finally:
        db.close() 