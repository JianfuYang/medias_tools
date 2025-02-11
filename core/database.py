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