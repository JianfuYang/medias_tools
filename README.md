# 媒体效率工具库

一个基于 FastAPI + Tailwind CSS 的综合性在线工具平台，集成了媒体处理、AI助手、实用工具等多种功能模块。

## 平台概述

### 核心特点
- 模块化设计，易于扩展
- 统一的用户界面和操作体验
- 响应式布局，支持多端访问
- RESTful API支持
- 实时处理反馈
- 批量处理能力

### 功能分类

#### 1. 媒体处理工具
- **YouTube下载器**
  - 单视频/批量下载
  - 音视频分离
  - 格式转换
  - 在线预览
- **图片处理**
  - 图片压缩
  - 格式转换
  - 批量处理
  - 在线预览
- **音视频工具**（开发中）
  - 视频压缩
  - 格式转换
  - 视频剪辑
  - 音频提取

#### 2. AI助手工具
- **ChatGPT对话**
  - 多轮对话支持
  - 上下文记忆
  - 代码高亮
  - 会话导出
- **AI图像生成**（开发中）
  - 文本生图
  - 图片编辑
  - 风格迁移
- **智能助手**（规划中）
  - 文本摘要
  - 代码解释
  - 数据分析

#### 3. 实用工具集
- **文档处理**
  - PDF转换
  - 文字提取
  - 格式转换
- **开发工具**
  - 代码格式化
  - JSON编辑器
  - 正则测试
- **其他工具**
  - 文字卡片生成
  - 二维码生成
  - 图表制作

## 技术架构

### 后端架构
- **Web框架**: FastAPI
- **数据库**: 
  - SQLite (本地存储)
  - Redis (缓存)
- **媒体处理**:
  - FFmpeg (音视频)
  - Pillow (图片)
  - yt-dlp (视频下载)
- **AI集成**:
  - OpenAI API
  - Stable Diffusion
- **任务队列**: Celery

### 前端技术
- **UI框架**: 
  - TailwindCSS
  - Alpine.js
- **交互组件**:
  - Video.js
  - CodeMirror
  - Chart.js
- **构建工具**: 
  - Webpack
  - PostCSS

### 部署架构
- **应用服务器**: uvicorn
- **反向代理**: Nginx
- **容器化**: Docker
- **CI/CD**: GitHub Actions

## 项目结构
```
media-tools/
├── config/                # 配置文件
│   ├── settings.py       # 全局设置
│   └── tools.py          # 工具配置
├── core/                 # 核心模块
│   ├── database.py      # 数据库配置
│   ├── security.py      # 安全相关
│   └── celery_app.py    # Celery配置
├── modules/             # 功能模块
│   ├── youtube/        # YouTube下载
│   ├── image_compress/ # 图片压缩
│   ├── chatgpt/       # AI对话
│   └── utils/         # 通用工具
├── static/             # 静态资源
├── templates/          # 模板文件
├── toolsfile/         # 文件存储
├── tests/             # 测试用例
└── docs/              # 文档
```

## 功能模块详解

### 1. YouTube下载器
- 支持单个视频下载和批量下载
- 自动提取音频和缩略图
- 支持下载YouTube Shorts短视频
- 按日期和用户分类管理下载内容
- 实时显示下载进度
- 支持视频预览和在线播放
- 显示详细的视频信息（标题、作者、时长等）

### 2. 图片压缩工具
- 支持多种图片格式(PNG、JPG、JPEG、WebP)
- 智能压缩算法，在保证画质的同时大幅减小文件体积
- 批量处理功能
- 自定义压缩参数：
  - 压缩质量(0-100)
  - 最大宽度限制(可选)
  - EXIF信息保留选项
- 直观的压缩效果预览
- 便捷的图片下载方式

### 3. ChatGPT对话
- **功能特点**
  - 支持多种对话模式
  - 代码高亮显示
  - 会话历史管理
  - Markdown渲染
- **使用方法**
  - 选择对话模式
  - 输入问题
  - 查看历史记录
  - 导出会话

### 4. 调整大小工具
- 完全本地处理，无需上传服务器
- 支持拖放上传图片
- 实时预览调整效果
- 智能锁定宽高比例
- 支持PNG、JPG、GIF等常见格式
- 最大支持10000x10000像素
- 高质量图片处理
- 一键下载调整后的图片

#### 使用说明
1. 选择或拖放图片到上传区域
2. 在调整设置中输入目标宽度或高度
3. 可选择是否锁定宽高比例
4. 点击"调整大小"按钮预览效果
5. 确认效果后点击下载按钮保存

#### 注意事项
- 建议图片尺寸不要超过10000像素
- 锁定比例可以避免图片变形
- 支持常见图片格式，输出为PNG格式
- 所有处理都在浏览器中完成，保护隐私

## 开发规范

### 代码规范
- Python: PEP 8
- JavaScript: ESLint
- HTML/CSS: Prettier
- 提交信息: Angular规范

### 文档规范
- 代码注释完整
- API文档及时更新
- 更新日志维护
- 测试用例覆盖

## 部署指南

1. 克隆项目
```bash
git clone https://github.com/yourusername/media-tools.git
cd media-tools
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 安装FFmpeg
- Windows: 下载并添加到系统环境变量
- macOS: `brew install ffmpeg`
- Linux: `sudo apt-get install ffmpeg`

4. 创建必要的目录
```bash
mkdir -p toolsfile/youtube/{videos,batch_videos}
mkdir -p dbfile/youtube
mkdir -p static/images
```

5. 启动服务
```bash
uvicorn main:app --reload
```

6. 访问服务
打开浏览器访问 http://localhost:8000

## 使用指南

### YouTube下载器
1. 单视频下载
   - 输入视频URL
   - 选择下载质量
   - 点击下载按钮
2. 批量下载
   - 输入频道URL
   - 设置下载参数
   - 开始批量下载
3. 下载管理
   - 查看下载历史
   - 管理已下载文件
   - 预览和播放视频

### 图片压缩工具
1. 上传图片
   - 点击上传或拖拽图片
   - 支持批量上传
2. 设置压缩参数
   - 调整压缩质量
   - 设置最大宽度
   - 选择EXIF选项
3. 下载结果
   - 点击图片下载
   - 批量下载全部

### ChatGPT对话
1. 选择对话模式
2. 输入问题
3. 查看历史记录
4. 导出会话

### 调整大小工具
1. 选择或拖放图片到上传区域
2. 在调整设置中输入目标宽度或高度
3. 可选择是否锁定宽高比例
4. 点击"调整大小"按钮预览效果
5. 确认效果后点击下载按钮保存

## 开发计划

### 2024 Q1
- [ ] 完善AI助手功能
- [ ] 优化媒体处理性能
- [ ] 添加用户系统

### 2024 Q2
- [ ] 集成更多AI模型
- [ ] 添加数据分析功能
- [ ] 优化移动端体验

## 贡献指南

欢迎提交Issue和Pull Request。在提交PR之前，请确保：
1. 代码符合项目规范
2. 添加必要的测试
3. 更新相关文档

## 许可证

MIT License

## 联系方式

- 项目主页：[GitHub](https://github.com/yourusername/media-tools)
- 问题反馈：[Issues](https://github.com/yourusername/media-tools/issues) 