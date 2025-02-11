import os

# 数据库配置
SQLALCHEMY_DATABASE_URL = "sqlite:///./dbfile/youtube/youtube_videos.db"
BATCH_DATABASE_URL = "sqlite:///./dbfile/youtube/batch_videos.db"

# 文件路径配置
VIDEOS_DIR = "toolsfile/youtube/videos"
BATCH_VIDEOS_DIR = "toolsfile/youtube/batch_videos"
STATIC_DIR = "static"

# 确保目录存在
for dir_path in [VIDEOS_DIR, BATCH_VIDEOS_DIR, STATIC_DIR]:
    os.makedirs(dir_path, exist_ok=True) 