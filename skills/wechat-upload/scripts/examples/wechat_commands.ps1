# 运行前先查看当前 CLI 帮助；发表前请确认内容与群发设置。

sau wechat login --account account_a
sau wechat check --account account_a

# 只填写并核对，不发表（会留下远端草稿）
sau wechat upload-article --account account_a --title "文章标题示例" --content-file articles/demo.md --digest "一句话摘要" --prepare-only

# 真实发表：默认群发通知，原创声明按实际选择
sau wechat upload-article --account account_a --title "文章标题示例" --content-file articles/demo.md --digest "一句话摘要" --cover "封面.png" --originality none
