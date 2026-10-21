from subprocess import run

commands = [['sau', 'xueqiu', 'login', '--account', 'account_a'], ['sau', 'xueqiu', 'check', '--account', 'account_a'], ['sau', 'xueqiu', 'upload-article', '--account', 'account_a', '--title', 'ArticleTitle', '--content-file', 'articles/demo.md', '--declaration', 'NoDeclaration']]

for command in commands:
    run(command, check=True)
