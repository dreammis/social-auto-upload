# PowerShell examples for the installed sau CLI.

# account_name is user-defined. One account_name maps to one account file.
# You can prepare multiple account names and run them in parallel.
$account = "account_a"
$video = "videos/demo.mp4"
$thumbnail = "videos/demo.png"
$noteImages = @("videos/1.png", "videos/2.png")

sau douyin login --account $account --headless
sau douyin check --account $account

sau douyin upload-video `
  --account $account `
  --file $video `
  --title "Douyin video from PowerShell" `
  --desc "Douyin video description from PowerShell" `
  --tags "cli,video" `
  --thumbnail $thumbnail `
  --headless

sau douyin upload-note `
  --account $account `
  --images $noteImages `
  --title "Douyin note title from PowerShell" `
  --note "Douyin note from PowerShell" `
  --tags "cli,note" `
  --headless
