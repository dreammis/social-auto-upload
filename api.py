# -*- coding: utf-8 -*-
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import logging
import os
import sys
from typing import List, Optional, Dict

from fastapi import FastAPI, HTTPException, BackgroundTasks, Body
from pydantic import BaseModel, Field, FilePath, field_validator, PositiveInt
import uvicorn

# --- Project Imports ---
# Ensure these modules are accessible in your Python environment
try:
    from conf import BASE_DIR
    from uploader.douyin_uploader.main import DouYinVideo # Assuming setup is not needed if cookies exist
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
    sys.exit(1)

# --- Setup Logging ---
# Configure logging for the API server
log_format = '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
logging.basicConfig(level=logging.INFO, format=log_format)
logger = logging.getLogger("UploaderAPI")

# --- Constants ---
COOKIES_DIR = Path(BASE_DIR) / "cookies"
SUPPORTED_PLATFORMS = get_supported_social_media() # Get list once

# --- Input Validation Models (Pydantic) ---
class RepeatConfig(BaseModel):
    interval_minutes: PositiveInt = Field(..., description="重复间隔时间（分钟）")
    times: PositiveInt = Field(..., description="重复总次数")

class UploadRequest(BaseModel):
    platforms: List[str] = Field(..., min_length=1, description="要上传到的平台列表 (e.g., ['抖音', '快手'])")
    account_name: str = Field(..., description="用于所有选定平台的账号名称")
    video_path: str = Field(..., description="视频文件在服务器上的绝对或相对路径")
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

    @field_validator('video_path')
    @classmethod
    def check_video_path_exists(cls, v: str) -> str:
        # Note: This checks path existence *at validation time* on the server.
        # The file might be moved/deleted before the background task runs.
        # Consider re-checking in the background task.
        if not Path(v).is_file():
            raise ValueError(f"视频文件未找到或不是一个文件: {v}")
        return v

    @field_validator('publish_datetime')
    @classmethod
    def check_publish_datetime_future(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v:
            # Ensure datetime is aware if it has no timezone info (assume local?)
            # Or better, require timezone-aware strings (like ISO format with offset/Z)
            now = datetime.now(v.tzinfo or timezone.utc) # Compare with same awareness
            if v <= now + timedelta(seconds=30): # Add buffer
                raise ValueError("定时发布时间必须是将来的时间 (至少30秒后)")
        return v

    @field_validator('repeat')
    @classmethod
    def check_repeat_with_schedule(cls, v: Optional[RepeatConfig], info) -> Optional[RepeatConfig]:
        # Repeat only makes sense if publish_datetime is also set
        publish_dt = info.data.get('publish_datetime')
        if v and not publish_dt:
            raise ValueError("重复上传设置仅在设置了定时发布时间 (publish_datetime) 时有效。")
        return v


# --- FastAPI App Instance ---
app = FastAPI(
    title="社交媒体上传 API",
    description="提供视频上传到多个社交媒体平台的接口。",
    version="1.0.0",
)

# --- Helper Functions (Adapted from GUI) ---
# Reusing _get_uploader_instance, assuming it works with paths
def get_uploader_instance(platform, account_file_path: Path, title, video_file_str, tags, publish_date):
    """Helper to create the correct uploader instance (uses specific cookie path)."""
    # This function needs access to the uploader classes (DouYinVideo, etc.)
    logger.info(f"Creating uploader instance for {platform} using cookie {account_file_path} with publish_date: {publish_date}")
    account_file_str = str(account_file_path)
    try:
        if platform == SOCIAL_MEDIA_DOUYIN: account_name = account_file_path.stem.split('_', 1)[1] if '_' in account_file_path.stem else 'Unknown'; logger.debug(f"Instantiating DouYinVideo positionally: title='{title}', file='{video_file_str}', tags={tags}, publish_date={publish_date}, cookie='{account_file_str}' (Account: {account_name})"); return DouYinVideo(title, video_file_str, tags, publish_date, account_file_str)
        else: common_args = { "title": title, "file_path": video_file_str, "tags": tags, "publish_date": publish_date, "cookie_path": account_file_str };
        if platform == SOCIAL_MEDIA_TIKTOK: return TiktokVideo(**common_args)
        elif platform == SOCIAL_MEDIA_TENCENT: return TencentVideo(**common_args, category=TencentZoneTypes.LIFESTYLE.value) # Make category configurable?
        elif platform == SOCIAL_MEDIA_KUAISHOU: return KSVideo(**common_args)
        else: raise ValueError(f"不支持的平台实例创建: {platform}")
    except Exception as e: logger.error(f"Error creating {platform} uploader instance: {e}", exc_info=True); raise type(e)(f"创建 {platform} 上传器实例时出错: {e}") from e


async def perform_single_upload_iteration(
    platforms: list[str], account_name: str, video_path_obj: Path, title: str, tags: list,
    publish_date_obj: datetime | int
    ) -> tuple[dict, dict]:
    """Helper async function to upload to all platforms for a single time slot."""
    success = {p: 0 for p in platforms}; failure = {p: 0 for p in platforms}
    for platform in platforms:
        # Check for cancellation if using more advanced task management
        # await asyncio.sleep(0) # Yield control briefly

        msg_start = f"平台 '{platform}', 账号 '{account_name}': 开始上传..."
        logger.info(f"BG Task: {msg_start}")
        try:
            cookie_file = COOKIES_DIR / f"{platform}_{account_name}.json"
            if not cookie_file.exists():
                raise FileNotFoundError(f"未找到平台 '{platform}' 账号 '{account_name}' 的 Cookie 文件。请确保已登录。")

            # Ensure video file still exists before attempting upload
            if not video_path_obj.is_file():
                 raise FileNotFoundError(f"视频文件在执行上传前找不到了: {video_path_obj}")

            app_instance = get_uploader_instance(platform, cookie_file, title, str(video_path_obj), tags, publish_date_obj)
            # Assuming app_instance.main() is the async upload function
            await app_instance.main()

            msg_success = f"平台 '{platform}', 账号 '{account_name}': 上传成功。"
            logger.info(f"BG Task: {msg_success}")
            success[platform] += 1
        except Exception as e_inner:
            msg_fail = f"平台 '{platform}', 账号 '{account_name}': 上传失败! 原因: {e_inner.__class__.__name__}: {e_inner}"
            logger.error(f"BG Task: {msg_fail}", exc_info=True) # Log full traceback for failures
            failure[platform] += 1
            # Continue with other platforms even if one fails

    return success, failure

# --- Background Task Logic ---
async def process_upload_task(req: UploadRequest):
    """The actual upload logic that runs in the background."""
    platforms = req.platforms
    account_name = req.account_name
    video_file = req.video_path
    is_scheduled = req.publish_datetime is not None
    is_repeat = req.repeat is not None

    logger.info(f"BG Task started: Account='{account_name}', Platforms={platforms}, Video='{video_file}', Scheduled={is_scheduled}, Repeat={is_repeat}")

    try:
        video_path_obj = Path(video_file)
        # Re-check file existence just before processing
        if not video_path_obj.is_file():
            raise FileNotFoundError(f"视频文件在后台任务开始时未找到: {video_file}")

        title, tags = get_title_and_hashtags(str(video_path_obj))
        publish_date_obj = 0 # Default for immediate

        if is_scheduled:
            publish_date_obj = req.publish_datetime # Already validated as datetime
            if is_repeat:
                # --- Repeat Logic ---
                interval_seconds = req.repeat.interval_minutes * 60
                total_times = req.repeat.times
                logger.info(f"BG Task: Repeat task detected: {total_times}x, interval {interval_seconds}s")
                success_summary = {p: 0 for p in platforms}
                failure_summary = {p: 0 for p in platforms}

                for repeat_num in range(total_times):
                    # Calculate publish time for this iteration
                    current_publish_dt = publish_date_obj + timedelta(seconds=repeat_num * interval_seconds)
                    # Check if time is too far in past? Platforms might handle this.
                    now = datetime.now(current_publish_dt.tzinfo or timezone.utc)
                    if current_publish_dt < now - timedelta(minutes=5): # Allow small window for processing delay
                         logger.warning(f"BG Task: Repeat {repeat_num+1}/{total_times}: Calculated time {current_publish_dt} is significantly in the past. Skipping this iteration.")
                         for p in platforms: failure_summary[p] += 1 # Count as failure for this iter
                         continue # Skip to next iteration/wait

                    # Wait until scheduled time if it's in the future
                    wait_seconds = (current_publish_dt - now).total_seconds()
                    if wait_seconds > 0:
                        logger.info(f"BG Task: Repeat {repeat_num+1}/{total_times}: Waiting {wait_seconds:.1f} seconds until scheduled time {current_publish_dt}...")
                        try:
                            await asyncio.sleep(wait_seconds)
                        except asyncio.CancelledError:
                            logger.warning("BG Task: Waiting for scheduled time cancelled.")
                            raise # Propagate cancellation

                    logger.info(f"BG Task: Repeat {repeat_num+1}/{total_times}: Starting upload iteration for {current_publish_dt}...")
                    iter_success, iter_fail = await perform_single_upload_iteration(
                        platforms, account_name, video_path_obj, title, tags, current_publish_dt, # Pass datetime for scheduled
                    )
                    for p, count in iter_success.items(): success_summary[p] += count
                    for p, count in iter_fail.items(): failure_summary[p] += count

                    # Wait for interval *after* completion, before next iteration (if any)
                    if repeat_num < total_times - 1:
                        logger.info(f"BG Task: Repeat {repeat_num+1}/{total_times}: Iteration complete. Waiting {interval_seconds} seconds for next...")
                        try:
                            await asyncio.sleep(interval_seconds)
                        except asyncio.CancelledError:
                            logger.warning("BG Task: Interval wait cancelled.")
                            raise

                # Log final summary for repeats
                success_count = sum(success_summary.values()); fail_count = sum(failure_summary.values()); total_attempts = total_times * len(platforms)
                summary_msg = f"重复上传完成 ({total_times}次)。总尝试: {total_attempts}, 成功: {success_count}, 失败: {fail_count}。"
                failed_plats = [f"{p}({c})" for p, c in failure_summary.items() if c > 0];
                if failed_plats: summary_msg += f" 失败详情: {', '.join(failed_plats)}"
                logger.info(f"BG Task: {summary_msg}")
                # No return needed, just logging

            else: # Single scheduled upload
                 # Wait until scheduled time
                now = datetime.now(publish_date_obj.tzinfo or timezone.utc)
                wait_seconds = (publish_date_obj - now).total_seconds()
                if wait_seconds > 0:
                    logger.info(f"BG Task: Single schedule: Waiting {wait_seconds:.1f} seconds until scheduled time {publish_date_obj}...")
                    try: await asyncio.sleep(wait_seconds)
                    except asyncio.CancelledError: logger.warning("BG Task: Waiting for scheduled time cancelled."); raise

                logger.info(f"BG Task: Single schedule: Starting upload for {publish_date_obj}...")
                success_summary, failure_summary = await perform_single_upload_iteration(
                    platforms, account_name, video_path_obj, title, tags, publish_date_obj # Pass datetime
                )
                success_count = sum(success_summary.values()); fail_count = sum(failure_summary.values())
                summary_msg = f"定时上传完成。成功: {success_count}/{len(platforms)}。"
                failed_plats = [p for p, c in failure_summary.items() if c > 0];
                if failed_plats: summary_msg += f" 失败平台: {', '.join(failed_plats)}"
                logger.info(f"BG Task: {summary_msg}")

        else: # Immediate upload
            logger.info(f"BG Task: Immediate upload task for account '{account_name}'")
            publish_date_obj = 0 # Use 0 for immediate
            success_summary, failure_summary = await perform_single_upload_iteration(
                platforms, account_name, video_path_obj, title, tags, publish_date_obj
            )
            success_count = sum(success_summary.values()); fail_count = sum(failure_summary.values())
            summary_msg = f"立即上传完成。成功: {success_count}/{len(platforms)}。"
            failed_plats = [p for p, c in failure_summary.items() if c > 0];
            if failed_plats: summary_msg += f" 失败平台: {', '.join(failed_plats)}"
            logger.info(f"BG Task: {summary_msg}")

    except FileNotFoundError as e:
        logger.error(f"BG Task failed: File not found - {e}", exc_info=True)
        # Potentially notify someone or update a task status DB here
    except Exception as e:
        logger.error(f"BG Task failed with unexpected error: {e}", exc_info=True)
        # Potentially notify someone


# --- API Endpoints ---
@app.post("/upload/", status_code=202) # 202 Accepted indicates task started
async def create_upload_task(
    request: UploadRequest = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    接收上传请求，验证输入，并将实际上传操作添加到后台任务。
    立即返回 202 Accepted 状态码。
    """
    logger.info(f"Received upload request: Account='{request.account_name}', Platforms={request.platforms}, Video='{request.video_path}'")

    # --- Basic Pre-check for Cookies (Optional but helpful) ---
    # This prevents starting a task doomed to fail immediately if no cookies exist.
    missing_cookies = []
    for platform in request.platforms:
        cookie_file = COOKIES_DIR / f"{platform}_{request.account_name}.json"
        if not cookie_file.exists():
            missing_cookies.append(platform)

    if missing_cookies:
        detail = f"账号 '{request.account_name}' 在以下平台缺少必需的 Cookie 文件: {', '.join(missing_cookies)}. 请先确保登录。"
        logger.warning(f"Upload request rejected: {detail}")
        raise HTTPException(status_code=400, detail=detail)
    # --- End Pre-check ---

    # Add the long-running task to the background
    background_tasks.add_task(process_upload_task, request)
    logger.info("Upload task added to background.")

    return {"message": "上传任务已接收并在后台开始处理。详细状态请查看服务器日志。"}

@app.get("/platforms/")
async def get_platforms():
    """返回支持的平台列表。"""
    return {"supported_platforms": SUPPORTED_PLATFORMS}

@app.get("/accounts/")
async def get_scanned_accounts():
    """扫描 cookies 目录并返回找到的账号名称列表。"""
    # Use the same scanning logic as the GUI
    accounts = set()
    try:
        for cookie_file in COOKIES_DIR.glob('*_*.json'):
            filename = cookie_file.stem
            parts = filename.split('_', 1)
            if len(parts) == 2 and parts[1]: accounts.add(parts[1])
    except Exception as e:
        logger.error(f"扫描账号时出错: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="扫描账号时服务器内部出错。")
    return {"scanned_accounts": sorted(list(accounts))}


# --- Main Execution ---
if __name__ == "__main__":
    # Ensure BASE_DIR check is done before starting server
    try:
        if 'BASE_DIR' not in globals() or not isinstance(BASE_DIR, (str, Path)) or not Path(BASE_DIR).is_dir():
            raise FileNotFoundError(f"BASE_DIR 未在 conf.py 中定义或不是有效目录")
        COOKIES_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Base directory checked: {BASE_DIR}")
    except Exception as e:
        logger.critical(f"配置检查失败: {e}。请检查 conf.py 中的 BASE_DIR 设置。", exc_info=True)
        sys.exit(1)

    logger.info("Starting Uploader API server...")
    # Use reload=True for development, remove for production
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
    # To run without auto-reload: uvicorn.run(app, host="0.0.0.0", port=8000)