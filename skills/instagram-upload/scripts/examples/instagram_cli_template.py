from subprocess import run

commands = [['sau', 'instagram', 'login', '--account', 'account_a'], ['sau', 'instagram', 'check', '--account', 'account_a'], ['sau', 'instagram', 'upload-video', '--account', 'account_a', '--file', 'videos/demo.mp4', '--title', 'ReelTitle', '--desc', 'Description', '--tags', 'life,share'], ['sau', 'instagram', 'upload-note', '--account', 'account_a', '--images', 'images/1.jpg', 'images/2.jpg', '--title', 'CarouselTitle', '--note', 'Text']]

for command in commands:
    run(command, check=True)
