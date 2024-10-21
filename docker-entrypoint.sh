#!/bin/sh

# 重试次数
RETRY_COUNT=3
# 重试间隔（秒）
RETRY_INTERVAL=5

# 尝试运行命令
for i in $(seq 1 $RETRY_COUNT); do
  echo "Attempt $i to run the command..."
  xvfb-run --auto-servernum --server-num=1 --server-args='-screen 0, 1920x1080x24' python api.py
  if [ $? -eq 0 ]; then
    exit 0
  else
    echo "Command failed, retrying in $RETRY_INTERVAL seconds..."
    sleep $RETRY_INTERVAL
  fi
done

echo "All attempts failed, exiting."
exit 1
