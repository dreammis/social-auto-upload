# -*- coding: utf-8 -*-
# ^ Added encoding declaration for potentially non-ASCII paths/titles

import asyncio
from datetime import datetime, timedelta
from os.path import exists
from pathlib import Path
import sys
import json
import logging
import time # Potentially needed for fine-grained sleeps

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QComboBox, QLineEdit, QPushButton, QFileDialog,
                               QGroupBox, QRadioButton, QDateTimeEdit, QMessageBox, QCheckBox,
                               QCompleter)
from PySide6.QtCore import (Qt, QDateTime, QThread, Signal, QObject, QSettings,
                           QTimer)

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s')


# --- Project Imports ---
try:
    # Assuming conf.py is one level up or in PYTHONPATH
    # Adjust relative path if needed, e.g., from ..conf import BASE_DIR
    from conf import BASE_DIR
    from uploader.douyin_uploader.main import douyin_setup, DouYinVideo
    from uploader.ks_uploader.main import ks_setup, KSVideo
    from uploader.tencent_uploader.main import weixin_setup, TencentVideo
    from uploader.tk_uploader.main_chrome import tiktok_setup, TiktokVideo
    from utils.base_social_media import get_supported_social_media, SOCIAL_MEDIA_DOUYIN, \
        SOCIAL_MEDIA_TENCENT, SOCIAL_MEDIA_TIKTOK, SOCIAL_MEDIA_KUAISHOU
    from utils.constant import TencentZoneTypes
    from utils.files_times import get_title_and_hashtags
except ImportError as e:
    logging.critical(f"关键模块导入失败。请确保项目结构正确且依赖已安装。 Import Error: {e}", exc_info=True)
    # Attempt to show message box before exiting
    try:
        app_temp = QApplication.instance() # Check if app exists
        if not app_temp:
            app_temp = QApplication(sys.argv) # Create temporary app for message box
        QMessageBox.critical(None, "启动错误", f"关键模块导入失败: {e}\n请检查环境和项目路径。")
    except Exception as me:
        print(f"无法显示错误弹窗: {me}") # Fallback to print if GUI fails
    sys.exit(f"关键模块导入失败: {e}")


# --- Constants for QSettings ---
ORGANIZATION_NAME = "YourOrganizationName" # !!! CHANGE THIS !!!
APPLICATION_NAME = "SocialMediaUploader"
SETTINGS_HISTORY_PREFIX = "account_history/"

