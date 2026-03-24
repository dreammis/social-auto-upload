# 登录
sau bilibili login --account creator

# 校验
sau bilibili check --account creator

# 上传视频
sau bilibili upload-video `
  --account creator `
  --file .\videos\demo.mp4 `
  --title "Bilibili CLI Demo" `
  --desc "Bilibili CLI Demo" `
  --tid 249 `
  --tags 足球,测试 `
  --schedule "2026-03-26 16:00"
