from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config.settings import SQLALCHEMY_DATABASE_URL, BATCH_DATABASE_URL

# 单个视频下载数据库
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 批量下载视频数据库
batch_engine = create_engine(
    BATCH_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
BatchSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=batch_engine)

Base = declarative_base()

# 初始化数据库表
def init_db():
    """初始化所有数据库表"""
    from modules.chatgpt.models import ChatSession, ChatMessage
    from modules.youtube.models import Video, BatchVideo
    
    # 创建主数据库表
    Base.metadata.create_all(bind=engine)
    
    # 创建批量下载数据库表
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