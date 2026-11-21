"""微信公众号后台页面入口与表单约束。

微信公众号的 token 是登录会话级参数，每次登录都会变化，因此不作为账号绑定
依据；账号绑定只使用昵称。发布时每次重新访问后台首页，从跳转后的 URL 读取
当前 token 再构造图文编辑地址。
"""
from datetime import timedelta, timezone


WECHAT_HOME_URL = "https://mp.weixin.qq.com/"
WECHAT_HOME_PATH = "/cgi-bin/home"
WECHAT_ARTICLE_PATH = "/cgi-bin/appmsg"

WECHAT_TIMEZONE = timezone(timedelta(hours=8), "Asia/Shanghai")

WECHAT_ARTICLE_TITLE_MAX = 64
WECHAT_DIGEST_MAX = 120
WECHAT_AUTHOR_MAX = 8

WECHAT_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")

# 登录页特征：未登录访问后台首页会被重定向到根路径并显示扫码框。
WECHAT_LOGIN_HINTS = ("login", "scanlogin", "cgi-bin/loginpage")

# 创作来源声明的可选提交值。创作声明必须由作者按实际内容选择，CLI 只做传递。
WECHAT_ORIGINALITY = ("none", "original")
