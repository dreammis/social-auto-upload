## 启动项目：
python 版本：3.10
1. 安装依赖
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
2. 删除 db 目录下 database.db（如果没有直接运行createTable.py即可），运行 createTable.py 重新建库，避免出现脏数据
3. 修改 conf.py最下方 LOCAL_CHROME_PATH 为本地 chrome 浏览器地址
4. 运行根目录的 sau_backend.py
5. type字段（平台标识） 1 小红书 2 视频号 3 抖音 4 快手
## 接口说明
1. /upload post
    上传接口，上传成功会返回文件的唯一id，后期靠这个发布视频
2. /login id参数 用户名 type参数 平台标识：登录流程，前端和后端建立sse连接，后端获取到图片base64编码后返回给前端，前端接受扫码后后端存库后返回200，前端主动断开连接，然后调取/getValidAccounts获取当前所有可用账号
3. /getValidAccounts 会获取当前所有可用cookie，时间较慢，会逐个校验cookie，status 1 有效 0 无效cookie
4. /postVideo 发布视频接口 post json传参
    file_list      /upload获取的文件唯一标识
    account_list   /getValidAccounts获取的filePath字段
    type           类型字段（平台标识）
    title          视频标题
    tags           视频tag 列表，不带#
    category       原作者说是原创表示，0表示不是原创其他表示为原创，但测试该字段没有效果
    enableTimer    是否开启定时发布，默认关闭，开启传True，如果开启，下面三个必传，否则不传
    videos_per_day 每天发布几个视频
    daily_times    每天发布视频的时间，整形列表，与上面列表长度保持一致
    start_days     开始天数，0 代表明天开始定时发布 1 代表明天的明天
    以上三个字段是我的理解，不知道对不对，也不知道原作者为什么要这么设置
## 数据库说明
见当前目录下 db目录，py文件是创建脚本，db文件是sqlite数据库
## 文件说明
cookiesFile文件夹 存储cookie文件
myUtils文件夹 存储自己封装的python模块
videoFile文件夹 文件上传存放位置
web 文件夹 web路由目录
conf.py 全局配置，记得修改配置中 LOCAL_CHROME_PATH 为本机浏览器地址