# --- Async Worker ---
class AsyncWorker(QObject):
    finished = Signal()
    success = Signal(str, str) # platform, account
    error = Signal(str)
    message = Signal(str)

    def __init__(self, coro_func, *args, **kwargs):
        super().__init__()
        self.coro_func = coro_func
        self.args = args
        self.kwargs = kwargs
        self._is_running = True
        self._loop = None

    async def run_wrapper(self):
        try:
            await self.coro_func(*self.args, **self.kwargs)
            if self._is_running:
                platform = self.kwargs.get('platform') or (self.args[0] if self.args else None)
                account = self.kwargs.get('account_name') or (self.args[1] if len(self.args) > 1 else None)
                if platform and account:
                     self.success.emit(platform, account)
                self.message.emit("操作成功完成")
        except Exception as e:
            logging.exception("异步任务执行出错:")
            if self._is_running:
                self.error.emit(f"操作失败: {e.__class__.__name__}: {e}")
        finally:
            if self._is_running:
                self.finished.emit() # Signal that the work is done

    def run(self):
        thread_name = QThread.currentThread().objectName()
        logging.info(f"AsyncWorker starting run method on thread: {thread_name}")
        if not self._is_running:
            logging.warning("Worker run called but already stopped.")
            return

        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            logging.info(f"Asyncio loop created and set for thread {thread_name}")
            self._loop.run_until_complete(self.run_wrapper())
            logging.info(f"Asyncio run_until_complete finished on thread {thread_name}")
        except Exception as e:
            logging.exception("设置或运行异步循环时出错:")
            if self._is_running:
                self.error.emit(f"异步任务运行时出错: {e.__class__.__name__}: {e}")
                # Ensure finished is emitted if loop setup/run fails catastrophically
                # Use a flag to prevent double emission?
                if hasattr(self, '_finished_emitted') and not self._finished_emitted:
                    self.finished.emit()
                    self._finished_emitted = True

        finally:
            logging.info(f"AsyncWorker run method finally block on thread {thread_name}")
            if self._loop:
                try:
                    if self._loop.is_running():
                        logging.info("Loop is running, scheduling stop...")
                        # Ensure stop is called from the loop's thread if possible,
                        # but call_soon_threadsafe handles calls from other threads.
                        self._loop.call_soon_threadsafe(self._loop.stop)
                        # Give loop a chance to process stop, but don't block GUI thread long
                        # This might be tricky. Closing might be enough.
                    logging.info("Closing asyncio loop...")
                    self._loop.close()
                    logging.info("Asyncio loop closed.")
                except Exception as e:
                    logging.error(f"关闭 asyncio 循环时出错: {e}", exc_info=True)
                self._loop = None
                # It's good practice to clear the loop policy for the thread if done
                # asyncio.set_event_loop(None) # Be cautious with this in multi-threaded apps

            # Set flag after finished signal is potentially emitted
            self._finished_emitted = True # Mark as finished handled

    def stop(self):
        logging.info("AsyncWorker stop requested.")
        self._is_running = False
        if self._loop and self._loop.is_running():
            logging.info("Requesting asyncio loop stop via call_soon_threadsafe...")
            self._loop.call_soon_threadsafe(self._loop.stop)


