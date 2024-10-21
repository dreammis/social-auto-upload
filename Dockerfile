FROM mcr.microsoft.com/playwright/python:v1.48.0-focal

ENV http_proxy="http://dev.datamatrixai.com:30130"
ENV https_proxy="http://dev.datamatrixai.com:30130"

WORKDIR /app

# 复制项目文件
COPY . /app

# 安装项目依赖
RUN pip3 install --no-cache-dir -r requirements.txt

# 暴露FastAPI应用的端口
EXPOSE 8000

ENV http_proxy=""
ENV https_proxy=""

# 运行FastAPI应用 xvfb-run --auto-servernum --server-num=1 --server-args='-screen 0, 1920x1080x24' python login.py
#CMD ["xvfb-run", "--auto-servernum", "--server-num=1", "--server-args='-screen 0, 1920x1080x24'", "python3", "api.py"]
