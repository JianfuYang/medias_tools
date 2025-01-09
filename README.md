# YouTube视频下载器

一个简单的YouTube视频下载和管理Web应用。

## 功能特性

- YouTube视频下载
  - 支持输入视频链接异步下载
  - 显示下载进度
  - 下载完成后展示视频信息
- 本地视频管理
  - 列表展示已下载视频
  - 支持视频预览播放
  - 显示视频详细信息

## 安装使用

1. 安装依赖:
```bash
pip install -r requirements.txt
```

2. 运行应用:
```bash
uvicorn main:app --reload
```

3. 访问应用:
打开浏览器访问 http://localhost:8000 