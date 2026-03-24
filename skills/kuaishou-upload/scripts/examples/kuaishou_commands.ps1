# PowerShell examples for the installed sau CLI.

$account = "creator"
$video = "videos/demo.mp4"
$thumbnail = "videos/demo.png"
$noteImages = @("videos/1.png", "videos/2.png", "videos/3.png")

sau kuaishou login --account $account --headed
sau kuaishou check --account $account

sau kuaishou upload-video `
  --account $account `
  --file $video `
  --title "Kuaishou video from PowerShell" `
  --tags "cli,video" `
  --thumbnail $thumbnail `
  --headless

sau kuaishou upload-note `
  --account $account `
  --images $noteImages `
  --note "Kuaishou note from PowerShell" `
  --tags "cli,note" `
  --headless
