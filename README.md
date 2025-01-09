# YouTube 视频下载器

一个基于 FastAPI + yt-dlp 的 YouTube 视频下载工具，支持高质量视频下载、音频提取和缩略图保存。

## 功能特性

- 支持下载 YouTube 视频、Shorts 和播放列表
- 自动提取并保存音频文件（m4a 格式，192kbps）
- 自动生成视频缩略图
- 按日期分类管理下载内容
- 实时显示下载进度
- 支持视频预览和在线播放
- 显示详细的视频信息（标题、作者、时长、文件大小等）
- 支持分别下载视频、音频和缩略图
- 仅显示最近一周的下载记录

## 技术栈

- 后端：Python FastAPI
- 视频处理：yt-dlp + FFmpeg
- 数据库：SQLite + SQLAlchemy
- 前端：HTML + Tailwind CSS + JavaScript
- 模板引擎：Jinja2

## 系统要求

- Python 3.8+
- FFmpeg（用于视频处理和缩略图生成）
- 足够的磁盘空间用于存储下载的视频

## 安装步骤

1. 克隆仓库：
```bash
git clone [repository-url]
cd youtube_downloader
```

2. 安装 Python 依赖：
```bash
pip install -r requirements.txt
```

3. 安装 FFmpeg：
- macOS：
```bash
brew install ffmpeg
```
- Linux：
```bash
sudo apt-get install ffmpeg
```
- Windows：
  - 下载 FFmpeg 并添加到系统环境变量

4. 创建必要的目录：
```bash
mkdir -p static/thumbnails videos
```

## 使用方法

1. 启动服务器：
```bash
python main.py
```
或者使用 uvicorn：
```bash
uvicorn main:app --reload
```

2. 打开浏览器访问：`http://localhost:8000`

3. 在输入框中粘贴 YouTube 视频链接，点击"下载"按钮

4. 等待下载完成，下载的文件将按日期分类保存在 videos 目录中

## 文件结构

```
youtube_downloader/
├── main.py              # 主程序文件
├── database.py          # 数据库模型
├── requirements.txt     # Python 依赖
├── static/             # 静态文件目录
│   ├── css/           # CSS 文件
│   └── thumbnails/    # 视频缩略图
├── templates/          # HTML 模板
│   └── index.html     # 主页模板
├── videos/            # 下载的视频文件
│   └── YYYY-MM-DD/   # 按日期分类的视频目录
└── youtube_downloader.log  # 日志文件
```

## 文件保存结构

下载的文件按日期分类保存在 videos 目录下：
```
videos/
└── YYYY-MM-DD/
    ├── [video_id].mp4      # 视频文件
    ├── [video_id].m4a      # 音频文件
    ├── [video_id].info.json # 视频信息
    └── thumbnails/
        └── [video_id].jpg   # 缩略图
```

## 注意事项

1. 确保系统已正确安装 FFmpeg，否则部分功能可能无法使用
2. 下载视频前请确认有足够的磁盘空间
3. 部分视频可能因版权限制无法下载
4. 建议使用稳定的网络连接
5. 默认只保存最近一周的下载记录显示

## 开发计划

- [ ] 添加视频格式选择功能
- [ ] 支持批量下载
- [ ] 添加下载历史记录搜索功能
- [ ] 添加视频标签分类功能
- [ ] 支持更多视频平台

## 许可证

MIT License 