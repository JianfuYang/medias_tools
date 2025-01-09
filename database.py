from sqlalchemy import create_engine, Column, Integer, String, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./youtube_videos.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 