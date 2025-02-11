import os

# 添加数据库目录配置
DB_DIR = "dbfile/youtube"
os.makedirs(DB_DIR, exist_ok=True)

# 数据库配置
SQLALCHEMY_DATABASE_URL = f"sqlite:///./{DB_DIR}/youtube_videos.db"
BATCH_DATABASE_URL = f"sqlite:///./{DB_DIR}/batch_videos.db"

# 文件路径配置
VIDEOS_DIR = "toolsfile/youtube/videos"
BATCH_VIDEOS_DIR = "toolsfile/youtube/batch_videos"
STATIC_DIR = "static"

# 确保目录存在
for dir_path in [VIDEOS_DIR, BATCH_VIDEOS_DIR, STATIC_DIR]:
    os.makedirs(dir_path, exist_ok=True) 