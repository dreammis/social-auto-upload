import asyncio
import re
from pathlib import Path

from conf import BASE_DIR
from myUtils.screenshot_manager import ScreenshotManager
from uploader.douyin_uploader.main import DouYinVideo
from uploader.ks_uploader.main import KSVideo
from uploader.tencent_uploader.main import TencentVideo
from uploader.xiaohongshu_uploader.main import XiaoHongShuVideo
from uploader.baijiahao_uploader.main import BaiJiaHaoVideo
from uploader.tk_uploader.main import TiktokVideo
from uploader.bilibili_uploader.uploader import BilibiliUploader
from utils.constant import TencentZoneTypes
from utils.files_times import generate_schedule_time_next_day


def resolve_thumbnail_path(thumbnail_path):
    """处理封面路径：支持绝对路径和相对路径
    
    Args:
        thumbnail_path: 封面路径（可以是绝对路径或相对于 videoFile 目录的相对路径）
    
    Returns:
        Path 对象或 None
    """
    if not thumbnail_path:
        return None
    path = Path(thumbnail_path)
    # 如果是绝对路径且文件存在，直接使用
    if path.is_absolute() and path.exists():
        return path
    # 否则作为相对路径处理（相对于 videoFile 目录）
    relative_path = Path(BASE_DIR / "videoFile" / thumbnail_path)
    if relative_path.exists():
        return relative_path
    return None


def post_video_tencent(title, files, tags, account_file, category=TencentZoneTypes.LIFESTYLE.value,
                        enableTimer=False, videos_per_day=1, daily_times=None, start_days=0,
                        is_draft=False, thumbnail_path='', desc='',
                        collection: str | None = None):  # 合集名称
    """视频号视频发布

    Args:
        title: 视频标题
        files: 视频文件列表
        tags: 标签列表
        account_file: 账号文件列表
        category: 原创声明类型
        enableTimer: 是否启用定时发布
        videos_per_day: 每天发布视频数
        daily_times: 每天发布时间点
        start_days: 从今天开始计算的发布天数
        is_draft: 是否保存为草稿
        desc: 视频描述
        thumbnail_path: 封面图片路径
        collection: 合集名称（模糊匹配）
    """
    # 生成文件的完整路径
    account_file = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
    files = [Path(BASE_DIR / "videoFile" / file) for file in files]
    thumbnail = resolve_thumbnail_path(thumbnail_path)
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(len(files), videos_per_day, daily_times, start_days)
    else:
        publish_datetimes = [0 for i in range(len(files))]
    for index, file in enumerate(files):
        for cookie in account_file:
            print(f"文件路径{str(file)}")
            # 打印视频文件名、标题和 hashtag
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"Hashtag：{tags}")
            if desc:
                print(f"描述：{desc[:50]}...")
            if thumbnail:
                print(f"封面：{thumbnail}")
            if collection:
                print(f"合集：{collection}")

            # 创建截图管理器（用于无头模式调试）
            account_name = cookie.stem if hasattr(cookie, 'stem') else str(cookie)
            screenshot_manager = ScreenshotManager(platform="tencent", account=account_name)

            app = TencentVideo(
                title,
                str(file),
                tags,
                publish_datetimes[index],
                cookie,
                category=category,
                is_draft=is_draft,
                desc=desc or None,
                thumbnail_path=str(thumbnail) if thumbnail else None,
                collection=collection,  # 传递合集参数
                screenshot_manager=screenshot_manager,  # 传递截图管理器
            )
            asyncio.run(app.main(), debug=False)


