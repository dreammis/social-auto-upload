# -*- coding: utf-8 -*-
import asyncio
import os
import shlex # 用于安全地分割命令参数（如果需要），但列表更好
import sys
from datetime import datetime, timezone, timedelta # 确保导入 timedelta
from pathlib import Path
from typing import List, Optional

from loguru import logger # 使用 loguru 记录日志，与 FastAPI 示例一致

# --- 配置 ---
# 定义 biliup-rs 可执行文件的位置，或假定它在系统的 PATH 中
BILIUP_RS_EXECUTABLE = "biliup" # 如果需要，请更改，例如 "/usr/local/bin/biliup"
# 定义常见的 Bilibili 分区 ID (TIDs) - 根据需要添加更多
# 参考: https://github.com/biliup/biliup-rs/blob/main/src/uploader/bilibili/constants.rs#L11
class BiliBiliTIDs:
    """Bilibili 常用分区 ID"""
    ANIME = 1           # 动画
    MUSIC = 3           # 音乐
    DANCE = 129         # 舞蹈
    GAME = 4            # 游戏
    KNOWLEDGE = 36      # 知识
    TECH = 188          # 科技
    SPORTS = 234        # 运动
    AUTO = 223          # 汽车
    LIFE = 160          # 生活总区 (可能包含子分区)
    FOOD = 211          # 美食
    ANIMAL = 217        # 动物圈
    FASHION = 155       # 时尚
    ENTERTAINMENT = 5   # 娱乐
    MOVIES = 181        # 电影
    TV_SERIES = 119     # 电视剧
    DOCUMENTARY = 177   # 纪录片
    DEFAULT = LIFE      # 默认分区设为生活区

# 为 Bilibili 上传设置 logger
bilibili_logger = logger.bind(source="BiliBiliUploader")

# --- 认证辅助函数 ---
async def bilibili_check_cookie(cookie_file: str | Path) -> bool:
    """
    检查 Bilibili cookie 文件是否存在。
    注意：这 *不会* 验证 cookie 是否仍然有效。
          biliup-rs 会在尝试上传时处理这个问题。
    """
    cookie_path = Path(cookie_file)
    if not cookie_path.is_file():
        bilibili_logger.error(f"Bilibili cookie 文件未找到: {cookie_path}")
        return False
    bilibili_logger.info(f"Bilibili cookie 文件已找到: {cookie_path}")
    return True

async def bilibili_setup(cookie_file: str | Path, handle: bool = False) -> bool:
    """
    检查 cookie 文件。如果 handle=True 且文件丢失，
    它会记录手动登录的说明，但不会执行登录操作。
    """
    cookie_path = Path(cookie_file)
    if not await bilibili_check_cookie(cookie_path):
        if handle:
            bilibili_logger.warning(f"Cookie 文件 '{cookie_path}' 未找到。")
            bilibili_logger.warning(f"请在终端中手动运行 'biliup login' 或 'biliup login --user \"{cookie_path}\"' 来登录。")
            # 我们无法从这里轻松地触发适用于 API 的非阻塞交互式登录。
            # 用户必须单独执行此步骤。
        return False
    return True

