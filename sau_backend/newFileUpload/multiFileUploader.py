import asyncio
from pathlib import Path
from conf import BASE_DIR
from .baseFileUploader import BaseFileUploader, run_upload
from utils.files_times import generate_schedule_time_next_day

def post_file(platform, account_file, file_type, files, title, text,tags,thumbnail_path, location, enableTimer=False, videos_per_day=1, daily_times=None, start_days=0):
    """
    批量发布多个文件到某个平台
    参数:
        platform: 平台名称
        account_file: 账号文件列表
        file_type: 文件类型，1-图文 2-视频
        files: 文件列表
        title: 视频标题
        text: 视频正文描述
        tags: 视频标签，多个标签用逗号隔开
        thumbnail_path: 视频缩略图路径
        location: 视频地点
        enableTimer: 是否开启定时发布
        videos_per_day: 每天发布视频数量
        daily_times: 每天发布时间列表
        start_days: 开始发布时间偏移天数
    """

    try:
        # 生成文件的完整路径
        account_file = [Path(BASE_DIR / "cookiesFile" / file) for file in account_file]
        files = [Path(BASE_DIR / "videoFile" / file) for file in files]
        file_num = len(files)

        if enableTimer:
            publish_datetimes = generate_schedule_time_next_day(file_num, videos_per_day,daily_times, start_days)
        else:
            publish_datetimes = 0

        success_count = 0
        for index, file in enumerate(files):
            file_published = False
            for cookie in account_file:
                try:
                    # 使用独立的run_upload函数来执行上传
                    publish_result = asyncio.run(run_upload(platform, cookie, file_type, file, title, text, tags, thumbnail_path, location, publish_datetimes))
                     
                    # 是否成功发布
                    if publish_result:
                        print(f"{platform}文件{file.name}发布成功")
                        success_count += 1
                        file_published = True
                        # 这个账号发布成功后跳过
                        continue
                    else:
                        print(f"{platform}文件{file.name}发布失败，尝试下一个账号")
                except Exception as e:
                    print(f"{platform}文件{file.name}发布失败: {str(e)}")
                    # 继续尝试其他账号，不中断当前文件的发布
                    continue
            
            # 任务进度 - 显示成功数量/总数量
            print(f"{platform}已发布{success_count}/{file_num}个文件")
        
        # 全部发布完毕后，显示最终结果
        if success_count == file_num:
            print(f"{platform}所有文件发布完成")
        else:
            print(f"{platform}发布完成，成功发布{success_count}/{file_num}个文件")
        # 如果有文件发布成功，返回True
        if file_published:
            return True
        else:
            return False
    except Exception as e:
        print(f"{platform}文件发布过程中发生异常: {str(e)}")
        return False


#批量发布单个文件到多个平台
def post_single_file_to_multiple_platforms(platforms, account_files, file_type, file, title, text, tags, thumbnail_path, location, enableTimer=False, videos_per_day=1, daily_times=None, start_days=0):
    """
    批量发布单个文件到多个平台
    参数:
        platforms: 平台名称列表
        account_files: 账号文件字典，key为平台名称，value为该平台对应的账号文件列表
        file_type: 文件类型，1-图文 2-视频
        file: 单个文件路径
        title: 视频标题
        text: 视频正文描述
        tags: 视频标签，多个标签用逗号隔开
        thumbnail_path: 视频缩略图路径
        location: 视频地点
        enableTimer: 是否开启定时发布
        videos_per_day: 每天发布视频数量
        daily_times: 每天发布时间列表
        start_days: 开始发布时间偏移天数
    返回值:
        bool: 所有平台发布是否全部成功
    """

    try:
        # 生成文件的完整路径
        file = Path(BASE_DIR / "videoFile" / file)
        platform_num = len(platforms)
        success_count = 0

        # 单个文件发布，不需要生成多个时间点
        if enableTimer:
            # 生成一个发布时间点
            publish_datetimes = generate_schedule_time_next_day(1, videos_per_day, daily_times, start_days)
        else:
            publish_datetimes = 0

        for index, platform in enumerate(platforms):
            # 获取当前平台对应的账号文件列表
            if platform in account_files:
                platform_accounts = account_files[platform]
                platform_accounts = [Path(BASE_DIR / "cookiesFile" / account) for account in platform_accounts]
            else:
                print(f"平台{platform}没有对应的账号文件，跳过发布")
                continue

            for cookie in platform_accounts:
                try:
                    # 使用独立的run_upload函数来执行上传
                    publish_result = asyncio.run(run_upload(platform, cookie, file_type, file, title, text, tags, thumbnail_path, location, publish_datetimes))
                    
                    # 是否成功发布
                    if publish_result:
                        print(f"{platform}文件{file.name}发布成功")
                        success_count += 1
                        # 一个平台只需要用一个账号发布成功即可
                        break
                    else:
                        print(f"{platform}文件{file.name}发布失败，尝试下一个账号")
                except Exception as e:
                    print(f"{platform}文件{file.name}发布失败: {str(e)}")
                    # 继续尝试其他账号，不中断当前平台的发布
                    continue
            
            # 任务进度 - 显示成功数量/总数量
            print(f"已发布到{success_count}/{platform_num}个平台")
        
        # 全部发布完毕后
        if success_count == platform_num:
            print(f"所有平台发布完成，成功发布到{success_count}/{platform_num}个平台")
            return True
        else:
            print(f"发布完成，但部分平台发布失败，成功发布到{success_count}/{platform_num}个平台")
            return False
    except Exception as e:
        print(f"文件发布过程中发生异常: {str(e)}")
        return False


