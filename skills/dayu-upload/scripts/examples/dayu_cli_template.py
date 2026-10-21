from subprocess import run

commands = [['sau', 'dayu', 'login', '--account', 'account_a'], ['sau', 'dayu', 'check', '--account', 'account_a'], ['sau', 'dayu', 'upload-video', '--account', 'account_a', '--file', 'videos/demo.mp4', '--title', 'DayuTitle', '--category', 'Tech', '--source', 'None', '--thumbnail', 'videos/demo.png'], ['sau', 'dayu', 'upload-article', '--account', 'account_a', '--title', 'ArticleTitle', '--content-file', 'articles/demo.md', '--source', 'None']]

for command in commands:
    run(command, check=True)
