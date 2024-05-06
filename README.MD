# social-auto-upload
social-auto-upload 该项目旨在自动化发布视频到各个社交媒体平台

social-auto-upload This project aims to automate the posting of videos to various social media platforms.

<img src="media/show/tkupload.gif" alt="tiktok show" width="800"/>

## 💡Feature
- 中国主流社交媒体平台：
  - [x] 抖音
  - [x] 视频号
  - [x] bilibili
  - [x] 小红书
  - [ ] 快手

- 部分国外社交媒体：
  - [x] tiktok
  - [ ] youtube
- [ ] 自动化上传(schedule)
- [x] 定时上传(cron)
- [ ] cookie 管理
- [ ] 国外平台proxy 设置
- [ ] 多线程上传
- [ ] slack 推送


# 💾Installation
```
pip install -r requirements.txt
playwright install chromium firefox
```

# 🐇 About
The project for my own project extracted, my release strategy is timed release (released a day in advance), so the release part of the event are used for the next day time!

If you need to release it immediately, you can study the source code or ask me questions.

该项目为我自用项目抽离出来，我的发布策略是定时发布（提前一天发布），故发布部分采用的事件均为第二天的时间

如果你有需求立即发布，可自行研究源码或者向我提问


# 核心模块解释

### 1. 视频文件准备(video prepare)
filepath 本地视频目录，目录包含(filepath Local video directory containing)

- 视频文件(video files)
- 视频meta信息txt文件(video meta information txt file)

举例(for example)：

file：2023-08-24_16-29-52 - 这位勇敢的男子为了心爱之人每天坚守 .mp4

meta_file:2023-08-24_16-29-52 - 这位勇敢的男子为了心爱之人每天坚守 .txt

meta_file 内容(content)：
```angular2html
这位勇敢的男子为了心爱之人每天坚守 🥺❤️‍🩹
#坚持不懈 #爱情执着 #奋斗使者 #短视频
```
---

### 2. 抖音
<img src="media/show/pdf3.gif" alt="douyin show" width="500"/>

使用playwright模拟浏览器行为
> 抖音前端实现，诸多css class id 均为随机数，故项目中locator多采用相对定位，而非固定定位
1. 准备视频目录结构
2. cookie获取：get_douyin_cookie.py 扫码登录
3. 上传视频：upload_video_to_douyin.py 



其他部分解释：
```
douyin_setup handle 参数为True，为手动获取cookie False 则是校验cookie有效性

generate_schedule_time_next_day 默认从第二天开始（此举为避免选择时间的意外错误）
参数解释：
- total_videos 本次上传视频个数
- videos_per_day 每日上传视频数量
- daily_times 视频发布时间 默认6、11、14、16、22点
- start_days 从第N天开始
```

> 2023年12月15日补充：使用chromium可能会出现无法识别视频封面图片的情况
> 解决方案：
> 1. 下载chrome
> 2. 找到chrome的安装目录
> 3. 将目录配置到DouYinVideo类中  self.local_executable_path = "xxx/xxx/chrome.exe"


参考项目：
- https://github.com/wanghaisheng/tiktoka-studio-uploader
- https://github.com/Superheroff/douyin_uplod
- https://github.com/lishang520/DouYin-Auto-Upload.git

---

### 3. 视频号
使用playwright模拟浏览器行为
1. 准备视频目录结构
2. cookie获取：get_tencent_cookie.py 扫码登录
3. 上传视频：upload_video_to_tencent.py 



其他部分解释：
```
参考上面douyin_setup 配置
```

> 视频号使用chromium会出现不支持上传视频，需要自行指定本地浏览器
> 解决方案：
> 1. 下载chrome
> 2. 找到chrome的安装目录
> 3. 将目录配置到TencentVideo类中  self.local_executable_path = "xxx/xxx/chrome.exe"

---


### 4. 小红书
该实现，借助ReaJason的[xhs](https://github.com/ReaJason/xhs)，再次感谢。

1. 目录结构同上
2. cookie获取，可使用chrome插件：EditThisCookie
- 设置导出格式
![Alt text](media/20231009111131.png)
- 导出
![Alt text](media/20231009111214.png)
3. 黏贴至 accounts.ini文件中


#### 解释与注意事项：

```
xhs签名方式分为两种：
- 本地签名 sign_locl （默认）
- 自建签名服务 sign

测试下来发现本地签名，在实际多账号情况下会存在问题
故如果你有多账号分发，建议采用自建签名服务（todo 上传docker配置）
```
##### 疑难杂症
遇到签名问题，可尝试更新cdn.jsdelivr.net_gh_requireCool_stealth.min.js_stealth.min.js文件
https://github.com/requireCool/stealth.min.js

24.4.10 大多数人小红书失败的原因在于你的cookie有问题，请参照你cookie是不是如我这样
![正确的cookie](media/xhs_error_cookie.png)

关于xhs部分可参考作者： https://reajason.github.io/xhs/basic

##### todo
- 扫码登录方式（实验下来发现与浏览器获取的存在区别，会有问题，未来再研究）


参考项目：
- https://github.com/ReaJason/xhs

---

### 5. bilibili
该实现，借助biliup的[biliup-rs](https://github.com/biliup/biliup-rs)，再次感谢。
1. 准备视频目录结构
2. cookie获取：`biliup.exe -u account.json login` 选项你喜欢的登录方式
![登录方式](media/get_bili_cookie.png) 
3. 上传视频：upload_video_to_bilibili.py

#### 解释与注意事项：

```
bilibili cookie 长期有效（至少我运行2年以来是这样的）
其他平台 诸如linux mac 服务器运行 请自行研究
```
参考项目：
- https://github.com/biliup/biliup-rs

---

### 6. tiktok 
使用playwright模拟浏览器行为(Simulating Browser Behavior with playwright)
1. 准备视频目录结构(Prepare the video directory structure)
2. cookie获取(generate your cookie)：get_tk_cookie.py 
![get tiktok cookie](media/tk_login.png) 
3. 上传视频(upload video)：upload_video_to_tiktok.py



其他部分解释：
```
参考上面douyin_setup 配置
```

other part explain(for eng friends)：
```
tiktok_setup handle parameter is True to get cookie manually False to check cookie validity

generate_schedule_time_next_day defaults to start on the next day (this is to avoid accidental time selection errors)
Parameter explanation:
- total_videos Number of videos uploaded this time
- videos_per_day Number of videos uploaded per day
- daily_times The video posting times are 6, 11, 14, 16, 22 by default.
- start_days Starts on the nth day.
```
参考项目：
- https://github.com/wkaisertexas/tiktok-uploader

---

### 其余部分(todo)
整理后上传

---

## 其他优秀项目
- https://github.com/KLordy/auto_publish_videos
  - db支持
  - 定期自动发布
  - cookie db管理
  - 视频去重
  - 消息推送


## 🐾Communicate
[Donate as u like](https://www.buymeacoffee.com/hysn2001m)

探讨自动化上传、自动制作视频
|![Nas](media/mp.jpg)|![赞赏](media/QR.png)|
|:-:|:-:|
|后台回复 `上传` 加群交流|如果你觉得有用|
