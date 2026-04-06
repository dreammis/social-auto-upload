# login
# Run this in a local interactive terminal.
# If the terminal QR code is incomplete, open ./qrcode.png and scan that image.
account="account_a"
# account_name is user-defined. One account_name maps to one account file.
# You can prepare multiple account names and run them in parallel.

sau bilibili login --account "$account"

# check
sau bilibili check --account "$account"

# upload video
sau bilibili upload-video \
  --account "$account" \
  --file ./videos/demo.mp4 \
  --title "Bilibili CLI Demo" \
  --desc "Bilibili CLI Demo" \
  --tid 249 \
  --tags 足球,测试 \
  --schedule "2026-03-26 16:00"
