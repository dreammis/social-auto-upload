# 登录
# 建议由用户自己在本地真实终端里执行。
# 如果终端二维码显示不完整，可以打开当前目录下的 qrcode.png 扫码。
$account = "account_a"
# account_name is user-defined. One account_name maps to one account file.
# You can prepare multiple account names and run them in parallel.

sau bilibili login --account $account

# 校验
sau bilibili check --account $account

# 上传视频
sau bilibili upload-video `
  --account $account `
  --file .\videos\demo.mp4 `
  --title "Bilibili CLI Demo" `
  --desc "Bilibili CLI Demo" `
  --tid 249 `
  --tags 足球,测试 `
  --schedule "2026-03-26 16:00"