def post_video_DouYin(title,files,tags,account_file,category=TencentZoneTypes.LIFESTYLE.value,enableTimer=False,videos_per_day = 1, daily_times=None,start_days = 0,
                      thumbnail_landscape_path = '',
                      thumbnail_portrait_path = '',
                      productLink = '', productTitle = '', declaration_info = None, desc = '',
                      collection: str | None = None):  # 合集名称
    # 生成文件的完整路径
    account_file = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
    files = [Path(BASE_DIR / "videoFile" / file) for file in files]
    
    print(f"[DEBUG] post_video_DouYin 接收到的封面参数 - thumbnail_landscape_path: '{thumbnail_landscape_path}' (type: {type(thumbnail_landscape_path)}), thumbnail_portrait_path: '{thumbnail_portrait_path}' (type: {type(thumbnail_portrait_path)})")
    
    thumbnail_landscape = resolve_thumbnail_path(thumbnail_landscape_path)
    thumbnail_portrait = resolve_thumbnail_path(thumbnail_portrait_path)
    
    print(f"[DEBUG] resolve_thumbnail_path 处理后 - thumbnail_landscape: {thumbnail_landscape} (type: {type(thumbnail_landscape)}), thumbnail_portrait: {thumbnail_portrait} (type: {type(thumbnail_portrait)})")
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(len(files), videos_per_day, daily_times,start_days)
    else:
        publish_datetimes = [0 for i in range(len(files))]
    for index, file in enumerate(files):
        for cookie in account_file:
            print(f"文件路径{str(file)}")
            # 打印视频文件名、标题和 hashtag
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"Hashtag：{tags}")
            if declaration_info is not None:
                print(f"自主声明：{declaration_info}")
            if collection:
                print(f"合集：{collection}")

            # 创建截图管理器（用于无头模式调试）
            account_name = cookie.stem if hasattr(cookie, 'stem') else str(cookie)
            screenshot_manager = ScreenshotManager(platform="douyin", account=account_name)

            app = DouYinVideo(
                title,
                str(file),
                tags,
                publish_datetimes[index],
                cookie,
                thumbnail_landscape_path=str(thumbnail_landscape) if thumbnail_landscape else None,
                productLink=productLink,
                productTitle=productTitle,
                declaration_info=declaration_info,
                thumbnail_portrait_path=str(thumbnail_portrait) if thumbnail_portrait_path else None,
                desc=desc,
                category=category,
                collection=collection,  # 传递合集参数
                screenshot_manager=screenshot_manager,  # 传递截图管理器
            )
            asyncio.run(app.main())


def post_video_ks(title, files, tags, account_file, category=TencentZoneTypes.LIFESTYLE.value,
                  enableTimer=False, videos_per_day=1, daily_times=None, start_days=0,
                  desc='', thumbnail_path='',
                  kuaishou_declaration='内容为AI生成', allow_duet=True, allow_download=True, show_in_city=True,
                  collection: str | None = None):  # 合集名称
    """快手视频发布

    Args:
        title: 视频标题
        files: 视频文件列表
        tags: 标签列表
        account_file: 账号文件列表
        category: 原创声明类型
        enableTimer: 是否启用定时发布
        videos_per_day: 每天发布视频数
        daily_times: 每天发布时间点
        start_days: 从今天开始计算的发布天数
        desc: 视频描述
        thumbnail_path: 封面图片路径
        kuaishou_declaration: 作者声明类型（默认"内容为AI生成"）
        allow_duet: 允许别人跟我拍同框（默认True）
        allow_download: 允许下载此作品（默认True）
        show_in_city: 作品展示在同城页（默认True）
        collection: 合集名称（模糊匹配）
    """
    # 生成文件的完整路径
    account_file = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
    files = [Path(BASE_DIR / "videoFile" / file) for file in files]
    thumbnail = resolve_thumbnail_path(thumbnail_path)
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(len(files), videos_per_day, daily_times, start_days)
    else:
        publish_datetimes = [0 for i in range(len(files))]
    for index, file in enumerate(files):
        for cookie in account_file:
            print(f"文件路径{str(file)}")
            # 打印视频文件名、标题和 hashtag
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"Hashtag：{tags}")
            if desc:
                print(f"描述：{desc[:50]}...")
            if thumbnail:
                print(f"封面：{thumbnail}")
            if collection:
                print(f"合集：{collection}")

            # 创建截图管理器（用于无头模式调试）
            account_name = cookie.stem if hasattr(cookie, 'stem') else str(cookie)
            screenshot_manager = ScreenshotManager(platform="kuaishou", account=account_name)

            app = KSVideo(
                title,
                str(file),
                tags,
                publish_datetimes[index],
                cookie,
                category=category,
                desc=desc,
                thumbnail_path=str(thumbnail) if thumbnail else None,
                kuaishou_declaration=kuaishou_declaration,
                allow_duet=allow_duet,
                allow_download=allow_download,
                show_in_city=show_in_city,
                collection=collection,  # 传递合集参数
                screenshot_manager=screenshot_manager,  # 传递截图管理器
            )
            asyncio.run(app.main(), debug=False)

