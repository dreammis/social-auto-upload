import asyncio
import re
import os
import tempfile
from pathlib import Path
from PIL import Image

from conf import BASE_DIR
from myUtils.screenshot_manager import ScreenshotManager
from uploader.douyin_uploader.main import DouYinVideo
from uploader.ks_uploader.main import KSVideo
from uploader.tencent_uploader.main import TencentVideo
from uploader.xiaohongshu_uploader.main import XiaoHongShuVideo
from uploader.baijiahao_uploader.main import BaiJiaHaoVideo
from uploader.tk_uploader.main import TiktokVideo
from uploader.bilibili_uploader.main import BilibiliVideo, BILIBILI_PUBLISH_STRATEGY_IMMEDIATE, BILIBILI_PUBLISH_STRATEGY_SCHEDULED
from utils.constant import TencentZoneTypes
from utils.files_times import generate_schedule_time_next_day


def compress_image_if_needed(image_path, max_size_mb=5):
    """压缩图片如果超过指定大小
    
    Args:
        image_path: 图片路径（Path对象或字符串）
        max_size_mb: 最大大小（MB），默认5MB
    
    Returns:
        Path对象：如果图片小于限制，返回原路径；否则返回压缩后的临时文件路径
    """
    if not image_path:
        return None
    
    path = Path(image_path)
    if not path.exists():
        return None
    
    # 检查文件大小
    file_size_mb = path.stat().st_size / (1024 * 1024)
    
    if file_size_mb <= max_size_mb:
        return path
    
    print(f"图片大小 {file_size_mb:.2f}MB 超过限制 {max_size_mb}MB，开始压缩...")
    
    try:
        # 打开图片
        img = Image.open(path)
        
        # 创建临时文件
        temp_dir = tempfile.gettempdir()
        temp_path = Path(temp_dir) / f"compressed_{path.name}"
        
        # 逐步降低质量直到满足大小要求
        quality = 85
        while quality > 20:
            # 保存压缩后的图片
            if img.mode in ('RGBA', 'P'):
                # 转换为RGB模式（去除透明度）
                img = img.convert('RGB')
            
            img.save(temp_path, optimize=True, quality=quality)
            
            # 检查压缩后的大小
            compressed_size_mb = temp_path.stat().st_size / (1024 * 1024)
            
            if compressed_size_mb <= max_size_mb:
                print(f"压缩成功：{file_size_mb:.2f}MB → {compressed_size_mb:.2f}MB (质量={quality})")
                return temp_path
            
            quality -= 5
        
        # 如果质量降到20还是太大，尝试缩小尺寸
        print("质量压缩不足，尝试缩小尺寸...")
        scale_factor = 0.9
        while scale_factor > 0.5:
            new_width = int(img.width * scale_factor)
            new_height = int(img.height * scale_factor)
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            resized_img.save(temp_path, optimize=True, quality=75)
            compressed_size_mb = temp_path.stat().st_size / (1024 * 1024)
            
            if compressed_size_mb <= max_size_mb:
                print(f"压缩成功（缩放{scale_factor:.1f}）：{file_size_mb:.2f}MB → {compressed_size_mb:.2f}MB")
                return temp_path
            
            scale_factor -= 0.1
        
        print(f"警告：无法将图片压缩到 {max_size_mb}MB 以下，使用最小压缩版本")
        return temp_path
        
    except Exception as e:
        print(f"图片压缩失败：{e}")
        return path


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
    
    # 快手平台限制封面图片不能大于5MB，需要压缩
    if thumbnail:
        thumbnail = compress_image_if_needed(thumbnail, max_size_mb=5)
    
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
    """B站视频发布（使用 playwright 实现）

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
    # 只使用传入的tags参数，不从描述提取
    if not tags:
        raise ValueError("B站标签不能为空，请在话题栏填写标签")
    
    tag_list = tags
    print(f"使用的标签：{tags}")

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

            # 使用 playwright 实现
            publish_strategy = BILIBILI_PUBLISH_STRATEGY_SCHEDULED if enableTimer else BILIBILI_PUBLISH_STRATEGY_IMMEDIATE
            
            app = BilibiliVideo(
                title=title,
                file_path=str(file),
                tags=tag_list,
                publish_date=publish_datetimes[index],
                account_file=str(cookie),
                tid=tid,
                desc=desc or title,
                cover_path=str(resolved_cover) if resolved_cover else None,
                copyright_type=copyright_type,
                no_reprint=1 if copyright_type == 1 else 0,
                ai_declaration=ai_declaration,
                publish_strategy=publish_strategy,
            )

            try:
                asyncio.run(app.main(), debug=False)
                print(f"B站视频上传成功: {file}")
            except Exception as e:
                print(f"B站视频上传失败: {e}")
                raise



# post_video("333",["demo.mp4"],"d","d")
# post_video_DouYin("333",["demo.mp4"],"d","d")
