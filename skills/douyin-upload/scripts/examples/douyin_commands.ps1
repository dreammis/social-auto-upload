# PowerShell examples for the installed sau CLI.

$account = "creator"
$video = "videos/demo.mp4"
$thumbnail = "videos/demo.png"
$noteImages = @("videos/1.png", "videos/2.png")

sau douyin login --account $account --headless
sau douyin check --account $account

sau douyin upload-video `
  --account $account `
  --file $video `
  --title "Douyin video from PowerShell" `
  --tags "cli,video" `
  --thumbnail $thumbnail `
  --headless

sau douyin upload-note `
  --account $account `
  --images $noteImages `
  --note "Douyin note from PowerShell" `
  --tags "cli,note" `
  --headless