def post_video_xhs(title, files, tags, account_file, category=TencentZoneTypes.LIFESTYLE.value,
                   enableTimer=False, videos_per_day=1, daily_times=None, start_days=0,
                   desc='', thumbnail_path='',
                   collection: str | None = None,
                   declaration_info: dict | None = None):  # 声明信息（如AI合成内容声明）
    """小红书视频发布

    Args:
        title: 视频标题
        files: 视频文件列表
        tags: 标签列表
        account_file: 账号文件列表
        category: 原创声明类型
        enableTimer: 是否启用定时发布
        videos_per_day: 每天发布视频数
        daily_times: 每天发布时间点
        start_days: 从今天开始计算的发布天数
        desc: 视频描述
        thumbnail_path: 封面图片路径
        collection: 合集名称（模糊匹配）
    """
    # 生成文件的完整路径
    account_file = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
    files = [Path(BASE_DIR / "videoFile" / file) for file in files]
    thumbnail = resolve_thumbnail_path(thumbnail_path)
    file_num = len(files)
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(file_num, videos_per_day, daily_times, start_days)
    else:
        publish_datetimes = 0
    for index, file in enumerate(files):
        for cookie in account_file:
            # 打印视频文件名、标题和 hashtag
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"Hashtag：{tags}")
            if desc:
                print(f"描述：{desc[:50]}...")
            if thumbnail:
                print(f"封面：{thumbnail}")
            if collection:
                print(f"合集：{collection}")

            # 创建截图管理器（用于无头模式调试）
            account_name = cookie.stem if hasattr(cookie, 'stem') else str(cookie)
            screenshot_manager = ScreenshotManager(platform="xiaohongshu", account=account_name)

            app = XiaoHongShuVideo(
                title,
                file,
                tags,
                publish_datetimes,
                cookie,
                category=category,
                desc=desc,
                thumbnail_path=str(thumbnail) if thumbnail else None,
                collection=collection,  # 传递合集参数
                declaration_info=declaration_info,  # 传递声明信息
                screenshot_manager=screenshot_manager,  # 传递截图管理器
            )
            asyncio.run(app.main(), debug=False)


def post_video_baijiahao(title,files,tags,account_file,category=TencentZoneTypes.LIFESTYLE.value,enableTimer=False,videos_per_day = 1, daily_times=None,start_days = 0):
    """百家号视频发布"""
    # 生成文件的完整路径
    account_file = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
    files = [Path(BASE_DIR / "videoFile" / file) for file in files]
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(len(files), videos_per_day, daily_times,start_days)
    else:
        publish_datetimes = [0 for i in range(len(files))]
    for index, file in enumerate(files):
        for cookie in account_file:
            print(f"文件路径{str(file)}")
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"Hashtag：{tags}")
            app = BaiJiaHaoVideo(title, str(file), tags, publish_datetimes[index], cookie, category=category)
            asyncio.run(app.main(), debug=False)


