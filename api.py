# -*- coding: utf-8 -*-
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import logging
import os
import sys
from typing import List, Optional, Dict

from fastapi import FastAPI, HTTPException, BackgroundTasks, Body, Depends
from pydantic import BaseModel, Field, field_validator, PositiveInt
import uvicorn

# --- Project Imports ---
# Ensure these modules are accessible in your Python environment
try:
    # 假设 conf.py 在项目根目录或 PYTHONPATH 中
    # 如果 api.py 在项目的子目录，可能需要调整路径
    current_dir = Path(__file__).parent
    project_root = current_dir.parent # 根据你的项目结构调整
    sys.path.insert(0, str(project_root)) # 确保能找到 conf 和 utils

    from conf import BASE_DIR
    from uploader.douyin_uploader.main import DouYinVideo
    from uploader.ks_uploader.main import KSVideo
    from uploader.tencent_uploader.main import TencentVideo
    from uploader.tk_uploader.main_chrome import TiktokVideo
    # Import necessary enums/constants and utilities
    from utils.base_social_media import get_supported_social_media, SOCIAL_MEDIA_DOUYIN, \
        SOCIAL_MEDIA_TENCENT, SOCIAL_MEDIA_TIKTOK, SOCIAL_MEDIA_KUAISHOU
    from utils.constant import TencentZoneTypes
    from utils.files_times import get_title_and_hashtags
except ImportError as e:
    print(f"关键模块导入失败: {e}. 请确保 FastAPI 环境可以访问项目模块。")
    print(f"Project root considered: {project_root}")
    print(f"sys.path: {sys.path}")
    sys.exit(1)
except NameError as e:
     print(f"关键配置 'BASE_DIR' 未找到: {e}. 请确保 conf.py 中已定义。")
     sys.exit(1)

# --- Setup Logging ---
log_format = '%(asctime)s - %(levelname)s - [%(name)s:%(lineno)d] - %(message)s' # 添加行号
logging.basicConfig(level=logging.INFO, format=log_format)
logger = logging.getLogger("UploaderAPI")

# --- Constants ---
try:
    COOKIES_DIR = Path(BASE_DIR) / "cookies"
    COOKIES_DIR.mkdir(parents=True, exist_ok=True) # Ensure exists
except Exception as e:
    logger.critical(f"无法访问或创建 Cookies 目录 ({COOKIES_DIR}): {e}")
    sys.exit(1)

SUPPORTED_PLATFORMS = get_supported_social_media() # Get list once

# --- Input Validation Models (Pydantic) ---
class RepeatConfig(BaseModel):
    interval_minutes: PositiveInt = Field(..., description="重复间隔时间（分钟）")
    times: PositiveInt = Field(..., description="重复总次数")

