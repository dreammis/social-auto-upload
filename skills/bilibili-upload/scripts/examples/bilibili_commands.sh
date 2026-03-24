# login
# Run this in a local interactive terminal.
# If the terminal QR code is incomplete, open ./qrcode.png and scan that image.
sau bilibili login --account creator

# check
sau bilibili check --account creator

# upload video
sau bilibili upload-video \
  --account creator \
  --file ./videos/demo.mp4 \
  --title "Bilibili CLI Demo" \
  --desc "Bilibili CLI Demo" \
  --tid 249 \
  --tags 足球,测试 \
  --schedule "2026-03-26 16:00"
