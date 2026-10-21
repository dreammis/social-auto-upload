from subprocess import run

commands = [['sau', 'facebook-page', 'login', '--account', 'account_a'], ['sau', 'facebook-page', 'check', '--account', 'account_a'], ['sau', 'facebook-page', 'upload-video', '--account', 'account_a', '--page', 'MyPage', '--file', 'videos/demo.mp4', '--title', 'VideoTitle', '--desc', 'Description'], ['sau', 'facebook-page', 'upload-note', '--account', 'account_a', '--page', 'MyPage', '--images', 'images/1.jpg', '--title', 'NoteTitle', '--note', 'Text']]

for command in commands:
    run(command, check=True)
