# 自动化上传视频到社交媒体
包含：抖音、视频号、bilibili、小红书等平台
1. 自动化上传
2. 视频立即发布 or 定时发布
3. 自动填写标题、hashtag等

## install
```pip install -r requeirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple```

## 核心模块解释

### 文件目录结构
filepath 为本地视频目录，目录包含视频文件、视频meta信息txt文件

file：2023-08-24_16-29-52 - 这位勇敢的男子为了心爱之人每天坚守 .mp4

meta_file:2023-08-24_16-29-52 - 这位勇敢的男子为了心爱之人每天坚守 .txt

meta_file 内容：
```angular2html
---Youtube title---
这位勇敢的男子为了心爱之人每天坚守 🥺❤️‍🩹
#坚持不懈 #爱情执着 #奋斗使者 #短视频
```

视频发布规则：
1. 第一条视频立即发送
2. 第二条开始 每日11:00, 16:00定时发布
举例：
filepath 5个视频
第一个视频立即发布，第二个视频在第二天11点发布，第三个视频在第二天16点发布，第四个视频在第三天11点发布....


### bilibili
1. 设置好视频目录结构
2. 替换filepath本地目录（视频目录）
3. 获取bilibili 相应cookie: sessdata, bili_jct, buvid3, dedeuserid, ac_time_value(用于刷新cookie， 见图2)
```javascript
// 获取 cookie 中的值
function getCookie(name) {
    const value = "; " + document.cookie;
    const parts = value.split("; " + name + "=");
    if (parts.length == 2) return parts.pop().split(";").shift();
}

// 获取 localStorage 中的值
function getLocalStorage(name) {
    return localStorage.getItem(name);
}

// 获取所需的值
const values = {
    sessdata: '加密信息, 请通过浏览器获取',
    bili_jct: getCookie('bili_jct'),
    buvid3: getCookie('buvid3'),
    dedeuserid: getCookie('dedeuserid'),
    ac_time_value: getLocalStorage('ac_time_value')
};

// 输出值
console.log(values);

```

4. 拉取子仓库 `git submodule add https://github.com/Nemo2011/bilibili-api.git bilibili_uploader/bilibili_api`

![Alt text](media/e0df568f16d6447c8a66f672ba37af2f.jpg)
![Alt text](media/2023-10-09_105553.png)

其他部分解释：
```angular2html
random_emoji() 标题后增加随机emoji，避免出错后抛出相同标题不允许上传
time.sleep(30) 
为什么没使用pypi包，因为有个bug，仓库代码修改了但是pypi并没有更新
分区可以在VideoZoneTypes 文件获取
```
todo:
- [ ] tid 分区id指定
- [ ] 多账号cookie管理 https://nemo2011.github.io/bilibili-api/#/refresh_cookies
- [ ] cookie 失效预警

参考项目：
- https://github.com/Nemo2011/bilibili-api
  - api 文档: https://nemo2011.github.io/bilibili-api/#/homepage
  - 分区 文档：https://biliup.github.io/tid-ref.html
- https://github.com/biliup/biliup-rs

### 小红书
1. 目录结构同上
2. cookie获取，可使用chrome插件：EditThisCookie
- 设置导出格式
![Alt text](media/20231009111131.png)
- 导出
![Alt text](media/20231009111214.png)

其他部分解释：
```
遇到签名问题，可尝试更新cdn.jsdelivr.net_gh_requireCool_stealth.min.js_stealth.min.js文件
https://github.com/requireCool/stealth.min.js
参考：
- https://reajason.github.io/xhs/basic
```
todo:
- [ ] 多账号cookie管理
- [ ] cookie 失效预警

参考项目：https://github.com/ReaJason/xhs

### 抖音
1. 目录结构同上
2. cookie获取：运行程序，检测无cookie，弹出浏览器，登录后，关于。将会保存cookie，文件名为account1.json

其他部分解释：
```
laywright.chromium.launch 中的headless可以设置为true，不显示浏览器
```

todo：
- [ ] cookie 失效预警
- [ ] 多账号cookie管理

参考项目：
- https://github.com/wanghaisheng/tiktoka-studio-uploader
- https://github.com/Superheroff/douyin_uplod
- https://github.com/lishang520/DouYin-Auto-Upload.git


### 视频号
1. 目录结构同上
2. cookie获取：运行程序，检测无cookie，弹出浏览器，登录后，关于。将会保存cookie，文件名为account1.json

其他部分解释：
```
laywright.chromium.launch 中的headless可以设置为true，不显示浏览器
chromium 不支持h264编码，需要使用chrome，我这里下载的是Canary
https://www.google.com/intl/en_sg/chrome/canary/

这里设置启动的浏览器地址（你chrome的地址）
browser = await playwright.chromium.launch(headless=False,
                                                   executable_path="C:/Users/dream/AppData/Local/Google/Chrome SxS/Application/chrome.exe")
```

todo：
- [ ] cookie 失效预警
- [ ] 多账号cookie管理


### tiktok
1. 目录结构同上
2. cookie获取：sessionid
3. 设置proxy 代理（最好干净代理，避免封号）
4. url_prefix 设置tiktok区，default: us, The request domain. Different countries require different domain configurations.

proxy = {'socks': 'socks://172.16.22.73:10808'}
url_prefix = "www"
其他部分解释：
```
Note that you cannot schedule a video more than 10 days in advance.
Note that your TikTok sessionid cookie needs to be updated every 2 months.
```



todo：
- [ ] cookie 失效预警
- [ ] 多账号cookie管理

参考项目：https://github.com/546200350/TikTokUploder