# --- Main GUI Window ---
class SocialMediaUploaderGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Social Media Uploader - 支持定时上传")
        self.setMinimumSize(700, 550)

        self.settings = QSettings(ORGANIZATION_NAME, APPLICATION_NAME)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget) # Set layout directly on widget

        self.init_ui()
        self.setup_connections()
        self.update_account_history()

        self.thread = None
        self.worker = None

        logging.info("SocialMediaUploaderGUI initialized.")

    def init_ui(self):
        # Platform selection
        platform_group = QGroupBox("平台设置")
        platform_layout = QVBoxLayout()
        self.platform_label = QLabel("选择平台:")
        self.platform_combo = QComboBox()
        try: self.platform_combo.addItems(get_supported_social_media())
        except Exception as e: # Catch broader exceptions during init
             logging.warning(f"获取支持平台失败: {e}, 使用默认列表。", exc_info=True)
             self.platform_combo.addItems(["抖音", "快手", "视频号", "TikTok"])

        self.account_label = QLabel("账号名称 (输入或选择):")
        self.account_combo = QComboBox()
        self.account_combo.setEditable(True)
        self.account_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        completer = QCompleter(self) # Create completer with parent
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        completer.setModel(self.account_combo.model()) # Set model for completer
        self.account_combo.setCompleter(completer) # Assign completer

        platform_layout.addWidget(self.platform_label)
        platform_layout.addWidget(self.platform_combo)
        platform_layout.addWidget(self.account_label)
        platform_layout.addWidget(self.account_combo)
        platform_group.setLayout(platform_layout)

        # Action buttons
        action_group = QGroupBox("操作")
        action_layout = QHBoxLayout()
        self.login_btn = QPushButton("登录账号")
        self.upload_btn = QPushButton("上传视频")
        self.schedule_btn = QPushButton("定时上传")
        action_layout.addWidget(self.login_btn)
        action_layout.addWidget(self.upload_btn)
        action_layout.addWidget(self.schedule_btn)
        action_group.setLayout(action_layout)

        # Video selection
        video_group = QGroupBox("视频设置")
        video_layout = QVBoxLayout()
        self.video_label = QLabel("视频文件:")
        self.video_path_input = QLineEdit()
        self.video_path_input.setReadOnly(True)
        self.browse_btn = QPushButton("选择文件...")
        file_layout = QHBoxLayout()
        file_layout.addWidget(self.video_path_input)
        file_layout.addWidget(self.browse_btn)
        video_layout.addWidget(self.video_label)
        video_layout.addLayout(file_layout)
        video_group.setLayout(video_layout)

        # Schedule settings
        self.schedule_group = QGroupBox("定时上传设置")
        schedule_layout = QVBoxLayout()
        self.publish_type_group = QGroupBox("发布方式")
        publish_type_layout = QHBoxLayout()
        self.immediate_radio = QRadioButton("立即发布")
        self.immediate_radio.setChecked(True)
        self.scheduled_radio = QRadioButton("定时发布")
        publish_type_layout.addWidget(self.immediate_radio)
        publish_type_layout.addWidget(self.scheduled_radio)
        self.publish_type_group.setLayout(publish_type_layout)

        self.schedule_time_group = QGroupBox("定时设置")
        schedule_time_layout = QVBoxLayout()
        self.schedule_label = QLabel("发布时间:")
        self.schedule_datetime = QDateTimeEdit()
        self.schedule_datetime.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        self.schedule_datetime.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.schedule_datetime.setCalendarPopup(True)
        self.schedule_datetime.setEnabled(False)

        self.repeat_check = QCheckBox("重复上传")
        self.repeat_check.setEnabled(False)
        self.repeat_interval = QLineEdit()
        self.repeat_interval.setPlaceholderText("间隔(分钟)")
        self.repeat_interval.setEnabled(False)
        self.repeat_times = QLineEdit()
        self.repeat_times.setPlaceholderText("次数")
        self.repeat_times.setEnabled(False)
        repeat_layout = QHBoxLayout()
        repeat_layout.addWidget(self.repeat_check)
        repeat_layout.addWidget(QLabel("间隔:"))
        repeat_layout.addWidget(self.repeat_interval)
        repeat_layout.addWidget(QLabel("分钟, 次数:"))
        repeat_layout.addWidget(self.repeat_times)
        repeat_layout.addStretch()
        schedule_time_layout.addWidget(self.schedule_label)
        schedule_time_layout.addWidget(self.schedule_datetime)
        schedule_time_layout.addLayout(repeat_layout)
        self.schedule_time_group.setLayout(schedule_time_layout)
        self.schedule_time_group.setEnabled(False)

        schedule_layout.addWidget(self.publish_type_group)
        schedule_layout.addWidget(self.schedule_time_group)
        self.schedule_group.setLayout(schedule_layout)

        self.layout.addWidget(platform_group)
        self.layout.addWidget(action_group)
        self.layout.addWidget(video_group)
        self.layout.addWidget(self.schedule_group)
        self.layout.addStretch()

        self.status_bar = self.statusBar()
        self.status_bar.showMessage("准备就绪", 5000)

    def setup_connections(self):
        self.login_btn.clicked.connect(self.handle_login)
        self.upload_btn.clicked.connect(self.handle_upload)
        self.schedule_btn.clicked.connect(self.handle_schedule)
        self.browse_btn.clicked.connect(self.browse_video_file)

        self.immediate_radio.toggled.connect(self.toggle_schedule_options)
        self.repeat_check.toggled.connect(self.toggle_repeat_options)
        self.platform_combo.currentIndexChanged.connect(self.update_account_history)
        # Ensure completer model updates when items change
        self.account_combo.model().rowsInserted.connect(self.update_completer_model)
        self.account_combo.model().rowsRemoved.connect(self.update_completer_model)


    def update_completer_model(self):
        """Updates the completer's model when the QComboBox model changes."""
        if self.account_combo.completer():
            self.account_combo.completer().setModel(self.account_combo.model())
            logging.debug("Completer model updated.")


    # --- Account History Methods ---
    def load_account_history(self, platform):
        if not platform: return []
        key = f"{SETTINGS_HISTORY_PREFIX}{platform}"
        history = self.settings.value(key, [])
        if isinstance(history, str): history = [history] if history else []
        logging.debug(f"Loaded history for {platform}: {history}")
        return history

    def save_account_to_history(self, platform, account):
        account = account.strip()
        if not platform or not account: return
        key = f"{SETTINGS_HISTORY_PREFIX}{platform}"
        history = self.load_account_history(platform)
        if account not in history:
            history.append(account)
            self.settings.setValue(key, history)
            self.settings.sync()
            logging.info(f"Saved account '{account}' for platform '{platform}'")
            self.update_account_history(select_account=account) # Update UI

    def update_account_history(self, select_account=None):
        current_platform = self.platform_combo.currentText()
        history = self.load_account_history(current_platform)
        current_text = select_account if select_account else self.account_combo.currentText()

        self.account_combo.blockSignals(True)
        # Store current line edit text if different from combo items
        edit_text = self.account_combo.lineEdit().text() if self.account_combo.isEditable() else ""

        self.account_combo.clear()
        if history: self.account_combo.addItems(history)

        # Try to restore selection or typed text
        index = self.account_combo.findText(current_text)
        if index != -1:
            self.account_combo.setCurrentIndex(index)
        elif current_text and self.account_combo.isEditable():
            # Restore only if it was explicitly passed or was in line edit
            if select_account or (edit_text and edit_text == current_text):
                 self.account_combo.lineEdit().setText(current_text)
            else:
                 self.account_combo.setCurrentIndex(-1) # Don't restore if just random text
        else:
             self.account_combo.setCurrentIndex(-1)

        self.account_combo.blockSignals(False)
        # Explicitly update completer model after clear/addItems
        self.update_completer_model()


    # --- UI Toggles ---
    def toggle_schedule_options(self, checked):
        schedule_enabled = not checked
        self.schedule_time_group.setEnabled(schedule_enabled)
        # These are inside schedule_time_group, no need to toggle individually
        # self.schedule_datetime.setEnabled(schedule_enabled)
        # self.repeat_check.setEnabled(schedule_enabled)
        if not schedule_enabled:
            # Ensure repeat check and fields are disabled too
            if self.repeat_check.isChecked(): # Only change if needed
                self.repeat_check.setChecked(False)
            else: # Still need to disable fields if check was already false
                self.toggle_repeat_options(False)
        else:
            self.toggle_repeat_options(self.repeat_check.isChecked())

    def toggle_repeat_options(self, checked):
        # Enable only if checkbox is checked AND parent group is enabled
        enabled = checked and self.schedule_time_group.isEnabled()
        self.repeat_interval.setEnabled(enabled)
        self.repeat_times.setEnabled(enabled)

    # --- File Browsing ---
    def browse_video_file(self):
        start_dir = self.settings.value("last_video_dir", str(Path.home()))
        file_path, _ = QFileDialog.getOpenFileName(self, "选择视频文件", start_dir,
                                                   "视频文件 (*.mp4 *.mov *.avi *.mkv)")
        if file_path:
            self.video_path_input.setText(file_path)
            self.settings.setValue("last_video_dir", str(Path(file_path).parent))
            self.settings.sync()

    # --- Input Validation ---
    def validate_inputs(self, check_video=True):
        platform = self.platform_combo.currentText()
        if not platform:
             QMessageBox.warning(self, "警告", "请选择一个平台!")
             return False, None

        account_name = self.account_combo.currentText().strip()
        if not account_name:
            QMessageBox.warning(self, "警告", "账号名称不能为空!")
            self.account_combo.setFocus()
            return False, None

        if check_video:
            video_path = self.video_path_input.text()
            if not video_path:
                QMessageBox.warning(self, "警告", "请选择视频文件!")
                self.browse_btn.setFocus()
                return False, account_name
            if not exists(video_path):
                QMessageBox.warning(self, "警告", f"找不到视频文件: {video_path}")
                self.browse_btn.setFocus()
                return False, account_name

        if self.scheduled_radio.isChecked():
            schedule_dt = self.schedule_datetime.dateTime()
            if schedule_dt <= QDateTime.currentDateTime().addSecs(30):
                QMessageBox.warning(self, "警告", "发布时间必须是将来的时间 (至少半分钟后)!")
                self.schedule_datetime.setFocus()
                return False, account_name

            if self.repeat_check.isChecked():
                interval_text = self.repeat_interval.text().strip()
                times_text = self.repeat_times.text().strip()
                error_field = None
                try:
                    if not interval_text: error_field = self.repeat_interval; raise ValueError("间隔时间未填写")
                    interval = int(interval_text)
                    if interval <= 0: error_field = self.repeat_interval; raise ValueError("间隔时间必须大于0")
                    if not times_text: error_field = self.repeat_times; raise ValueError("重复次数未填写")
                    times = int(times_text)
                    if times <= 0: error_field = self.repeat_times; raise ValueError("重复次数必须大于0")
                except ValueError as e:
                    QMessageBox.warning(self, "警告", f"重复设置无效: {e}!")
                    if error_field: error_field.setFocus()
                    else: (self.repeat_interval if not interval_text else self.repeat_times).setFocus()
                    return False, account_name

        return True, account_name

    # --- Async Task Logic (Core Business Logic) ---
    async def async_login(self, platform, account_name):
        logging.info(f"Async: Attempting login for {account_name} on {platform}")
        account_file = Path(BASE_DIR) / "cookies" / f"{platform}_{account_name}.json"
        account_file.parent.mkdir(parents=True, exist_ok=True)
        if platform == SOCIAL_MEDIA_DOUYIN: await douyin_setup(str(account_file), handle=True)
        elif platform == SOCIAL_MEDIA_TIKTOK: await tiktok_setup(str(account_file), handle=True)
        elif platform == SOCIAL_MEDIA_TENCENT: await weixin_setup(str(account_file), handle=True)
        elif platform == SOCIAL_MEDIA_KUAISHOU: await ks_setup(str(account_file), handle=True)
        else: raise ValueError(f"不支持的平台: {platform}")
        logging.info(f"Async: Login logic completed for {account_name} on {platform}")

    async def async_upload(self, platform, account_name, video_file, scheduled=False):
        logging.info(f"Async: Starting upload for {account_name} on {platform}. Scheduled: {scheduled}")
        account_file = Path(BASE_DIR) / "cookies" / f"{platform}_{account_name}.json"
        if not account_file.exists():
             raise FileNotFoundError(f"账号 {account_name} 的 Cookie 文件不存在 ({account_file}). 请先登录.")

        video_path_obj = Path(video_file)
        title, tags = get_title_and_hashtags(str(video_path_obj))
        publish_date_obj = 0 # Default to 0 for immediate, or None if uploader prefers

        if scheduled and self.scheduled_radio.isChecked():
            publish_date_obj = self.schedule_datetime.dateTime().toPython() # Python datetime
            schedule_str = publish_date_obj.strftime('%Y-%m-%d %H:%M:%S')

            if self.repeat_check.isChecked():
                interval = int(self.repeat_interval.text()) * 60
                times = int(self.repeat_times.text())
                logging.info(f"Async: Starting repeat task ({times}x, {interval}s interval). First at: {schedule_str}")
                for i in range(times):
                    current_publish_dt = publish_date_obj + timedelta(seconds=i * interval)
                    current_schedule_str = current_publish_dt.strftime('%Y-%m-%d %H:%M:%S')
                    logging.info(f"Async: Repeat {i+1}/{times}. Scheduled for: {current_schedule_str}")
                    if current_publish_dt < datetime.now():
                        logging.warning(f"Calculated repeat time {current_schedule_str} is in the past. Trying anyway.")
                    try:
                        app = self._get_uploader_instance(platform, account_file, title, str(video_path_obj), tags, current_publish_dt)
                        await app.main()
                        logging.info(f"Async: Repeat {i+1}/{times} upload successful.")
                        if i < times - 1:
                            logging.info(f"Async: Waiting for {interval} seconds before next repeat...")
                            await asyncio.sleep(interval)
                    except Exception as e_inner:
                        error_msg = f"第 {i + 1}/{times} 次重复上传失败: {e_inner.__class__.__name__}: {e_inner}"
                        logging.error(error_msg, exc_info=True)
                        raise RuntimeError(error_msg) from e_inner
                logging.info(f"Async: Repeat upload task completed for {account_name}.")
                return # End function for repeat logic
            else: # Single scheduled upload
                logging.info(f"Async: Single scheduled upload at {schedule_str}")
                app = self._get_uploader_instance(platform, account_file, title, str(video_path_obj), tags, publish_date_obj)
                await app.main()
        else: # Immediate upload
            logging.info("Async: Immediate upload task")
            app = self._get_uploader_instance(platform, account_file, title, str(video_path_obj), tags, publish_date_obj) # Pass 0 or None
            await app.main()
        logging.info(f"Async: Upload logic completed for {account_name} on {platform}")


    # --- THIS METHOD IS UPDATED ---
    def _get_uploader_instance(self, platform, account_file, title, video_file_str, tags, publish_date):
        """Helper to create the correct uploader instance."""
        logging.info(f"Creating uploader instance for {platform} with publish_date: {publish_date}")
        account_file_str = str(account_file) # Ensure cookie path is string

        try:
            # --- Special handling for DouYinVideo based on example/error ---
            if platform == SOCIAL_MEDIA_DOUYIN:
                logging.debug(f"Instantiating DouYinVideo positionally: title='{title}', "
                              f"file='{video_file_str}', tags={tags}, publish_date={publish_date}, "
                              f"cookie='{account_file_str}'")
                # Call with positional arguments matching the example:
                # DouYinVideo(title, file_path, tags, publish_date, cookie_path)
                return DouYinVideo(title, video_file_str, tags, publish_date, account_file_str)

            # --- For other platforms, assume they accept keyword arguments ---
            # --- (If they also fail, they need similar positional adjustments) ---
            else:
                # Prepare common keyword arguments for others
                common_args = {
                    "title": title,
                    "file_path": video_file_str, # Use 'file_path' keyword
                    "tags": tags,
                    "publish_date": publish_date,
                    "cookie_path": account_file_str # Use 'cookie_path' keyword
                }

                if platform == SOCIAL_MEDIA_TIKTOK:
                    logging.debug(f"Instantiating TiktokVideo with keywords: {common_args}")
                    return TiktokVideo(**common_args)
                elif platform == SOCIAL_MEDIA_TENCENT:
                    category = TencentZoneTypes.LIFESTYLE.value
                    logging.debug(f"Instantiating TencentVideo with keywords: {common_args}, category={category}")
                    # Add category specific keyword argument
                    return TencentVideo(**common_args, category=category)
                elif platform == SOCIAL_MEDIA_KUAISHOU:
                     logging.debug(f"Instantiating KSVideo with keywords: {common_args}")
                     return KSVideo(**common_args)
                else:
                     # This case should ideally not be reached if platform list is correct
                     raise ValueError(f"不支持的平台实例创建: {platform}")

        except NameError as e:
             logging.error(f"Uploader class for {platform} not found. {e}", exc_info=True)
             raise ImportError(f"无法找到平台 {platform} 的上传器类。") from e
        except TypeError as e:
            logging.error(f"Mismatch constructing {platform} uploader. Error: {e}. "
                          f"Provided args (approx): title={title}, file={video_file_str}, "
                          f"tags={tags}, pub_date={publish_date}, cookie={account_file_str}",
                          exc_info=True)
            raise TypeError(f"创建平台 {platform} 上传器实例时参数不匹配: {e}") from e
        except Exception as e:
            logging.error(f"Unexpected error creating {platform} uploader instance: {e}", exc_info=True)
            raise RuntimeError(f"创建 {platform} 上传器时发生未知错误") from e


    # --- Button Handlers ---
    def handle_login(self):
        valid, account_name = self.validate_inputs(check_video=False)
        if not valid: return
        platform = self.platform_combo.currentText()
        self.show_message(f"正在尝试登录 {account_name} 到 {platform}...")
        self.run_async_task(self.async_login, platform=platform, account_name=account_name)

    def handle_upload(self):
        valid, account_name = self.validate_inputs(check_video=True)
        if not valid: return
        platform = self.platform_combo.currentText()
        video_file = self.video_path_input.text()
        self.show_message(f"准备立即上传视频到 {platform} ({account_name})...")
        self.run_async_task(self.async_upload, platform=platform, account_name=account_name, video_file=video_file, scheduled=False)

    def handle_schedule(self):
        valid, account_name = self.validate_inputs(check_video=True)
        if not valid: return
        if not self.scheduled_radio.isChecked():
            QMessageBox.information(self, "提示", "请先选择'定时发布'选项并设置有效的发布时间。")
            return

        platform = self.platform_combo.currentText()
        video_file = self.video_path_input.text()
        schedule_dt_str = self.schedule_datetime.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        repeat_info = ""
        if self.repeat_check.isChecked():
             interval = self.repeat_interval.text().strip() or "?"
             times = self.repeat_times.text().strip() or "?"
             repeat_info = f" (重复 {times} 次, 间隔 {interval} 分钟)"
        self.show_message(f"准备定时上传视频到 {platform} ({account_name}) 于 {schedule_dt_str}{repeat_info}...")
        self.run_async_task(self.async_upload, platform=platform, account_name=account_name, video_file=video_file, scheduled=True)

    # --- Async Task Management ---
    def run_async_task(self, coro_func, *args, **kwargs):
        if self.thread and self.thread.isRunning():
             logging.warning("上一个任务仍在运行，请等待其完成后再试。")
             QMessageBox.warning(self, "操作繁忙", "上一个后台任务仍在运行，请稍后再试。")
             return # Prevent starting a new task while one is running

        # Set object names for easier debugging in logs
        thread_name = f"WorkerThread-{int(time.time())}"
        worker_name = f"AsyncWorker-{int(time.time())}"

        self.thread = QThread()
        self.thread.setObjectName(thread_name) # Name the thread
        self.worker = AsyncWorker(coro_func, *args, **kwargs)
        self.worker.setObjectName(worker_name) # Name the worker
        self.worker.moveToThread(self.thread)

        # Connections
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit) # Worker done -> tell thread to quit
        # Use a direct connection for cleanup on thread finish if possible,
        # otherwise on_thread_finished remains reliable.
        self.thread.finished.connect(self.worker.deleteLater) # Clean up worker when thread finishes
        self.thread.finished.connect(self.thread.deleteLater) # Clean up thread itself
        self.thread.finished.connect(self.on_thread_finished) # Also call our slot for button re-enabling

        # Worker signals to GUI slots
        self.worker.error.connect(self.show_error)
        self.worker.message.connect(self.show_message)
        self.worker.success.connect(self.save_account_to_history)

        self.set_buttons_enabled(False)
        self.thread.start()
        logging.info(f"新异步任务已启动 on thread {thread_name}.")

    def on_thread_finished(self):
        """Slot called when the QThread itself finishes execution."""
        logging.info(f"QThread finished signal received for thread {self.sender().objectName() if self.sender() else 'Unknown'}.")
        # Re-enable buttons. Use timer to ensure deleteLater calls are processed.
        QTimer.singleShot(100, lambda: self.set_buttons_enabled(True))
        # Nullify references after they are scheduled for deletion
        self.worker = None
        self.thread = None
        logging.info("异步任务线程已完成清理调度，按钮将很快重新启用。")

    def set_buttons_enabled(self, enabled):
        logging.debug(f"Setting buttons enabled: {enabled}")
        self.login_btn.setEnabled(enabled)
        self.upload_btn.setEnabled(enabled)
        self.schedule_btn.setEnabled(enabled)
        self.browse_btn.setEnabled(enabled)
        self.platform_combo.setEnabled(enabled)
        self.account_combo.setEnabled(enabled)
        # Enable/disable the entire schedule group first
        self.schedule_group.setEnabled(enabled)
        if enabled:
             # If enabling main group, restore sub-group state based on radio
             self.toggle_schedule_options(self.immediate_radio.isChecked())
        # No need for else, disabling schedule_group disables children


    # --- Status/Error Display ---
    def show_error(self, message):
        logging.error(f"GUI Error Display: {message}")
        try:
            QMessageBox.critical(self, "错误", message)
            self.status_bar.showMessage(f"错误: {message}", 10000)
        except Exception as e:
            logging.error(f"无法显示错误弹窗/状态栏: {e}")

    def show_message(self, message):
        logging.info(f"GUI Status: {message}")
        try:
            self.status_bar.showMessage(message, 5000)
        except Exception as e:
            logging.error(f"无法显示状态栏消息: {e}")

    # --- Window Closing ---
    def closeEvent(self, event):
        if self.thread and self.thread.isRunning():
            reply = QMessageBox.question(self, '退出确认',
                                           "后台任务正在运行，确定要强制退出吗？\n（任务将被中断）",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                           QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                logging.info("正在停止运行中的任务以退出...")
                if self.worker: self.worker.stop()
                self.thread.quit() # Request thread quit
                # Give it a bit more time, but don't hang indefinitely
                if not self.thread.wait(2500):
                     logging.warning("后台任务未能及时停止。可能需要强制终止。")
                     # self.thread.terminate() # Last resort
                logging.info("任务已尝试停止，正在退出。")
                event.accept()
            else:
                logging.info("退出取消。")
                event.ignore()
        else:
            event.accept()


# --- Main Execution ---
if __name__ == "__main__":
    # Set explicitly for QSettings if needed, especially on Linux/macOS
    QApplication.setOrganizationName(ORGANIZATION_NAME)
    QApplication.setApplicationName(APPLICATION_NAME)

    app = QApplication(sys.argv)

    # --- Check for Base Directory Existence ---
    try:
        # Check if BASE_DIR is defined and is a directory
        if 'BASE_DIR' not in globals() or not isinstance(BASE_DIR, (str, Path)) or not Path(BASE_DIR).is_dir():
             raise FileNotFoundError(f"BASE_DIR ('{BASE_DIR if 'BASE_DIR' in globals() else 'Not Defined'}') "
                                     "未在 conf.py 中定义或不是有效目录")
        # Ensure cookies subdirectory exists
        (Path(BASE_DIR) / "cookies").mkdir(parents=True, exist_ok=True)
        logging.info(f"Base directory checked: {BASE_DIR}")
    except NameError: # Should be caught by the check above now
         msg = "配置错误： 'BASE_DIR' 变量未找到。"
         logging.critical(msg)
         QMessageBox.critical(None, "启动错误", msg + "\n请检查 conf.py。")
         sys.exit(1)
    except FileNotFoundError as e:
         msg = f"配置错误： {e}。"
         logging.critical(msg)
         QMessageBox.critical(None, "启动错误", msg + "\n请检查 conf.py 中的 BASE_DIR 设置。")
         sys.exit(1)
    except Exception as e:
         msg = f"初始化时发生意外错误: {e}"
         logging.critical(msg, exc_info=True)
         QMessageBox.critical(None, "启动错误", msg)
         sys.exit(1)

    # --- Run the GUI ---
    try:
        window = SocialMediaUploaderGUI()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        logging.critical("启动 GUI 时发生未处理的异常:", exc_info=True)
        try:
            QMessageBox.critical(None, "严重错误", f"无法启动应用程序:\n{e}")
        except:
            pass # Ignore errors showing the error message itself
        sys.exit(1)