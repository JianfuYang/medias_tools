# 媒体效率工具库

一个基于 FastAPI + Tailwind CSS 的在线媒体工具集合，提供视频下载、AI图像生成、文字卡片制作等功能。

## 主要功能

### YouTube下载器
- 支持单个视频下载和批量下载
- 自动提取音频和缩略图
- 支持下载YouTube Shorts短视频
- 按日期和用户分类管理下载内容
- 实时显示下载进度
- 支持视频预览和在线播放
- 显示详细的视频信息（标题、作者、时长等）

### AI文生图（开发中）
- 通过文字描述生成图像
- 支持多种艺术风格
- 提供参数微调功能

### 文字卡片生成（开发中）
- 提供多种精美模板
- 支持自定义样式
- 一键生成分享图

## 技术栈

### 后端
- Python FastAPI
- SQLAlchemy + SQLite
- yt-dlp
- FFmpeg

### 前端
- Tailwind CSS
- JavaScript
- Video.js
- Font Awesome

### 模板引擎
- Jinja2

## 系统要求

- Python 3.8+
- FFmpeg
- 足够的磁盘空间用于存储下载的视频

## 安装步骤

1. 克隆仓库：
```bash
git clone [repository-url]
cd media-tools
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 安装FFmpeg：
- Windows: 下载并添加到系统环境变量
- macOS: `brew install ffmpeg`
- Linux: `sudo apt-get install ffmpeg`

4. 创建必要的目录：
```bash
mkdir -p toolsfile/youtube/{videos,batch_videos}
mkdir -p dbfile/youtube
mkdir -p static/images
```

## 目录结构

```
media-tools/
├── config/                 # 配置文件
│   ├── settings.py        # 全局设置
│   └── tools.py           # 工具配置
├── core/                  # 核心模块
│   └── database.py       # 数据库配置
├── modules/              # 功能模块
│   └── youtube/         # YouTube下载模块
├── static/              # 静态文件
│   ├── css/            # 样式文件
│   └── images/         # 图片资源
├── templates/           # HTML模板
│   ├── common/         # 公共模板
│   ├── home/           # 首页模板
│   ├── navigation/     # 导航模板
│   └── tools/          # 工具模板
├── toolsfile/          # 下载文件存储
│   └── youtube/        # YouTube视频存储
├── dbfile/             # 数据库文件
│   └── youtube/        # YouTube数据库
├── main.py             # 主程序
└── requirements.txt    # Python依赖
```

## 使用说明

1. 启动服务：
```bash
python main.py
```

2. 访问地址：`http://localhost:8000`

3. YouTube下载器使用：
   - 单视频下载：输入视频URL，点击下载
   - 批量下载：输入频道URL，自动下载最近3个月的短视频
   - 下载历史：查看和管理已下载的视频

## 文件存储结构

```
toolsfile/
└── youtube/
    ├── videos/              # 单视频下载
    │   └── YYYY-MM-DD/     # 按日期分类
    │       ├── video_id.mp4
    │       ├── video_id.m4a
    │       └── thumbnails/
    └── batch_videos/        # 批量下载
        └── YYYY-MM-DD/     # 按日期分类
            └── channel_id/  # 按频道分类
                ├── video_id.mp4
                ├── video_id.m4a
                └── video_id.jpg
```

## 注意事项

1. 确保系统已正确安装FFmpeg
2. 下载前检查磁盘空间是否充足
3. 批量下载仅支持最近3个月的短视频
4. 建议使用稳定的网络连接
5. 部分视频可能因版权限制无法下载

## 开发计划

- [ ] 完善AI文生图功能
- [ ] 添加文字卡片生成器
- [ ] 支持更多视频平台
- [ ] 添加用户系统
- [ ] 优化下载速度
- [ ] 添加视频处理功能

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 发起 Pull Request

## 许可证

MIT License 