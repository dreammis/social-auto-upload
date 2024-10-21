FROM --platform=linux/arm64 playwright/chromium:playwright-1.48.1

WORKDIR /app

# 安装Python和pip
RUN apt-get update && apt-get install -y python3 python3-pip || true

# 复制项目文件
COPY . /app

# 安装项目依赖
RUN pip3 install --no-cache-dir -r requirements.txt

# 暴露FastAPI应用的端口
EXPOSE 8000

# 运行FastAPI应用
CMD ["python3", "api.py"]
