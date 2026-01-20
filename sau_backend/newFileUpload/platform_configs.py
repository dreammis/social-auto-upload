# 平台配置字典
PLATFORM_CONFIGS = {
    "xiaohongshu": {
        #平台类型编号
        "type": 1,
        #平台名称
        "platform_name": "xiaohongshu",
        #平台个人中心URL
        "personal_url": "https://creator.xiaohongshu.com/new/home",
        #平台登录URL
        "login_url": "https://creator.xiaohongshu.com/login",
        #平台视频发布URL
        "creator_video_url": "https://creator.xiaohongshu.com/publish/publish?from=homepage&target=video&openFilePicker=true",
        #平台图片发布URL
        "creator_image_url": "https://creator.xiaohongshu.com/publish/publish?from=homepage&target=image&openFilePicker=true",
        "selectors": {
            #上传按钮选择器
            "upload_button": ['input.upload-input[type="file"]'],
            #发布按钮选择器
            "publish_button": ['div.d-button-content span.d-text:has-text("发布")'],
            #标题编辑器选择器
            "title_editor": [
                'input.d-text[type="text"][placeholder*="填写标题"]',
                '[contenteditable="true"][role="textbox"][data-lexical-editor="true"]',
                '[aria-placeholder*="分享你的新鲜事"][contenteditable="true"]',
                '[aria-label="Add a description"]',
                '[aria-label="Write something..."]'
            ],
            #正文编辑器输入框选择器
            "textbox_selectors": [
                'div.tiptap.ProseMirror[contenteditable="true"][role="textbox"]'
            ],
            #封面按钮选择器
            "thumbnail_button": ["//span[contains(text(), 'Add')]", "//span[contains(text(), '添加')]"],
            #封面确认按钮选择器
            "thumbnail_finish": ['button.cheetah-btn.cheetah-btn-primary.cheetah-btn-solid:has-text("确定")'],
            #定时按钮选择器
            "schedule_button": ["//span[text()='Schedule']", "//span[text()='定时']"],
            #日期输入选择器
            "date_input": '[aria-label="Date"]',
            #时间输入选择器
            "time_input": '[aria-label="Time"]',
        },
        "features": {
            # 平台功能支持
            #是否跳过Cookie验证
            "skip_cookie_verify": True,
            #是否支持图文发布
            "image_publish": True,
            #是否支持标题
            "title": True,
            #是否支持正文
            "textbox": True,
            #是否支持标签
            "tags": True,
            #是否支持封面
            "thumbnail": False,
            #是否支持地点
            "location": False,
            #是否支持定时发布
            "schedule": False
        }
    },
    "tencent": {
        "type": 2,
        "platform_name": "tencent",
        "personal_url": "https://channels.weixin.qq.com/platform/",
        "login_url": "https://channels.weixin.qq.com/login.html",
        "creator_video_url": "https://channels.weixin.qq.com/platform/post/create",
        "creator_image_url": "https://channels.weixin.qq.com/platform/post/finderNewLifeCreate",
        "selectors": {
            "upload_button": [
                'span.add-icon.weui-icon-outlined-add',
                'div.upload-content',
                '#container-wrap > div.container-center > div > div.main-body-wrap > div.main-body > div.weui-desktop-block.main-card > div > div > div > div:nth-child(2) > div.feed-list-opt > div.video-btn-wrap > div > button',
                'xpath=/html/body/div[1]/div/div[2]/div[2]/div/wujie-app//html/body/div/div/div/div[2]/div/div[1]/div[2]/div[2]/div/div/div/div[2]/div[1]/div[2]/div/button',
                'button.weui-desktop-btn.weui-desktop-btn_primary:has-text("发表视频")'
            ],
            "publish_button": ['button.weui-desktop-btn.weui-desktop-btn_primary:has-text("发表")', 'button.weui-desktop-btn:has-text("发表")'],
            "title_editor": ['input.weui-desktop-form__input[placeholder="概括视频主要内容，字数建议6-16个字符"]'],
            "textbox_selectors": [
                'div.input-editor[contenteditable=""][data-placeholder="添加描述"]'
            ],
            "thumbnail_button": ["//span[contains(text(), '添加封面')]"],
            "thumbnail_finish": ['button.cheetah-btn.cheetah-btn-primary.cheetah-btn-solid:has-text("确定")'],
            "schedule_button": ['label:has-text("定时")'],
            "date_input": ['input[placeholder="请选择发表时间"]'],
            "time_input": ['input[placeholder="请选择时间"]'],
        },
        "features": {
            # 平台功能支持
            #是否跳过Cookie验证
            "skip_cookie_verify": True,
            #是否支持图文发布
            "image_publish": True,
            #是否支持标题
            "title": False,
            #是否支持正文
            "textbox": True,
            #是否支持标签
            "tags": True,
            #是否支持封面
            "thumbnail": False,
            #是否支持地点
            "location": False,
            #是否支持定时发布
            "schedule": False
        }
    },
    "douyin": {
        "type": 3,
        "platform_name": "douyin",
        "personal_url": "https://creator.douyin.com/creator-micro/home",
        "login_url": "https://creator.douyin.com/login",
        "creator_video_url": "https://creator.douyin.com/creator-micro/content/upload",
        "creator_image_url": "https://creator.douyin.com/creator-micro/content/upload?default-tab=3",
        "selectors": {
            "upload_button": ['span.semi-button-content-right:has-text("上传视频")', 'span.semi-button-content-right:has-text("上传图文")'],
            "publish_button": ['role=button[name="发布"]', 'button:has-text("发布"):not(:has-text("高清发布"))', 'text="发布"'],
            "title_editor": ['input[placeholder="填写作品标题，为作品获得更多流量"]', 'input.semi-input.semi-input-default'],
            "textbox_selectors": ['div[data-line-wrapper="true"]', 'div.zone-container.editor-kit-container.editor.editor-comp-publish[contenteditable="true"]'],
            "thumbnail_button": ["//span[contains(text(), '添加封面')]"],
            "thumbnail_finish": ['button.semi-button-content-right:has-text("完成")'],
            "schedule_button": ['button:has-text("定时发布")'],
            "date_input": ['.el-input__inner[placeholder="选择日期和时间"]'],
            "time_input": ['.el-input__inner[placeholder="选择日期和时间"]'],
        },
        "features": {
            # 平台功能支持
            #是否跳过Cookie验证
            "skip_cookie_verify": True,
            #是否支持图文发布
            "image_publish": True,
            #是否支持标题
            "title": True,
            #是否支持正文
            "textbox": True,
            #是否支持标签
            "tags": True,
            #是否支持封面
            "thumbnail": False,
            #是否支持地点
            "location": False,
            #是否支持定时发布
            "schedule": False
        }
    },
    "kuaishou": {
        "type": 4,
        "platform_name": "kuaishou",
        "personal_url": "https://cp.kuaishou.com/profile",
        "login_url": "https://passport.kuaishou.com/pc/account/login",
        "creator_video_url": "https://cp.kuaishou.com/article/publish/video?tabType=1",
        "creator_image_url": "https://cp.kuaishou.com/article/publish/video?tabType=2",
        "selectors": {
            "upload_button": ['button:has-text("上传图片")', 'button:has-text("上传视频")'],
            "publish_button": ['div._button_3a3lq_1._button-primary_3a3lq_60:has-text("发布")', 'div:has-text("发布")', 'text="发布"'],
            #标题编辑器选择器
            "title_editor": ['div:has-text("描述") + div'],
            #正文编辑器输入框选择器
            "textbox_selectors": [
                'div#work-description-edit',
                'div#work-description-edit[contenteditable="true"]',
                'div#work-description-edit[contenteditable="true"][placeholder="添加合适的话题和描述，作品能获得更多推荐～"]',
                'div.tiptap.ProseMirror[contenteditable="true"][role="textbox"]',
                '[contenteditable="true"][placeholder*="添加合适的话题和描述"]',
            ],
            "thumbnail_button": ["//span[contains(text(), '封面编辑')]"],
            "thumbnail_finish": ['button:has-text("完成")'],
            "schedule_button": ['label:text("发布时间") + div .ant-radio-input'],
            "date_input": ['div.ant-picker-input input[placeholder="选择日期时间"]'],
            "time_input": ['div.ant-picker-input input[placeholder="选择日期时间"]'],
        },
        "features": {
            # 平台功能支持
            #是否跳过Cookie验证
            "skip_cookie_verify": True,
            #是否支持图文发布
            "image_publish": True,
            #是否支持标题
            "title": False,
            #是否支持正文
            "textbox": True,
            #是否支持标签
            "tags": True,
            #是否支持封面
            "thumbnail": False,
            #是否支持地点
            "location": False,
            #是否支持定时发布
            "schedule": False
        }
    },
    "tiktok": {
        "type": 5,
        "platform_name": "tiktok",
        "personal_url": "https://www.tiktok.com/setting",
        "login_url": "https://www.tiktok.com/login?lang=en",
        "creator_video_url": "https://www.tiktok.com/tiktokstudio/upload?lang=en",
        "creator_image_url": "https://www.tiktok.com/tiktokstudio/upload?lang=en",
        "selectors": {
            "upload_button": ['button:has-text("Select video"):visible'],
            "publish_button": ['button[data-e2e="post_video_button"]', 'button:has-text("Post")', 'role=button[name="Post"]'],
            "title_editor": ['div.public-DraftEditor-content'],
            "textbox_selectors": [
                'div.public-DraftEditor-content[contenteditable="true"]',
                'div.caption-editor'
            ],
            "thumbnail_button": [".cover-container"],
            "thumbnail_finish": ['button:has-text("Done")'],
            "schedule_button": ["//span[text()='Schedule']", "//span[text()='定时']"],
            "date_input": '[aria-label="Date"]',
            "time_input": '[aria-label="Time"]',
        },
        "features": {
            # 平台功能支持
            #是否跳过Cookie验证
            "skip_cookie_verify": True,
            #是否支持图文发布
            "image_publish": False,
            #是否支持标题
            "title": False,
            #是否支持正文
            "textbox": True,
            #是否支持标签
            "tags": True,
            #是否支持封面
            "thumbnail": False,
            #是否支持地点
            "location": False,
            #是否支持定时发布
            "schedule": False
        }
    },
    "instagram": {
        "type": 6,
        "platform_name": "instagram",
        "personal_url": "https://www.instagram.com",
        "login_url": "https://www.instagram.com/accounts/login/",
        "creator_video_url": "https://business.facebook.com/latest/composer/",
        "creator_image_url": "https://business.facebook.com/latest/composer/",
        "selectors": {
            "upload_button": [
                'div[role="button"]:has-text("Add photo/video")',
                '#mount_0_0_1o > div > div:nth-child(1) > div > div.x9f619.x1n2onr6.x1ja2u2z > div > div > div.x78zum5.xdt5ytf.x10cihs4.x1t2pt76.x1n2onr6.x1ja2u2z > span > div > div > div._6g3g.x1ja2u2z.xeuugli.xh8yej3.x1q85c4o.x1kgee58 > div.x2atdfe.xb57i2i.x1q594ok.x5lxg6s.x78zum5.xdt5ytf.x1n2onr6.x1ja2u2z.xw2csxc.x7p5m3t.x1odjw0f.x1e4zzel.x5yr21d > div > div:nth-child(2) > div > div:nth-child(1) > div > div > div > div > div > div:nth-child(2) > div > div > div.x78zum5.xdt5ytf.x2lwn1j.xeuugli.x1c4vz4f.x2lah0s.x1g14t1j > div.x78zum5.xdt5ytf.x2lwn1j.xeuugli.x14rvwrp.x1nn3v0j.x18d9i69.xyiysdx.xv54qhq.x1odjw0f.x6ikm8r.x5yr21d > div:nth-child(2) > div > div.x9f619.x78zum5.x1iyjqo2.x5yr21d.x2lwn1j.x1n2onr6.xh8yej3 > div.xw2csxc.x1odjw0f.xh8yej3.x18d9i69 > div.x1iyjqo2.xs83m0k.xdl72j9.x3igimt.xedcshv.x1t2pt76.x1l90r2v.xf7dkkf.xv54qhq.xexx8yu > div.x6s0dn4.x78zum5.x1q0g3np.x1a02dak.x2lwn1j.xeuugli.x1iyjqo2.xbiq8gi > div > div > div > div > span > div > div > div.x1vvvo52.x1fvot60.xk50ysn.xxio538.x1heor9g.xuxw1ft.x6ikm8r.x10wlt62.xlyipyv.x1h4wwuj.xeuugli'
            ],
            "publish_button": ['*[role="button"]:has(:text("Publish"))'],
            "title_editor": [
                'div[role="combobox"][contenteditable="true"][aria-label*="Write into the dialogue box"]'
                ],
            #正文编辑器输入框选择器
            "textbox_selectors": [
                'div.tiptap.ProseMirror[contenteditable="true"][role="textbox"]',
                '#mount_0_0_Wk > div > div:nth-child(1) > div > div.x9f619.x1n2onr6.x1ja2u2z > div > div > div.x78zum5.xdt5ytf.x10cihs4.x1t2pt76.x1n2onr6.x1ja2u2z > span > div > div > div._6g3g.x1ja2u2z.xeuugli.xh8yej3.x1q85c4o.x1kgee58 > div.x2atdfe.xb57i2i.x1q594ok.x5lxg6s.x78zum5.xdt5ytf.x1n2onr6.x1ja2u2z.xw2csxc.x7p5m3t.x1odjw0f.x1e4zzel.x5yr21d > div > div:nth-child(2) > div > div:nth-child(1) > div > div > div > div > div > div:nth-child(2) > div > div > div.x78zum5.xdt5ytf.x2lwn1j.xeuugli.x1c4vz4f.x2lah0s.x1g14t1j > div.x78zum5.xdt5ytf.x2lwn1j.xeuugli.x14rvwrp.x1nn3v0j.x18d9i69.xyiysdx.xv54qhq.x1odjw0f.x6ikm8r.x5yr21d > div:nth-child(5) > div > div.x9f619.x78zum5.x1iyjqo2.x5yr21d.x2lwn1j.x1n2onr6.xh8yej3 > div.xw2csxc.x1odjw0f.xh8yej3.x18d9i69 > div.x1iyjqo2.xs83m0k.xdl72j9.x3igimt.xedcshv.x1t2pt76.x1l90r2v.xf7dkkf.xv54qhq.xexx8yu > div.xwya9rg > div > div > div.x6s0dn4.x78zum5.x2lwn1j.xeuugli > div > div > div > div.x6s0dn4.x78zum5.x13fuv20.x18b5jzi.x1q0q8m5.x1t7ytsu.x178xt8z.x1lun4ml.xso031l.xpilrb4.xwebqov.x1x9jw1y.xrsgblv.xceihxd.xjwep3j.x1t39747.x1wcsgtt.x1pczhz8.x1gzqxud.xbsr9hj.xm7lytj.x1ykpatu.x1iwz3mf.x1kukv79.x15x72sd > div.x6s0dn4.x78zum5.x1q0g3np.xozqiw3.x2lwn1j.xeuugli.x1iyjqo2.x8va1my > div > div > div > div.xjbqb8w.x972fbf.x10w94by.x1qhh985.x14e42zd.xdj266r.x14z9mp.xat24cr.x1lziwak.x1t137rt.xexx8yu.xyri2b.x18d9i69.x1c1uobl.xlyipyv.xwd1esu.x1gnnqk1.xbsr9hj.x1urst0s.x1glnyev.x1ad04t7.x1ix68h3.x19gujb8.xni1clt.x1tutvks.xfrpkgu.x1vvvo52.x1fvot60.xo1l8bm.xxio538.xh8yej3.xl8z2ie.x1ujl9rh.xw2csxc.x1odjw0f.xjbqb8w.x972fbf.x10w94by.x1qhh985.x14e42zd.xdj266r.x14z9mp.xat24cr.x1lziwak.x1t137rt.xexx8yu.xyri2b.x18d9i69.x1c1uobl.xlyipyv.xwd1esu.x1gnnqk1.xbsr9hj.x1urst0s.x1glnyev.x1ad04t7.x1ix68h3.x19gujb8.xni1clt.x1tutvks.xfrpkgu.x1vvvo52.x1fvot60.xo1l8bm.xxio538.xh8yej3.xl8z2ie.x1ujl9rh.xw2csxc.x1odjw0f',
                'xpath=/html/body/div[2]/div/div[1]/div/div[2]/div/div/div[1]/span/div/div/div[1]/div[1]/div/div[2]/div/div[1]/div/div/div/div/div/div[2]/div/div/div[1]/div[1]/div[5]/div/div[2]/div[1]/div[2]/div[2]/div/div/div[2]/div/div/div/div[1]/div[3]/div/div/div/div[1]',
                'div._5yk2 > div._5rp7 > div._5rpb > div[contenteditable="true"][role="combobox"][aria-label*="Write into the dialogue box"]'
            ],
            "thumbnail_button": ["//span[contains(text(), '选择封面')]"],
            "thumbnail_finish": ['button:has-text("完成")'],
            "schedule_button": ['#video_upload > div > div:nth-child(2) > div > div.time > div > div > div:nth-child(2) > label'],
            "date_input": ['#video_upload > div > div:nth-child(2) > div > div.time > div > div > div:nth-child(2) > div > input'],
            "time_input": ['#video_upload > div > div:nth-child(2) > div > div.time > div > div > div:nth-child(2) > div > input'],
        },
        "features": {
            # 平台功能支持
            #是否跳过Cookie验证
            "skip_cookie_verify": True,
            #是否支持图文发布
            "image_publish": True,
            #是否支持标题
            "title": False,
            #是否支持正文
            "textbox": True,
            #是否支持标签
            "tags": True,
            #是否支持封面
            "thumbnail": False,
            #是否支持地点
            "location": False,
            #是否支持定时发布
            "schedule": False
        }
    },
    #facebook
    "facebook": {
        "type": 7,
        "platform_name": "facebook",
        "personal_url": "https://www.facebook.com/profile.php",
        "login_url": "https://www.facebook.com/login",
        "creator_video_url": "https://www.facebook.com/",
        "creator_image_url": "https://www.facebook.com/",
        "selectors": {
            "upload_button": ['div[aria-label="照片/视频"]','div[aria-label="Photo/Video"]'],
            "publish_button": ['//span[text()="发帖"]','//span[text()="Post"]','//span[text()="Schedule"]','//span[text()="发布"]'],
            #标题编辑器选择器
            "title_editor": [
                # 中文界面选择器
                '[contenteditable="true"][role="textbox"][data-lexical-editor="true"]',
                '[aria-placeholder*="分享你的新鲜事"][contenteditable="true"]',
                # 英文界面选择器
                '[aria-label="Add a description"]',
                '[aria-label="Write something..."]'],
            #正文编辑器输入框选择器
            "textbox_selectors": [
                'div.tiptap.ProseMirror[contenteditable="true"][role="textbox"]'
            ],
            "thumbnail_button": ["//span[contains(text(), 'Add')]","//span[contains(text(), '添加')]"],
            "thumbnail_finish": ['button:has-text("完成")'],
            "schedule_button": ["//span[text()='Schedule']","//span[text()='定时']"],
            "date_input": ['.date-picker-input'],
            "time_input": ['.time-picker-input'],
        },
        "features": {
            # 平台功能支持
            #是否跳过Cookie验证
            "skip_cookie_verify": True,
            #是否支持图文发布
            "image_publish": True,
            #是否支持标题
            "title": True,
            #是否支持正文
            "textbox": False,
            #是否支持标签
            "tags": True,
            #是否支持封面
            "thumbnail": False,
            #是否支持地点
            "location": False,
            #是否支持定时发布
            "schedule": False
        }
    },
    "bilibili": {
        "type": 8,
        "platform_name": "bilibili",
        "personal_url": "https://member.bilibili.com/platform/home",
        "login_url": "https://passport.bilibili.com/login",
        "creator_video_url": "https://member.bilibili.com/platform/upload/video/frame?page_from=creative_home_top_upload",
        "creator_image_url": "https://member.bilibili.com/platform/upload/video/frame",
        "selectors": {
            "upload_button": ['#video-up-app > div.video-entrance > div.upload-body > div > div.upload-wrp > div > div > div','#video-up-app > div.video-complete > div.content-wrapper > div > div.op-buttons > button > span'],
            "publish_button": ['span.submit-add:has-text("立即投稿")'],
            #标题编辑器选择器
            "title_editor": ['input.input-val[type="text"][placeholder="请输入稿件标题"]'],
            #正文编辑器输入框选择器
            "textbox_selectors": [
                'div.ql-editor.ql-blank[contenteditable="true"][data-placeholder="填写更全面的相关信息，让更多的人能找到你的视频吧"]'
            ],
            "thumbnail_button": ["//span[contains(text(), '添加封面')]"],
            "thumbnail_finish": ['button:has-text("完成")'],
            "schedule_button": ['button:has-text("定时发布")'],
            "date_input": ['.date-picker-input'],
            "time_input": ['.time-picker-input'],
        },
        "features": {
            # 平台功能支持
            #是否跳过Cookie验证
            "skip_cookie_verify": True,
            #是否支持图文发布
            "image_publish": True,
            #是否支持标题
            "title": True,
            #是否支持正文
            "textbox": True,
            #是否支持标签
            "tags": True,
            #是否支持封面
            "thumbnail": False,
            #是否支持地点
            "location": False,
            #是否支持定时发布
            "schedule": False
        }
    },
    #baijiahao
    "baijiahao": {
        "type": 9,
        "platform_name": "baijiahao",
        "personal_url": "https://baijiahao.baidu.com/builder/rc/home",
        "login_url": "https://baijiahao.baidu.com/builder/theme/bjh/login",
        "creator_video_url": "https://baijiahao.baidu.com/builder/rc/edit?type=videoV2&is_from_cms=1",
        "creator_image_url": "https://baijiahao.baidu.com/builder/rc/edit?type=news&is_from_cms=1",
        "selectors": {
            "upload_button": [
                'div._5eb0d99a7a8a2180-uploadEventContainer',
                '#root > div > div.mp-container.mp-container-edit > div > div.scale-box > div > div > div > section > div > div.video-main-container > div.e844194154160364-blankWrap > div > div._5eb0d99a7a8a2180-inputWrap > div',
                'xpath=/html/body/div/div/div[1]/div/div[2]/div/div/div/section/div/div[1]/div[1]/div/div[2]/div'
                ],
            "publish_button": [
                '#new-operator-content > div > span > span.op-list-right > div:nth-child(3) > button',
                'xpath=/html/body/div[1]/div/div[1]/div/div[2]/div/div/div/div[3]/div/span/span[2]/div[3]/button'
                ],
            #标题编辑器选择器
            "title_editor": [
                '#formMain > form > div.left-area-content-box > div:nth-child(2) > div.form-inner-wrap.tags-container.videov2-title-wrap > div > div.cheetah-public.cheetah-textArea.acss-zwcv9m.autoSize > textarea',
                'xpath=/html/body/div/div/div[1]/div/div[2]/div/div/div/div[2]/div/form/div[1]/div[2]/div[2]/div/div[1]/textarea'
                ],
            #正文编辑器输入框选择器
            "textbox_selectors": [
                '#desc',
                'xpath=/html/body/div/div/div[1]/div/div[2]/div/div/div/div[2]/div/form/div[1]/div[11]/div[2]/div[2]/div/textarea'
            ],
            "thumbnail_button": [
                "#formMain > form > div.left-area-content-box > div.form-item-line-content-24.form-item-line-content-cover.form-cover > div.form-inner-wrap > div.d01689d7d733c6fb-coverWrap > div:nth-child(1) > div > span > div > span > div > div > div > div > div.d820b38cbcd0c526-icon",
                'xpath=/html/body/div[1]/div/div[1]/div/div[2]/div/div/div/div[2]/div/form/div[1]/div[1]/div[2]/div[1]/div[1]/div/span/div/span/div/div/div/div'
            ],
            "thumbnail_finish": [
                '#rc-tabs-0-panel-1 > div > div._37e9eeb539c7e75d-footer > button.cheetah-btn.css-zneqgo.cheetah-btn-primary.cheetah-btn-solid.cheetah-public.acss-qlkyg1.acss-1kjo6pu.acss-1tjgk22.acss-yhl6pe.acss-uv0qn4.acss-58e25w.acss-1grxnxm.acss-1izrri0.cheetah-btn-L.cheetah-btn-text-primary',
                'xpath=/html/body/div[2]/div/div[2]/div/div[1]/div/div/div/div[2]/div/div/div/div[2]/button[2]',
                'button.cheetah-btn.cheetah-btn-primary.cheetah-btn-solid:has-text("确定")'
            ],
            "schedule_button": ['button:has-text("定时发布")'],
            "date_input": ['.date-picker-input'],
            "time_input": ['.time-picker-input'],
        },
        "features": {
            # 平台功能支持
            #是否跳过Cookie验证
            "skip_cookie_verify": True,
            #是否支持图文发布
            "image_publish": True,
            #是否支持标题
            "title": True,
            #是否支持正文
            "textbox": True,
            #是否支持标签
            "tags": True,
            #是否支持封面
            "thumbnail": True,
            #是否支持地点
            "location": False,
            #是否支持定时发布
            "schedule": False
        }
    }
}

# 导出配置以便其他模块导入
__all__ = ['PLATFORM_CONFIGS', 'get_platform_key_by_type', 'get_type_by_platform_key']


def get_platform_key_by_type(type):
    """
    通过平台类型编号查找平台key
    :param type: 平台类型编号
    :return: 平台key，如果没有找到则返回None
    """
    for platform_key, config in PLATFORM_CONFIGS.items():
        if config['type'] == type:
            return platform_key
    return None


def get_type_by_platform_key(platform_key):
    """
    通过平台key查找平台类型编号
    :param platform_key: 平台key
    :return: 平台类型编号，如果没有找到则返回None
    """
    config = PLATFORM_CONFIGS.get(platform_key)
    if config:
        return config['type']
    return None