def post_video_tiktok(title,files,tags,account_file,category=TencentZoneTypes.LIFESTYLE.value,enableTimer=False,videos_per_day = 1, daily_times=None,start_days = 0):
    """TikTok视频发布"""
    # 生成文件的完整路径
    account_file = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
    files = [Path(BASE_DIR / "videoFile" / file) for file in files]
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(len(files), videos_per_day, daily_times,start_days)
    else:
        publish_datetimes = [0 for i in range(len(files))]
    for index, file in enumerate(files):
        for cookie in account_file:
            print(f"文件路径{str(file)}")
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"Hashtag：{tags}")
            app = TiktokVideo(title, str(file), tags, publish_datetimes[index], cookie, category=category)
            asyncio.run(app.main(), debug=False)


def post_video_bilibili(title, files, tags, account_file, category=None, enableTimer=False, videos_per_day=1, daily_times=None, start_days=0, tid=218, desc='',
                         copyright_type=1, cover_path=None, collection=None, ai_declaration=False):
    """B站视频发布（纯 Python 实现，不依赖 biliup CLI）

    Args:
        title: 视频标题
        files: 视频文件列表
        tags: 标签列表
        account_file: 账号文件列表
        category: 原创声明（暂不支持）
        enableTimer: 是否启用定时发布
        videos_per_day: 每天发布视频数
        daily_times: 每天发布时间点
        start_days: 从今天开始计算的发布天数，0表示明天，1表示后天
        tid: B站分区ID，默认218（动物圈·综合）
        desc: 视频简介
        copyright_type: 版权声明类型，1=原创（默认），2=转载
        cover_path: 封面图片路径
        collection: 合集名称（暂不支持）
        ai_declaration: 是否添加"含AI生成内容"创作声明
    """
    # 生成文件的完整路径
    account_file = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
    files = [Path(BASE_DIR / "videoFile" / file) for file in files]

    # 处理封面路径
    resolved_cover = resolve_thumbnail_path(cover_path)

    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(len(files), videos_per_day, daily_times, start_days)
    else:
        publish_datetimes = [0 for i in range(len(files))]

    # 标签处理：B站要求至少一个标签
    # 优先从标题中提取 #标签（如"可爱猫咪#萌宠#猫咪"提取出"萌宠"和"猫咪"）
    hashtag_pattern = re.compile(r'#([^#\s]+)')
    hashtags = hashtag_pattern.findall(title)
    if hashtags:
        tag_str = ",".join(hashtags)
        print(f"从标题提取的标签：{hashtags}")
    elif tags:
        tag_str = ",".join(tags)
    else:
        tag_str = title  # 默认用标题作为tag

    for index, file in enumerate(files):
        for cookie in account_file:
            print(f"文件路径{str(file)}")
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"Hashtag：{tags}")
            print(f"分区ID：{tid}")
            print(f"原创声明：{'原创' if copyright_type == 1 else '转载'}")
            if ai_declaration:
                print(f"创作声明：含AI生成内容")
            if resolved_cover:
                print(f"封面路径：{resolved_cover}")

            uploader = BilibiliUploader(cookie)

            # 定时发布
            dtime = None
            if isinstance(publish_datetimes[index], int) and publish_datetimes[index] != 0:
                dtime = publish_datetimes[index]

            try:
                result = uploader.upload(
                    video_path=str(file),
                    title=title,
                    tid=tid,
                    tag=tag_str,
                    desc=desc or title,
                    copyright_type=copyright_type,
                    cover_path=resolved_cover,
                    no_reprint=1 if copyright_type == 1 else 0,
                    dtime=dtime,
                    ai_declaration=ai_declaration,
                )
                print(f"B站视频上传成功: {file}, BV号: {result.get('bvid', '')}")
            except Exception as e:
                print(f"B站视频上传失败: {e}")
                raise



# post_video("333",["demo.mp4"],"d","d")
# post_video_DouYin("333",["demo.mp4"],"d","d")
