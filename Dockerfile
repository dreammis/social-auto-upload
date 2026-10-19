# ===== 阶段 1：构建前端 =====
FROM node:22.21.1-slim AS builder

WORKDIR /app

RUN npm config set registry https://registry.npmmirror.com

COPY sau_frontend/package.json ./

RUN npm install

# 复制前端源码
COPY sau_frontend .

# 生产环境构建：将 API 地址设为空，使前端走同源相对路径（由 Flask 统一服务）
ENV NODE_ENV=production
ENV VITE_API_BASE_URL=""

RUN npm run build


# ===== 阶段 2：构建后端运行环境 =====
FROM python:3.10.19-slim

WORKDIR /app

ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# Playwright / Chromium 运行所需的系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxkbcommon0 \
    libasound2 \
    libcairo2 \
    libpango-1.0-0 \
    libcups2 \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple

# 先复制依赖清单，利用 Docker 层缓存
COPY requirements.txt ./
RUN pip install -r requirements.txt

# 安装 Playwright 的 chromium-headless-shell（npmmirror 镜像源加速）
ENV PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright
RUN playwright install chromium-headless-shell

# 安装 patchright 的 chromium（必须使用官方源 cdn.playwright.dev）
# 注意：patchright 1.58.2 的 chromium 映射到 Chrome for Testing 145.0.7632.6，
# 走 cft 下载路径，npmmirror 镜像不含该版本（404），必须去掉 PLAYWRIGHT_DOWNLOAD_HOST
RUN unset PLAYWRIGHT_DOWNLOAD_HOST \
    && patchright install chromium

# 清理下载源环境变量，避免影响运行时
ENV PLAYWRIGHT_DOWNLOAD_HOST=

# 复制后端源码
COPY . .

# 生成配置文件（若镜像外挂载了 conf.py，运行时会被覆盖）
RUN cp conf.example.py conf.py

# 复制前端构建产物
COPY --from=builder /app/dist/index.html /app/index.html
COPY --from=builder /app/dist/assets /app/assets
# vite.svg 由 public/ 原样拷贝到 dist/ 根目录，再放到 assets/ 供 Flask 路由读取
COPY --from=builder /app/dist/vite.svg /app/assets/vite.svg

# 运行时目录（上传/素材存储/数据库）
RUN mkdir -p /app/videoFile /app/cookiesFile /app/db

# 复制启动脚本并赋予执行权限
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 5409

# 使用 entrypoint 在容器启动时初始化数据库（卷挂载后），再启动后端
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "sau_backend.py"]