class UploadBaseRequest(BaseModel):
    """基本上传请求模型，包含通用字段"""
    platforms: List[str] = Field(..., min_length=1, description="要上传到的平台列表 (e.g., ['抖音', '快手'])")
    account_name: str = Field(..., description="用于所有选定平台的账号名称")
    # Schedule fields are optional
    publish_datetime: Optional[datetime] = Field(None, description="ISO 格式的定时发布时间 (UTC or with timezone offset), e.g., '2024-12-31T18:30:00+08:00'. 如果为 null, 则立即发布。")
    repeat: Optional[RepeatConfig] = Field(None, description="重复上传配置 (仅当 publish_datetime 设置时有效)")

    @field_validator('platforms')
    @classmethod
    def check_platforms_supported(cls, platforms: List[str]) -> List[str]:
        unsupported = [p for p in platforms if p not in SUPPORTED_PLATFORMS]
        if unsupported:
            raise ValueError(f"不支持的平台: {', '.join(unsupported)}. 支持的平台: {', '.join(SUPPORTED_PLATFORMS)}")
        return platforms

    @field_validator('publish_datetime')
    @classmethod
    def check_publish_datetime_future(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v:
            # Ensure datetime is aware if it has no timezone info (assume UTC or local based on server?)
            # Recommendation: Always use timezone-aware strings for input.
            now = datetime.now(v.tzinfo or timezone.utc) # Compare with same awareness
            # Add a small buffer (e.g., 30 seconds) to avoid race conditions
            if v <= now + timedelta(seconds=30):
                raise ValueError("定时发布时间必须是将来的时间 (至少30秒后)")
        return v

    @field_validator('repeat')
    @classmethod
    def check_repeat_with_schedule(cls, v: Optional[RepeatConfig], info) -> Optional[RepeatConfig]:
        # Correctly access validation context using Pydantic v2 style if needed,
        # but info.data works for simple cases.
        # Using info.data is generally okay for accessing other fields in the model.
        publish_dt = info.data.get('publish_datetime')
        if v and not publish_dt:
            raise ValueError("重复上传设置仅在设置了定时发布时间 (publish_datetime) 时有效。")
        return v

class UploadFromPathRequest(UploadBaseRequest):
    """用于从服务器本地路径上传的请求模型"""
    video_path: str = Field(..., description="视频文件在服务器上的绝对或相对路径")

    @field_validator('video_path')
    @classmethod
    def check_video_path_exists(cls, v: str) -> str:
        resolved_path = Path(v)
        # Try resolving relative paths against BASE_DIR for robustness
        if not resolved_path.is_absolute():
             resolved_path = Path(BASE_DIR) / v
             logger.debug(f"Relative path '{v}' resolved to '{resolved_path}' against BASE_DIR")

        if not resolved_path.is_file():
            raise ValueError(f"视频文件未找到或不是一个文件: {resolved_path} (原始输入: {v})")
        # Return the potentially resolved absolute path string for consistency
        return str(resolved_path)

# --- FastAPI App Instance ---
app = FastAPI(
    title="社交媒体上传 API",
    description="提供视频上传到多个社交媒体平台的接口，支持从服务器本地路径触发。",
    version="1.0.1", # Increment version
)

# --- Helper Functions ---
def get_uploader_instance(platform: str, account_file_path: Path, title: str, video_file_str: str, tags: list, publish_date: datetime | int):
    """Helper to create the correct uploader instance."""
    logger.info(f"Creating uploader instance for {platform} using cookie {account_file_path.name} | Publish Date: {publish_date}")
    account_file_str = str(account_file_path)
    try:
        # 使用关键字参数以提高可读性和健壮性
        common_args = {
            "title": title,
            "tags": tags,
            "publish_date": publish_date,
            "cookie_path": account_file_str,
        }
        # Douyin 可能有不同的参数名或顺序，需要确认
        if platform == SOCIAL_MEDIA_DOUYIN:
            # 假设 DouYinVideo 构造函数是 (self, title, file_path, tags, publish_date, cookie_path)
            # 如果 DouYinVideo 的 file_path 参数名不同，需要相应修改
            return DouYinVideo(title=title, file_path=video_file_str, tags=tags, publish_date=publish_date, cookie_path=account_file_str)
        elif platform == SOCIAL_MEDIA_TIKTOK:
            return TiktokVideo(file_path=video_file_str, **common_args)
        elif platform == SOCIAL_MEDIA_TENCENT:
            # 考虑将 category 设为可选参数或从请求传入
            return TencentVideo(file_path=video_file_str, category=TencentZoneTypes.LIFESTYLE.value, **common_args)
        elif platform == SOCIAL_MEDIA_KUAISHOU:
            return KSVideo(file_path=video_file_str, **common_args)
        else:
            raise ValueError(f"不支持的平台实例创建: {platform}")
    except Exception as e:
        logger.error(f"Error creating {platform} uploader instance for video '{video_file_str}': {e}", exc_info=True)
        # 重新抛出异常，以便上层可以捕获
        raise type(e)(f"创建 {platform} 上传器实例时出错: {e}") from e


async def perform_single_upload_iteration(
    platforms: list[str], account_name: str, video_path_obj: Path, title: str, tags: list,
    publish_date_obj: datetime | int # 0 for immediate, datetime for scheduled
    ) -> tuple[dict, dict]:
    """Helper async function to upload to all platforms for a single time slot."""
    success = {p: 0 for p in platforms}
    failure = {p: 0 for p in platforms}
    video_file_str = str(video_path_obj) # Convert Path to string once

    for platform in platforms:
        # await asyncio.sleep(0) # Yield control briefly if needed

        msg_start = f"平台 '{platform}', 账号 '{account_name}', 视频 '{video_path_obj.name}': 开始处理..."
        logger.info(f"BG Task: {msg_start}")
        try:
            cookie_file = COOKIES_DIR / f"{platform}_{account_name}.json"
            if not cookie_file.exists():
                raise FileNotFoundError(f"未找到平台 '{platform}' 账号 '{account_name}' 的 Cookie 文件: {cookie_file}")

            # Re-check video file existence right before this specific upload attempt
            if not video_path_obj.is_file():
                 raise FileNotFoundError(f"视频文件在尝试上传到 {platform} 前找不到了: {video_path_obj}")

            app_instance = get_uploader_instance(
                platform=platform,
                account_file_path=cookie_file,
                title=title,
                video_file_str=video_file_str,
                tags=tags,
                publish_date=publish_date_obj # Pass the correct type
            )

            # Assuming app_instance.main() is the async upload function
            logger.info(f"BG Task: Calling {platform} uploader's main method...")
            await app_instance.main() # Await the async upload process

            msg_success = f"平台 '{platform}', 账号 '{account_name}', 视频 '{video_path_obj.name}': 上传成功。"
            logger.info(f"BG Task: {msg_success}")
            success[platform] += 1
        except FileNotFoundError as e_inner:
            msg_fail = f"平台 '{platform}', 账号 '{account_name}': 处理失败! 原因: 文件未找到 - {e_inner}"
            logger.error(f"BG Task: {msg_fail}") # No need for full traceback for FileNotFoundError usually
            failure[platform] += 1
        except Exception as e_inner:
            msg_fail = f"平台 '{platform}', 账号 '{account_name}': 上传失败! 原因: {e_inner.__class__.__name__}: {e_inner}"
            logger.error(f"BG Task: {msg_fail}", exc_info=True) # Log full traceback for unexpected failures
            failure[platform] += 1
            # Continue with other platforms even if one fails

    return success, failure

# --- Background Task Logic ---
# This task now accepts the validated request model directly
async def process_upload_task(req: UploadFromPathRequest):
    """The actual upload logic that runs in the background (using local path)."""
    platforms = req.platforms
    account_name = req.account_name
    video_file = req.video_path # This is the validated path string from the request
    is_scheduled = req.publish_datetime is not None
    is_repeat = req.repeat is not None

    logger.info(f"BG Task started: Account='{account_name}', Platforms={platforms}, Video='{video_file}', Scheduled={is_scheduled}, Repeat={is_repeat}")

    try:
        # Path object creation and file check already done in Pydantic validation,
        # but good practice to re-check or handle potential race conditions if needed.
        # The path string `video_file` is guaranteed to exist at request time.
        video_path_obj = Path(video_file)
        if not video_path_obj.is_file():
             # This case might happen if file deleted between request and task start
             raise FileNotFoundError(f"视频文件在后台任务启动时消失了: {video_file}")

        # Extract title and tags from the video filename (or potentially pass them in request later)
        try:
            title, tags = get_title_and_hashtags(str(video_path_obj))
            logger.info(f"BG Task: Extracted Title='{title}', Tags={tags} from '{video_path_obj.name}'")
        except Exception as e_tags:
            logger.warning(f"BG Task: Failed to extract title/tags from filename '{video_path_obj.name}': {e_tags}. Using defaults.")
            title = video_path_obj.stem # Use filename without extension as default title
            tags = [] # Empty tags

        publish_date_base = req.publish_datetime # Already validated datetime or None

        if is_scheduled:
            if is_repeat:
                # --- Repeat Logic ---
                interval_minutes = req.repeat.interval_minutes
                interval_seconds = interval_minutes * 60
                total_times = req.repeat.times
                logger.info(f"BG Task: Repeat task detected: {total_times}x, interval {interval_minutes} mins ({interval_seconds}s)")
                success_summary = {p: 0 for p in platforms}
                failure_summary = {p: 0 for p in platforms}

                for repeat_num in range(total_times):
                    current_publish_dt = publish_date_base + timedelta(seconds=repeat_num * interval_seconds)
                    now = datetime.now(current_publish_dt.tzinfo or timezone.utc) # Ensure consistent timezone comparison
                    time_until_publish = (current_publish_dt - now).total_seconds()

                    logger.info(f"BG Task: Repeat {repeat_num+1}/{total_times}: Scheduled for {current_publish_dt} (in {time_until_publish:.1f}s)")

                    # Check if time is too far in past (allow maybe 1 min buffer for processing)
                    if time_until_publish < -60:
                        logger.warning(f"BG Task: Repeat {repeat_num+1}/{total_times}: Calculated time {current_publish_dt} is >1 min in the past. Skipping.")
                        for p in platforms: failure_summary[p] += 1
                        # Need to wait interval before next *attempt* even if skipping
                        if repeat_num < total_times - 1:
                             logger.info(f"BG Task: Skipping to next interval ({interval_seconds}s wait)...")
                             try: await asyncio.sleep(interval_seconds)
                             except asyncio.CancelledError: logger.warning("BG Task: Interval wait cancelled."); raise
                        continue # Skip upload logic

                    # Wait until scheduled time if it's in the future
                    if time_until_publish > 0:
                        logger.info(f"BG Task: Repeat {repeat_num+1}/{total_times}: Waiting {time_until_publish:.1f} seconds...")
                        try: await asyncio.sleep(time_until_publish)
                        except asyncio.CancelledError: logger.warning("BG Task: Waiting for scheduled time cancelled."); raise

                    logger.info(f"BG Task: Repeat {repeat_num+1}/{total_times}: Starting upload iteration for {current_publish_dt}...")
                    iter_success, iter_fail = await perform_single_upload_iteration(
                        platforms, account_name, video_path_obj, title, tags, current_publish_dt, # Pass datetime
                    )
                    for p, count in iter_success.items(): success_summary[p] += count
                    for p, count in iter_fail.items(): failure_summary[p] += count

                    # Wait for interval *after* completion, before next iteration (if any)
                    if repeat_num < total_times - 1:
                        logger.info(f"BG Task: Repeat {repeat_num+1}/{total_times}: Iteration complete. Waiting {interval_seconds} seconds for next...")
                        try: await asyncio.sleep(interval_seconds)
                        except asyncio.CancelledError: logger.warning("BG Task: Interval wait cancelled."); raise

                # Log final summary for repeats
                success_count = sum(success_summary.values()); fail_count = sum(failure_summary.values()); total_attempts = total_times * len(platforms)
                summary_msg = f"重复上传完成 ({total_times}次)。总尝试: {total_attempts}, 成功: {success_count}, 失败: {fail_count}。"
                failed_plats = [f"{p}({c})" for p, c in failure_summary.items() if c > 0];
                if failed_plats: summary_msg += f" 失败详情: {', '.join(failed_plats)}"
                logger.info(f"BG Task: {summary_msg}")

            else: # Single scheduled upload
                 now = datetime.now(publish_date_base.tzinfo or timezone.utc)
                 time_until_publish = (publish_date_base - now).total_seconds()
                 logger.info(f"BG Task: Single schedule: Target time {publish_date_base} (in {time_until_publish:.1f}s)")

                 # Wait until scheduled time
                 if time_until_publish > 0:
                     logger.info(f"BG Task: Single schedule: Waiting {time_until_publish:.1f} seconds...")
                     try: await asyncio.sleep(time_until_publish)
                     except asyncio.CancelledError: logger.warning("BG Task: Waiting for scheduled time cancelled."); raise
                 elif time_until_publish < -60: # Check if already too late
                      logger.warning(f"BG Task: Single schedule: Target time {publish_date_base} is >1 min in the past. Uploading immediately.")
                      # Proceed to upload immediately

                 logger.info(f"BG Task: Single schedule: Starting upload for {publish_date_base}...")
                 success_summary, failure_summary = await perform_single_upload_iteration(
                     platforms, account_name, video_path_obj, title, tags, publish_date_base # Pass datetime
                 )
                 success_count = sum(success_summary.values()); fail_count = sum(failure_summary.values())
                 summary_msg = f"定时上传完成 ({publish_date_base})。成功: {success_count}/{len(platforms)}。"
                 failed_plats = [p for p, c in failure_summary.items() if c > 0];
                 if failed_plats: summary_msg += f" 失败平台: {', '.join(failed_plats)}"
                 logger.info(f"BG Task: {summary_msg}")

        else: # Immediate upload
            logger.info(f"BG Task: Immediate upload task for account '{account_name}', video '{video_path_obj.name}'")
            publish_date_obj = 0 # Use 0 for immediate upload signal in uploader classes
            success_summary, failure_summary = await perform_single_upload_iteration(
                platforms, account_name, video_path_obj, title, tags, publish_date_obj
            )
            success_count = sum(success_summary.values()); fail_count = sum(failure_summary.values())
            summary_msg = f"立即上传完成。成功: {success_count}/{len(platforms)}。"
            failed_plats = [p for p, c in failure_summary.items() if c > 0];
            if failed_plats: summary_msg += f" 失败平台: {', '.join(failed_plats)}"
            logger.info(f"BG Task: {summary_msg}")

    except FileNotFoundError as e:
        logger.error(f"BG Task failed critically: File not found - {e}", exc_info=False) # Traceback maybe less useful here
    except Exception as e:
        logger.error(f"BG Task failed with unexpected error: {e}", exc_info=True)
        # Consider adding notification logic here (e.g., email, webhook)


# --- Reusable Dependency for Cookie Check ---
async def check_cookies(request: UploadBaseRequest) -> None:
    """
    Dependency to check for required cookie files before processing the request.
    Raises HTTPException 400 if any cookie is missing.
    """
    missing_cookies = []
    for platform in request.platforms:
        cookie_file = COOKIES_DIR / f"{platform}_{request.account_name}.json"
        if not cookie_file.exists():
            missing_cookies.append(platform)

    if missing_cookies:
        detail = f"账号 '{request.account_name}' 在以下平台缺少必需的 Cookie 文件: {', '.join(missing_cookies)}. 请先确保已通过对应程序登录并生成了 Cookie。"
        logger.warning(f"Upload request rejected: {detail}")
        raise HTTPException(status_code=400, detail=detail)
    logger.debug(f"Cookie check passed for account '{request.account_name}', platforms: {request.platforms}")


# --- API Endpoints ---

# NEW Endpoint specifically for local paths (reuses existing logic)
@app.post("/upload_from_path/", status_code=202, summary="从服务器本地路径上传视频")
async def create_upload_task_from_local_path(
    request: UploadFromPathRequest = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    _: None = Depends(check_cookies) # Apply cookie check dependency
):
    """
    接收包含服务器本地视频文件路径的上传请求，验证输入，
    并将实际上传操作添加到后台任务。
    立即返回 202 Accepted 状态码。
    """
    logger.info(f"Received upload request (from path): Account='{request.account_name}', Platforms={request.platforms}, VideoPath='{request.video_path}'")

    # Input validation (including path existence) is handled by Pydantic model.
    # Cookie check is handled by the `check_cookies` dependency.

    # Add the long-running task to the background
    # Pass the validated request object directly to the task
    background_tasks.add_task(process_upload_task, request)
    logger.info(f"Upload task (from path) for '{request.video_path}' added to background.")

    return {"message": "本地路径视频上传任务已接收并在后台开始处理。详细状态请查看服务器日志。"}


# Existing endpoint - clarify its function or deprecate if confusing
@app.post("/upload/", status_code=202, summary="[兼容] 从服务器本地路径上传视频", deprecated=True)
async def create_upload_task_legacy(
    request: UploadFromPathRequest = Body(...), # Use the same model for consistency now
    background_tasks: BackgroundTasks = BackgroundTasks(),
    _: None = Depends(check_cookies) # Apply cookie check dependency
):
    """
    [已弃用, 请使用 /upload_from_path/]
    接收包含服务器本地视频文件路径的上传请求，验证输入，
    并将实际上传操作添加到后台任务。立即返回 202 Accepted。
    """
    logger.warning("Received request on deprecated /upload/ endpoint. Use /upload_from_path/ instead.")
    logger.info(f"Received upload request (legacy /upload/): Account='{request.account_name}', Platforms={request.platforms}, VideoPath='{request.video_path}'")

    background_tasks.add_task(process_upload_task, request)
    logger.info(f"Upload task (legacy /upload/) for '{request.video_path}' added to background.")

    return {"message": "[已弃用] 上传任务已接收并在后台开始处理。请更新您的客户端以使用 /upload_from_path/。"}


@app.get("/platforms/", summary="获取支持的平台列表")
async def get_platforms():
    """返回当前配置支持的社交媒体平台列表。"""
    return {"supported_platforms": SUPPORTED_PLATFORMS}

@app.get("/accounts/", summary="获取扫描到的账号列表")
async def get_scanned_accounts():
    """
    扫描 cookies 目录 (基于 BASE_DIR/cookies) 并返回找到的账号名称列表。
    文件名格式应为 '平台名_账号名.json'。
    """
    accounts = set()
    try:
        if not COOKIES_DIR.is_dir():
            logger.warning(f"Cookies directory '{COOKIES_DIR}' not found during account scan.")
            return {"scanned_accounts": []}

        for cookie_file in COOKIES_DIR.glob('*_*.json'):
            filename = cookie_file.stem # e.g., "抖音_张三"
            parts = filename.split('_', 1)
            # Ensure format is Platform_AccountName and AccountName is not empty
            if len(parts) == 2 and parts[0] in SUPPORTED_PLATFORMS and parts[1]:
                accounts.add(parts[1]) # Add account name ("张三")
            else:
                logger.debug(f"Skipping file with unexpected format: {cookie_file.name}")
    except Exception as e:
        logger.error(f"扫描账号时出错: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="扫描账号文件时服务器内部出错。")

    sorted_accounts = sorted(list(accounts))
    logger.info(f"Scanned accounts: {sorted_accounts}")
    return {"scanned_accounts": sorted_accounts}


# --- Main Execution ---
if __name__ == "__main__":
    # Basic configuration check at startup
    try:
        if 'BASE_DIR' not in globals() or not isinstance(BASE_DIR, (str, Path)) or not Path(BASE_DIR).is_dir():
             raise ValueError(f"BASE_DIR ('{globals().get('BASE_DIR')}') 未在 conf.py 中定义或不是有效目录")
        logger.info(f"Base directory: {BASE_DIR}")
        logger.info(f"Cookies directory: {COOKIES_DIR}")
        # Cookies directory creation is handled earlier
    except Exception as e:
        logger.critical(f"启动前配置检查失败: {e}。请检查 conf.py 中的 BASE_DIR 设置。", exc_info=True)
        sys.exit(1)

    logger.info("Starting Uploader API server on http://0.0.0.0:8000 ...")
    # Production: reload=False
    # Development: reload=True (watches for file changes)
    # Make sure the app string matches filename:app_instance, e.g., "main:app" if file is main.py
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
    # Example for production using Gunicorn (install gunicorn):
    # gunicorn api:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000