# --- 上传器类 ---
class BiliBiliUploader:
    """
    使用 biliup-rs 命令行工具将视频上传到 Bilibili。
    """
    def __init__(self,
                 title: str,
                 file_path: str,
                 tags: List[str],
                 publish_date: Optional[datetime], # None 表示立即发布
                 cookie_file: str,
                 tid: int = BiliBiliTIDs.DEFAULT, # Bilibili 分区 ID
                 description: str = "", # 可选的简介
                 thumbnail_path: Optional[str] = None, # 可选的封面图片路径
                 no_reprint: bool = False, # True 表示禁止转载 (自制声明)
                 open_elec: bool = False, # True 表示开启充电面板
                 biliup_path: str = BILIUP_RS_EXECUTABLE):
        """
        初始化 BiliBiliUploader。

        Args:
            title (str): 视频标题。Bilibili 限制最多 80 个字符。
            file_path (str): 视频文件的路径。
            tags (List[str]): 标签列表。Bilibili 限制最多 12 个标签，每个标签最多 20 个字符。
            publish_date (Optional[datetime]): 用于定时发布的带时区信息的 datetime 对象。
                                                如果为 None 或过去的时间，则立即发布。
            cookie_file (str): biliup-rs cookie/凭证文件的路径 (例如, user.toml)。
            tid (int): Bilibili 分区 ID。默认为 '生活' 分区。
            description (str, optional): 视频简介。默认为 ""。Bilibili 限制最多 2500 个字符。
            thumbnail_path (Optional[str], optional): 封面图片的路径。默认为 None。
            no_reprint (bool, optional): 禁止转载 (开启自制声明)。默认为 False (允许转载)。
            open_elec (bool, optional): 开启充电面板。默认为 False。
            biliup_path (str, optional): biliup-rs 可执行文件的路径。默认为 'biliup'。
        """
        self.title = title[:80] # 强制执行 Bilibili 标题长度限制
        self.file_path = Path(file_path)
        # 强制执行 Bilibili 标签限制
        self.tags = [tag[:20] for tag in tags[:12]]
        self.publish_date = publish_date # 为了精确调度，应该是带时区信息的
        self.cookie_file = Path(cookie_file)
        self.tid = tid
        self.description = description[:2500] # 强制执行 Bilibili 简介长度限制
        self.thumbnail_path = Path(thumbnail_path) if thumbnail_path else None
        self.no_reprint = no_reprint
        self.open_elec = open_elec
        self.biliup_path = biliup_path

    async def _validate_inputs(self) -> bool:
        """在尝试上传之前进行基本检查。"""
        if not self.file_path.is_file():
            bilibili_logger.error(f"视频文件未找到: {self.file_path}")
            return False
        if self.thumbnail_path and not self.thumbnail_path.is_file():
            bilibili_logger.error(f"封面文件未找到: {self.thumbnail_path}")
            return False
        if not self.cookie_file.is_file():
            bilibili_logger.error(f"Cookie 文件未找到: {self.cookie_file}。请运行 'biliup login --user \"{self.cookie_file}\"'")
            return False
        # 我们不在这里检查 biliup_path 是否存在，依赖于子进程的错误
        return True

    def _build_command_list(self) -> List[str]:
        """构建用于子进程执行的命令列表。"""
        command = [
            self.biliup_path,
            "upload",
            # 必要参数
            "--user", str(self.cookie_file), # 指定用户cookie/配置文件
            "--tid", str(self.tid),           # 指定分区ID
            "-T", self.title,                 # 标题
        ]

        # 视频文件 (当前支持一个)
        command.append(str(self.file_path))

        # 可选简介
        if self.description:
            command.extend(["--desc", self.description])

        # 可选标签
        for tag in self.tags:
            command.extend(["--tag", tag])

        # 可选封面
        if self.thumbnail_path:
            command.extend(["--cover", str(self.thumbnail_path)])

        # 可选定时发布时间
        if self.publish_date:
            # 确保 datetime 对象是带时区的，以获得正确的时间戳
            if self.publish_date.tzinfo is None or self.publish_date.tzinfo.utcoffset(self.publish_date) is None:
                 bilibili_logger.warning(f"发布日期 {self.publish_date} 不带时区信息。假设使用本地时区进行时间戳转换。")
                 # 或者强制使用 UTC: self.publish_date = self.publish_date.replace(tzinfo=timezone.utc)
                 # 最好是输入的 datetime 对象本身就带时区信息。
            now = datetime.now(self.publish_date.tzinfo or timezone.utc) # 使用与发布日期相同的时区感知进行比较
            if self.publish_date > now:
                timestamp = int(self.publish_date.timestamp()) # 获取 Unix 时间戳 (整数)
                command.extend(["--dtime", str(timestamp)])
                bilibili_logger.info(f"计划在 {self.publish_date} (时间戳: {timestamp}) 上传")
            else:
                 bilibili_logger.warning(f"发布日期 {self.publish_date} 已是过去时间。将立即上传。")

        # 可选标志
        if self.no_reprint: # 如果为 True，添加 --no-reprint 开启自制声明
            command.append("--no-reprint")
        if self.open_elec: # 如果为 True，添加 --open-elec 开启充电
            command.append("--open-elec")

        # 如果需要，可以添加其他标志，如 --dolby, --hires

        return command

    async def upload(self) -> bool:
        """
        异步执行 biliup-rs 上传命令。

        Returns:
            bool: 如果上传命令执行看起来成功 (退出码为 0)，则返回 True，否则返回 False。

        Raises:
            ValueError: 如果输入验证失败。
            RuntimeError: 如果子进程执行遇到错误或退出码非零。
            FileNotFoundError: 如果找不到 biliup-rs 可执行文件。
            Exception: 其他子进程执行期间的意外错误。
        """
        if not await self._validate_inputs():
            raise ValueError("输入验证失败。请检查日志。")

        command_list = self._build_command_list()
        command_str = ' '.join(shlex.quote(str(arg)) for arg in command_list) # 用于安全地记录命令
        bilibili_logger.info(f"正在执行命令: {command_str}")

        process = None
        try:
            # 启动子进程
            process = await asyncio.create_subprocess_exec(
                *command_list,
                stdout=asyncio.subprocess.PIPE, # 捕获标准输出
                stderr=asyncio.subprocess.PIPE  # 捕获标准错误
            )

            stdout_lines = [] # 存储标准输出行
            stderr_lines = [] # 存储标准错误行

            # 并发处理标准输出和标准错误流
            async def read_stream(stream, log_func, line_list):
                """异步读取流并记录/存储每一行"""
                while True:
                    line_bytes = await stream.readline() # 读取一行字节
                    if not line_bytes: # 如果流结束则退出
                        break
                    # 解码为字符串，处理潜在的编码错误，并去除首尾空白
                    line = line_bytes.decode(sys.stdout.encoding, errors='replace').strip()
                    log_func(f"biliup: {line}") # 实时记录 biliup 的输出
                    line_list.append(line)      # 将行添加到列表中

            # 创建任务来读取标准输出和标准错误
            stdout_task = asyncio.create_task(read_stream(process.stdout, bilibili_logger.info, stdout_lines))
            stderr_task = asyncio.create_task(read_stream(process.stderr, bilibili_logger.warning, stderr_lines))

            # 等待两个读取任务完成
            await asyncio.gather(stdout_task, stderr_task)
            # 等待子进程结束并获取退出码
            return_code = await process.wait()

            bilibili_logger.info(f"biliup 进程已结束，退出码 {return_code}")

            # 根据退出码检查结果 (以及可选的输出内容)
            if return_code == 0:
                # 基本的成功检查，biliup-rs 通常在成功时退出码为 0
                # 你可能想要解析 stdout_lines 以获取更具体的成功消息
                bilibili_logger.success(f"视频 '{self.title}' 上传命令执行成功。")
                return True
            else:
                # 记录来自标准错误的详细信息
                error_message = f"视频 '{self.title}' 上传失败。退出码: {return_code}。"
                if stderr_lines:
                    error_message += "\n标准错误输出:\n" + "\n".join(stderr_lines)
                bilibili_logger.error(error_message)
                # 抛出异常以明确表示失败
                raise RuntimeError(error_message)

        except FileNotFoundError:
            # 如果找不到 biliup 命令
            bilibili_logger.error(f"错误: 命令 '{self.biliup_path}' 未找到。")
            bilibili_logger.error("请确保 biliup-rs 已安装并在您的 PATH 中，或提供完整路径。")
            raise # 重新抛出 FileNotFoundError
        except Exception as e:
            # 捕获其他可能的异常
            bilibili_logger.error(f"执行 biliup 时发生意外错误: {e}", exc_info=True)
            # 确保在发生异常时（例如任务被取消）终止仍在运行的进程
            if process and process.returncode is None:
                try:
                    process.terminate() # 尝试终止进程
                    await process.wait() # 等待终止完成
                except ProcessLookupError:
                    pass # 进程已经结束了
                except Exception as term_e:
                     bilibili_logger.error(f"终止 biliup 进程时出错: {term_e}")
            raise # 重新抛出原始异常

    async def main(self):
        """方便的异步 main 方法来运行上传。"""
        try:
            await self.upload()
        except Exception as e:
            bilibili_logger.error(f"上传过程失败: {e}")
            # 在你的应用程序中根据需要处理或传播错误