def post_multiple_files_to_multiple_platforms(platforms, account_files, file_type, files, title, text, tags, thumbnail_path, location, enableTimer=False, videos_per_day=1, daily_times=None, start_days=0):
    """
    批量发布多个文件到多个平台
    参数:
        platforms: 平台名称列表
        account_files: 账号文件字典，key为平台名称，value为该平台对应的账号文件列表
        file_type: 文件类型，1-图文 2-视频
        files: 文件列表
        title: 视频标题
        text: 视频正文描述
        tags: 视频标签，多个标签用逗号隔开
        thumbnail_path: 视频缩略图路径
        location: 视频地点
        enableTimer: 是否开启定时发布
        videos_per_day: 每天发布视频数量
        daily_times: 每天发布时间列表
        start_days: 开始发布时间偏移天数
    返回值:
        dict: 发布结果字典，key为平台名称，value为该平台的发布结果（成功数量/总数量）
    """

    try:
        # 生成文件的完整路径
        files = [Path(BASE_DIR / "videoFile" / file) for file in files]
        file_num = len(files)
        platform_num = len(platforms)
        
        # 初始化发布结果字典
        publish_results = {}
        for platform in platforms:
            publish_results[platform] = {"success": 0, "total": file_num}
        
        # 生成所有文件的发布时间点
        if enableTimer:
            publish_datetimes = generate_schedule_time_next_day(file_num, videos_per_day, daily_times, start_days)
        else:
            publish_datetimes = 0
        
        # 遍历所有文件
        for file_index, file in enumerate(files):
            print(f"\n开始处理文件 {file.name} ({file_index+1}/{file_num})")
            
            # 遍历所有平台
            for platform in platforms:
                # 获取当前平台对应的账号文件列表
                if platform in account_files:
                    platform_accounts = account_files[platform]
                    platform_accounts = [Path(BASE_DIR / "cookiesFile" / account) for account in platform_accounts]
                else:
                    print(f"平台{platform}没有对应的账号文件，跳过发布")
                    continue
                
                # 遍历当前平台的所有账号，直到发布成功
                published = False
                for cookie in platform_accounts:
                    try:
                        # 使用独立的run_upload函数来执行上传
                        publish_result = asyncio.run(run_upload(platform, cookie, file_type, file, title, text, tags, thumbnail_path, location, publish_datetimes))
                        
                        # 是否成功发布
                        if publish_result:
                            print(f"{platform}文件{file.name}发布成功")
                            publish_results[platform]["success"] += 1
                            published = True
                            break
                        else:
                            print(f"{platform}文件{file.name}发布失败，尝试下一个账号")
                    except Exception as e:
                        print(f"{platform}文件{file.name}发布失败: {str(e)}")
                        # 继续尝试其他账号，不中断当前平台的发布
                        continue
                
                if not published:
                    print(f"{platform}文件{file.name}所有账号发布失败")
        
        # 输出最终发布结果
        print("\n=== 发布结果汇总 ===")
        for platform, result in publish_results.items():
            success = result["success"]
            total = result["total"]
            print(f"{platform}: 成功 {success}/{total}")
        
        return publish_results
    except Exception as e:
        print(f"文件发布过程中发生异常: {str(e)}")
        return {}
