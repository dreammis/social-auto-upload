# 视频文件管理器

一个基于 Gradio 的视频文件管理工具，帮助你管理本地视频文件和元数据。

## 功能特点

- 📁 文件树浏览
- 📊 视频信息显示
- 📝 元数据管理
- 🔄 实时更新

## 快速开始

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 配置环境变量：
```bash
cp .env.example .env
# 编辑 .env 文件，设置你的配置
```

3. 运行应用：
```bash
python run.py
```

4. 打开浏览器访问：
```
http://localhost:7860
```

## 目录结构

```
video_file_manager/
├── core/               # 核心功能模块
├── ui/                 # 用户界面模块
├── utils/             # 工具函数
├── .env.example       # 环境变量示例
├── config.py          # 配置文件
├── requirements.txt   # 依赖清单
└── run.py            # 启动脚本
```

## 配置说明

- `DEBUG`: 调试模式开关
- `VIDEO_DIR`: 视频目录路径
- `LOG_DIR`: 日志目录路径
- `HOST`: 服务器地址
- `PORT`: 服务器端口

## 使用说明

1. 左侧面板显示文件树，可以浏览和选择视频文件
2. 右侧面板显示选中视频的详细信息
3. 可以查看和编辑视频的元数据
4. 支持实时刷新目录结构

## 开发说明

- 使用 Python 3.10+
- 基于 Gradio 5.15+
 