# --- 示例用法 ---
if __name__ == "__main__":
    # 配置 Loguru 将日志输出到控制台
    logger.add(sys.stderr, level="INFO")

    async def run_example():
        # --- !!! 重要提示 !!! ---
        # 请确保您已事先手动登录，使用以下命令之一：
        # biliup login --user "cookies/bilibili_my_account.json"
        # 或只是： biliup login (如果使用默认的 user.toml)
        # ------------------------

        # 定义 cookie 文件路径 (如果需要，请创建 'cookies' 目录)
        cookie_path = Path("cookies/bilibili_my_account.json")
        # !!! 将下面的路径替换为你的视频文件路径 !!!
        video_path_str = "path/to/your/video.mp4"
        # !!! 将下面的路径替换为你的封面图片路径 (可选) !!!
        thumb_path_str = "path/to/your/thumbnail.jpg"

        # 为测试目的，如果文件不存在，则创建虚拟文件
        video_path = Path(video_path_str)
        thumb_path = Path(thumb_path_str)
        if not video_path.exists():
            logger.warning(f"视频文件 '{video_path}' 未找到。为测试创建虚拟文件。")
            video_path.parent.mkdir(parents=True, exist_ok=True) # 确保父目录存在
            video_path.touch() # 创建空文件
        if thumb_path_str and not thumb_path.exists(): # 仅当提供了封面路径且文件不存在时创建
             logger.warning(f"封面文件 '{thumb_path}' 未找到。为测试创建虚拟文件。")
             thumb_path.parent.mkdir(parents=True, exist_ok=True) # 确保父目录存在
             thumb_path.touch() # 创建空文件

        # 确保 cookie 文件的父目录存在
        cookie_path.parent.mkdir(parents=True, exist_ok=True)
        # 检查是否需要设置 (cookie 文件是否存在?)
        if not await bilibili_setup(cookie_path, handle=True):
             logger.error("Bilibili 设置失败或需要手动登录。正在退出。")
             return # 如果需要登录则退出

        # 示例 1: 立即上传
        uploader_immediate = BiliBiliUploader(
            title="我的 biliup-rs 测试视频",
            file_path=str(video_path),
            tags=["测试", "自动化", "biliup"],
            publish_date=None, # 立即发布
            cookie_file=str(cookie_path),
            tid=BiliBiliTIDs.TECH, # 科技分区
            description="这是一个使用 biliup-rs 包装器上传的测试视频。",
            # 仅在封面文件实际存在时传递路径
            thumbnail_path=str(thumb_path) if thumb_path.exists() else None,
            no_reprint=True # 标记为自制
        )
        logger.info("\n--- 开始运行立即上传示例 ---")
        await uploader_immediate.main()
        logger.info("--- 立即上传示例结束 ---")

        await asyncio.sleep(5) # 在示例之间暂停 5 秒

        # 示例 2: 定时上传 (例如，明天上午 10:00 本地时间)
        try:
            # 确保 datetime 对象带有时区信息以用于 biliup --dtime
            # 获取当前时间，替换小时/分钟/秒/毫秒，并增加一天
            schedule_time = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)

            # 注意：如果系统时区配置正确，上面的代码通常可以工作。
            # 为了健壮性，如果可能，最好显式设置时区：
            # import tzlocal # 需要安装: pip install tzlocal
            # local_tz = tzlocal.get_localzone()
            # schedule_time = datetime.now(local_tz).replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
            # 或者使用 UTC 时间：
            # schedule_time = datetime.now(timezone.utc).replace(hour=2, minute=0, second=0, microsecond=0) + timedelta(days=1) # 例如：北京时间上午10点是UTC时间凌晨2点

            uploader_scheduled = BiliBiliUploader(
                title="我的定时发布测试视频",
                file_path=str(video_path),
                tags=["计划发布", "测试"],
                publish_date=schedule_time, # 定于明天发布
                cookie_file=str(cookie_path),
                tid=BiliBiliTIDs.LIFE, # 生活分区
                description="定时上传测试。",
                thumbnail_path=None, # 这次不使用封面
                open_elec=True # 开启充电面板
            )
            logger.info("\n--- 开始运行定时上传示例 ---")
            await uploader_scheduled.main()
            logger.info("--- 定时上传示例结束 ---")
        except Exception as e:
            logger.error(f"定时上传示例失败: {e}")


    # 运行异步示例函数
    asyncio.run(run_example())