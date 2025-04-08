# -*- coding: utf-8 -*-
import asyncio
from datetime import datetime, timedelta
from os.path import exists, join
from pathlib import Path
import sys
import json
import logging
import time
import glob

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLabel, QLineEdit, QPushButton, QFileDialog,
                               QGroupBox, QRadioButton, QDateTimeEdit, QMessageBox, QCheckBox,
                               QCompleter, QComboBox,
                               QSpacerItem, QSizePolicy)
from PySide6.QtCore import (Qt, QDateTime, QThread, Signal, QObject, QSettings,
                           QTimer, Slot)

from uploader.bilibili_uploader.main import BiliBiliUploader, bilibili_setup

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s')

# --- Project Imports ---
try:
    from conf import BASE_DIR
    from uploader.douyin_uploader.main import douyin_setup, DouYinVideo
    from uploader.ks_uploader.main import ks_setup, KSVideo
    from uploader.tencent_uploader.main import weixin_setup, TencentVideo
    from uploader.tk_uploader.main_chrome import tiktok_setup, TiktokVideo
    from utils.base_social_media import get_supported_social_media, SOCIAL_MEDIA_DOUYIN, \
    SOCIAL_MEDIA_TENCENT, SOCIAL_MEDIA_TIKTOK, SOCIAL_MEDIA_KUAISHOU, SOCIAL_MEDIA_BILIBILI
    from utils.constant import TencentZoneTypes
    from utils.files_times import get_title_and_hashtags
except ImportError as e:
    logging.critical(f"关键模块导入失败。请确保项目结构正确且依赖已安装。 Import Error: {e}", exc_info=True)
    try:
        app_temp = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(None, "启动错误", f"关键模块导入失败: {e}\n请检查环境和项目路径。")
    except Exception as me: print(f"无法显示错误弹窗: {me}")
    sys.exit(f"关键模块导入失败: {e}")

# --- Constants for QSettings ---
ORGANIZATION_NAME = "YourOrganizationName"
APPLICATION_NAME = "SocialMediaUploader"
SETTINGS_TYPED_ACCOUNT_HISTORY = "typed_account_history"
COOKIES_DIR = Path(BASE_DIR) / "cookies"

# --- Async Worker ---
class AsyncWorker(QObject):
    finished = Signal()
    error = Signal(str)
    message = Signal(str)
    progress = Signal(str)
    login_success = Signal(str, str) # platform, account_name

    def __init__(self, coro_func, *args, **kwargs):
        super().__init__()
        self.coro_func = coro_func
        self.args = args
        self.kwargs = kwargs
        self._is_running = True
        self._loop = None
        self.kwargs['worker_instance'] = self

    async def run_wrapper(self):
        final_message = "操作已完成"
        try:
            result_message = await self.coro_func(*self.args, **self.kwargs)
            if result_message and isinstance(result_message, str): final_message = result_message
            if self._is_running: self.message.emit(final_message)
        except Exception as e:
            logging.exception("异步任务执行出错:")
            if self._is_running: self.error.emit(f"操作失败: {e.__class__.__name__}: {e}")
        finally:
            if self._is_running: self.finished.emit()

    def run(self):
        thread_name = QThread.currentThread().objectName() or "UnknownThread"
        logging.info(f"AsyncWorker starting run method on thread: {thread_name}")
        if not self._is_running: logging.warning("Worker run called but already stopped."); return
        self._finished_emitted = False
        try:
            self._loop = asyncio.new_event_loop(); asyncio.set_event_loop(self._loop)
            logging.info(f"Asyncio loop created/set for thread {thread_name}")
            self._loop.run_until_complete(self.run_wrapper())
            logging.info(f"Asyncio run_until_complete finished on thread {thread_name}")
        except Exception as e:
            logging.exception("设置或运行异步循环时出错:")
            if self._is_running:
                self.error.emit(f"异步任务运行时出错: {e.__class__.__name__}: {e}")
                if not self._finished_emitted: self.finished.emit(); self._finished_emitted = True
        finally:
            logging.info(f"AsyncWorker run method finally block on thread {thread_name}")
            if self._loop:
                try:
                    if self._loop.is_running(): self._loop.call_soon_threadsafe(self._loop.stop)
                    self._loop.close(); logging.info("Asyncio loop closed.")
                except Exception as e: logging.error(f"关闭 asyncio 循环时出错: {e}", exc_info=True)
                self._loop = None
            if self._is_running and not self._finished_emitted: self.finished.emit()
            self._finished_emitted = True

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
        self.setWindowTitle("Social Media Multi-Uploader v2.2")
        self.setMinimumSize(700, 600)
        self.settings = QSettings(ORGANIZATION_NAME, APPLICATION_NAME)
        COOKIES_DIR.mkdir(parents=True, exist_ok=True)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.platform_checkboxes = {}
        self.init_ui()
        self.setup_connections()
        self.load_accounts_and_update_combo()
        self.thread = None; self.worker = None
        logging.info(f"SocialMediaUploaderGUI initialized using Org='{ORGANIZATION_NAME}', App='{APPLICATION_NAME}'")

    def init_ui(self):
        # Platform Selection (Checkboxes)
        platform_group = QGroupBox("平台选择")
        platform_layout = QGridLayout()
        try:
            supported_platforms = get_supported_social_media(); col_count = 3
            for i, platform in enumerate(supported_platforms):
                checkbox = QCheckBox(platform); self.platform_checkboxes[platform] = checkbox
                platform_layout.addWidget(checkbox, i // col_count, i % col_count)
        except Exception as e:
             logging.warning(f"获取支持平台失败: {e}, 使用默认列表。", exc_info=True)
             supported_platforms = ["抖音", "快手", "视频号", "TikTok"]
             for i, p in enumerate(supported_platforms): checkbox = QCheckBox(p); self.platform_checkboxes[p] = checkbox; platform_layout.addWidget(checkbox, 0, i)
        platform_group.setLayout(platform_layout)

        # Account Input (ComboBox with History)
        account_group = QGroupBox("账号设置")
        account_layout = QHBoxLayout(); self.account_label = QLabel("账号名称:")
        self.account_combo = QComboBox(); self.account_combo.setEditable(True); self.account_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        completer = QCompleter(self); completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion); self.account_combo.setCompleter(completer)
        self.login_btn = QPushButton("登录选中平台")
        account_layout.addWidget(self.account_label); account_layout.addWidget(self.account_combo, 1); account_layout.addWidget(self.login_btn)
        account_group.setLayout(account_layout)

        # Action Buttons (Multi-Platform)
        action_group = QGroupBox("批量操作 (应用于所有勾选平台)")
        action_layout = QHBoxLayout(); self.upload_btn = QPushButton("立即上传"); self.schedule_btn = QPushButton("定时上传")
        action_layout.addWidget(self.upload_btn); action_layout.addWidget(self.schedule_btn); action_group.setLayout(action_layout)

        # Video Selection
        video_group = QGroupBox("视频设置")
        video_layout = QVBoxLayout(); self.video_label = QLabel("视频文件:"); self.video_path_input = QLineEdit(); self.video_path_input.setReadOnly(True); self.browse_btn = QPushButton("选择文件...")
        file_layout = QHBoxLayout(); file_layout.addWidget(self.video_path_input); file_layout.addWidget(self.browse_btn)
        video_layout.addWidget(self.video_label); video_layout.addLayout(file_layout); video_group.setLayout(video_layout)

        # Schedule Settings
        self.schedule_group = QGroupBox("定时上传设置")
        schedule_layout = QVBoxLayout()
        self.publish_type_group = QGroupBox("发布方式"); publish_type_layout = QHBoxLayout(); self.immediate_radio = QRadioButton("立即发布"); self.immediate_radio.setChecked(True); self.scheduled_radio = QRadioButton("定时发布"); publish_type_layout.addWidget(self.immediate_radio); publish_type_layout.addWidget(self.scheduled_radio); self.publish_type_group.setLayout(publish_type_layout)
        self.schedule_time_group = QGroupBox("定时设置 (所有选中平台使用相同设置)"); schedule_time_layout = QVBoxLayout(); self.schedule_label = QLabel("发布时间:"); self.schedule_datetime = QDateTimeEdit(); self.schedule_datetime.setDateTime(QDateTime.currentDateTime().addSecs(3600)); self.schedule_datetime.setDisplayFormat("yyyy-MM-dd HH:mm:ss"); self.schedule_datetime.setCalendarPopup(True); self.schedule_datetime.setEnabled(False)
        self.repeat_check = QCheckBox("重复上传 (所有选中平台)"); self.repeat_check.setEnabled(False); self.repeat_interval = QLineEdit(); self.repeat_interval.setPlaceholderText("间隔(分钟)"); self.repeat_interval.setEnabled(False); self.repeat_times = QLineEdit(); self.repeat_times.setPlaceholderText("次数"); self.repeat_times.setEnabled(False)
        repeat_layout = QHBoxLayout(); repeat_layout.addWidget(self.repeat_check); repeat_layout.addWidget(QLabel("间隔:")); repeat_layout.addWidget(self.repeat_interval); repeat_layout.addWidget(QLabel("分钟, 次数:")); repeat_layout.addWidget(self.repeat_times); repeat_layout.addStretch()
        schedule_time_layout.addWidget(self.schedule_label); schedule_time_layout.addWidget(self.schedule_datetime); schedule_time_layout.addLayout(repeat_layout); self.schedule_time_group.setLayout(schedule_time_layout); self.schedule_time_group.setEnabled(False)
        schedule_layout.addWidget(self.publish_type_group); schedule_layout.addWidget(self.schedule_time_group); self.schedule_group.setLayout(schedule_layout)

        # Layout
        self.layout.addWidget(platform_group); self.layout.addWidget(account_group); self.layout.addWidget(action_group)
        self.layout.addWidget(video_group); self.layout.addWidget(self.schedule_group); self.layout.addStretch()
        self.status_bar = self.statusBar(); self.status_bar.showMessage("准备就绪", 5000)

    def setup_connections(self):
        self.login_btn.clicked.connect(self.handle_login)
        self.upload_btn.clicked.connect(self.handle_upload)
        self.schedule_btn.clicked.connect(self.handle_schedule)
        self.browse_btn.clicked.connect(self.browse_video_file)
        self.immediate_radio.toggled.connect(self.toggle_schedule_options)
        self.repeat_check.toggled.connect(self.toggle_repeat_options)
        self.account_combo.model().rowsInserted.connect(self.update_completer_model)
        self.account_combo.model().rowsRemoved.connect(self.update_completer_model)

    def update_completer_model(self):
        completer = self.account_combo.completer()
        if completer:
            if completer.model() != self.account_combo.model():
                completer.setModel(self.account_combo.model())
            logging.debug("Completer model updated/verified.")

    # --- Account Scanning and History ---
    def scan_accounts_from_cookies(self) -> list[str]:
        """Scans COOKIES_DIR for platform_accountname.json files and extracts account names."""
        accounts = set()
        try:
            for cookie_file in COOKIES_DIR.glob('*_*.json'):
                filename = cookie_file.stem
                parts = filename.split('_', 1)
                if len(parts) == 2 and parts[1]: accounts.add(parts[1])
                else: logging.warning(f"无法从文件名解析账号: {cookie_file.name}")
        except Exception as e: logging.error(f"扫描 Cookie 文件时出错: {e}", exc_info=True)
        found_list = sorted(list(accounts))
        logging.info(f"从 Cookie 文件扫描到的账号: {found_list}")
        return found_list

    def load_accounts_and_update_combo(self):
        """Loads accounts from cookie files AND typed history, then updates the ComboBox."""
        accounts_from_files = set(self.scan_accounts_from_cookies())
        typed_history = self.settings.value(SETTINGS_TYPED_ACCOUNT_HISTORY, [])
        if isinstance(typed_history, str): typed_history = [typed_history] if typed_history else []
        accounts_from_settings = set(typed_history)
        logging.info(f"从设置加载的已输入账号历史 (Key: {SETTINGS_TYPED_ACCOUNT_HISTORY}): {accounts_from_settings}")

        combined_accounts = sorted(list(accounts_from_files.union(accounts_from_settings)))
        logging.info(f"合并后的账号列表: {combined_accounts}")

        self.account_combo.blockSignals(True)
        current_line_edit_text = self.account_combo.lineEdit().text() if self.account_combo.isEditable() else ""
        current_combo_text = self.account_combo.currentText()
        self.account_combo.clear()
        if combined_accounts: self.account_combo.addItems(combined_accounts); self.update_completer_model()
        text_to_restore = current_line_edit_text or current_combo_text
        index = self.account_combo.findText(text_to_restore)
        if index != -1: self.account_combo.setCurrentIndex(index); logging.debug(f"Restored account selection: {text_to_restore}")
        elif text_to_restore and self.account_combo.isEditable() and current_line_edit_text: self.account_combo.lineEdit().setText(text_to_restore); logging.debug(f"Restored account line edit text: {text_to_restore}")
        else: self.account_combo.setCurrentIndex(-1)
        self.account_combo.blockSignals(False)

    @Slot(str, str)
    def save_account_to_typed_history(self, platform: str, account_name: str):
        """Adds account_name to the TYPED history in QSettings if it's new."""
        account_name = account_name.strip()
        if not account_name: return
        logging.info(f"收到登录成功信号: 平台='{platform}', 账号='{account_name}' - 尝试保存到已输入历史 (Key: {SETTINGS_TYPED_ACCOUNT_HISTORY})...")
        history = self.settings.value(SETTINGS_TYPED_ACCOUNT_HISTORY, [])
        if isinstance(history, str): history = [history] if history else []
        if account_name not in history:
            history.append(account_name)
            self.settings.setValue(SETTINGS_TYPED_ACCOUNT_HISTORY, history); self.settings.sync()
            logging.info(f"已添加账号 '{account_name}' 到已输入历史。")
            self.load_accounts_and_update_combo() # Refresh combo after saving
            index = self.account_combo.findText(account_name)
            if index != -1: self.account_combo.setCurrentIndex(index)
        else:
            logging.debug(f"账号 '{account_name}' 已存在于已输入历史中，无需重复添加。")
            # Refresh anyway, in case file scan changed
            self.load_accounts_and_update_combo()
            index = self.account_combo.findText(account_name)
            if index != -1: self.account_combo.setCurrentIndex(index)

    # --- UI Toggles ---
    def toggle_schedule_options(self, checked):
        schedule_enabled = not checked
        self.schedule_time_group.setEnabled(schedule_enabled)
        if not schedule_enabled:
            if self.repeat_check.isChecked(): self.repeat_check.setChecked(False)
            else: self.toggle_repeat_options(False)
        else: self.toggle_repeat_options(self.repeat_check.isChecked())

    def toggle_repeat_options(self, checked):
        enabled = checked and self.schedule_time_group.isEnabled()
        self.repeat_interval.setEnabled(enabled); self.repeat_times.setEnabled(enabled)

    # --- File Browsing ---
    def browse_video_file(self):
        start_dir = self.settings.value("last_video_dir", str(Path.home()))
        file_path, _ = QFileDialog.getOpenFileName(self, "选择视频文件", start_dir, "视频文件 (*.mp4 *.mov *.avi *.mkv)")
        if file_path:
            self.video_path_input.setText(file_path)
            self.settings.setValue("last_video_dir", str(Path(file_path).parent)); self.settings.sync()

    # --- Input Validation ---
    def get_checked_platforms(self) -> list[str]:
        return [name for name, checkbox in self.platform_checkboxes.items() if checkbox.isChecked()]

    def validate_inputs(self, check_video=True, check_login=False) -> tuple[bool, list[str], str | None]:
        checked_platforms = self.get_checked_platforms()
        account_name = self.account_combo.currentText().strip()
        if not checked_platforms: QMessageBox.warning(self, "警告", "请至少勾选一个目标平台!"); return False, [], None
        if not account_name: QMessageBox.warning(self, "警告", "请输入账号名称!"); self.account_combo.setFocus(); return False, checked_platforms, None
        if check_video:
            video_path = self.video_path_input.text()
            if not video_path: QMessageBox.warning(self, "警告", "请选择视频文件!"); self.browse_btn.setFocus(); return False, checked_platforms, account_name
            if not exists(video_path): QMessageBox.warning(self, "警告", f"找不到视频文件: {video_path}"); self.browse_btn.setFocus(); return False, checked_platforms, account_name
        if check_login:
            missing = [p for p in checked_platforms if not (COOKIES_DIR / f"{p}_{account_name}.json").exists()]
            if missing: QMessageBox.warning(self, "登录检查", f"账号 '{account_name}' 在以下平台缺少 Cookie 文件:\n{', '.join(missing)}\n请先登录。"); return False, checked_platforms, account_name
        if self.scheduled_radio.isChecked():
            schedule_dt = self.schedule_datetime.dateTime()
            if schedule_dt <= QDateTime.currentDateTime().addSecs(30): QMessageBox.warning(self, "警告", "发布时间必须是将来时间!"); self.schedule_datetime.setFocus(); return False, checked_platforms, account_name
            if self.repeat_check.isChecked():
                try: interval = int(self.repeat_interval.text().strip()); assert interval > 0; times = int(self.repeat_times.text().strip()); assert times > 0
                except (ValueError, AssertionError, TypeError) as e: QMessageBox.warning(self, "警告", f"重复设置无效: {e}! 请输入正整数。"); (self.repeat_interval if not self.repeat_interval.text().strip() else self.repeat_times).setFocus(); return False, checked_platforms, account_name
        return True, checked_platforms, account_name

    # --- Async Task Logic ---
    async def async_login(self, platforms: list[str], account_name: str, worker_instance: AsyncWorker | None = None):
        logging.info(f"Async: Attempting login for account '{account_name}' on platforms: {platforms}")
        success_count = 0; failed_platforms = []
        for platform in platforms:
            if not worker_instance or not worker_instance._is_running: break
            target_cookie_file = COOKIES_DIR / f"{platform}_{account_name}.json"
            target_cookie_file.parent.mkdir(parents=True, exist_ok=True)
            msg_start = f"平台 '{platform}': 开始为账号 '{account_name}' 登录..."
            logging.info(f"Async: {msg_start}"); worker_instance.progress.emit(msg_start) if worker_instance else None
            try:
                if platform == SOCIAL_MEDIA_DOUYIN: await douyin_setup(str(target_cookie_file), handle=True)
                elif platform == SOCIAL_MEDIA_TIKTOK: await tiktok_setup(str(target_cookie_file), handle=True)
                elif platform == SOCIAL_MEDIA_TENCENT: await weixin_setup(str(target_cookie_file), handle=True)
                elif platform == SOCIAL_MEDIA_KUAISHOU: await ks_setup(str(target_cookie_file), handle=True)
                elif platform == SOCIAL_MEDIA_BILIBILI: await bilibili_setup(str(target_cookie_file), handle=True).main()
                else: raise ValueError(f"不支持的平台: {platform}")
                await asyncio.sleep(0.5)
                if target_cookie_file.exists() and target_cookie_file.stat().st_size > 0:
                     msg_success = f"平台 '{platform}', 账号 '{account_name}': 登录成功。"
                     logging.info(f"Async: {msg_success}")
                     if worker_instance: worker_instance.progress.emit(msg_success); worker_instance.login_success.emit(platform, account_name)
                     success_count += 1
                else: raise RuntimeError("登录过程未成功创建有效的 Cookie 文件。")
            except Exception as e:
                msg_fail = f"平台 '{platform}', 账号 '{account_name}': 登录失败! 原因: {e.__class__.__name__}: {e}"
                logging.error(f"Async: {msg_fail}", exc_info=True)
                if worker_instance: worker_instance.progress.emit(msg_fail)
                failed_platforms.append(platform)
        summary = f"登录完成。成功: {success_count}/{len(platforms)}。"
        if failed_platforms: summary += f" 失败平台: {', '.join(failed_platforms)}。"
        return summary

    async def async_upload(self, platforms: list[str], account_name: str, video_file: str, scheduled: bool, worker_instance: AsyncWorker | None = None):
        logging.info(f"Async: Starting multi-upload for account '{account_name}' to {len(platforms)} platforms. Scheduled: {scheduled}")
        video_path_obj = Path(video_file); title, tags = get_title_and_hashtags(str(video_path_obj)); publish_date_obj = 0
        if scheduled and self.scheduled_radio.isChecked():
            publish_date_obj = self.schedule_datetime.dateTime().toPython()
            if self.repeat_check.isChecked():
                interval = int(self.repeat_interval.text()) * 60; times = int(self.repeat_times.text())
                logging.info(f"Repeat task detected: {times}x, interval {interval}s"); success_summary = {p: 0 for p in platforms}; failure_summary = {p: 0 for p in platforms}
                for repeat_num in range(times):
                    if not worker_instance or not worker_instance._is_running: break
                    current_publish_dt = publish_date_obj + timedelta(seconds=repeat_num * interval); current_schedule_str = current_publish_dt.strftime('%Y-%m-%d %H:%M:%S')
                    msg = f"开始第 {repeat_num+1}/{times} 次重复上传 (账号: {account_name}, 时间: {current_schedule_str})..."
                    logging.info(f"Async: {msg}"); worker_instance.progress.emit(msg) if worker_instance else None
                    iter_success, iter_fail = await self._perform_single_upload_iteration(platforms, account_name, video_path_obj, title, tags, current_publish_dt, worker_instance)
                    for p, count in iter_success.items(): success_summary[p] += count;
                    for p, count in iter_fail.items(): failure_summary[p] += count
                    if repeat_num < times - 1:
                        if not worker_instance or not worker_instance._is_running: break
                        wait_msg = f"第 {repeat_num+1}/{times} 次上传完成，等待 {interval} 秒..."
                        logging.info(f"Async: {wait_msg}"); worker_instance.progress.emit(wait_msg) if worker_instance else None
                        try: await asyncio.sleep(interval)
                        except asyncio.CancelledError: logging.warning("等待间隔被取消。"); break
                success_count = sum(success_summary.values()); fail_count = sum(failure_summary.values()); total_attempts = times * len(platforms)
                summary_msg = f"重复上传完成 ({times}次)。总尝试: {total_attempts}, 成功: {success_count}, 失败: {fail_count}。"
                failed_plats = [f"{p}({c})" for p, c in failure_summary.items() if c > 0];
                if failed_plats: summary_msg += f" 失败详情: {', '.join(failed_plats)}"; logging.info(f"Async: {summary_msg}"); return summary_msg
            else: schedule_str = publish_date_obj.strftime('%Y-%m-%d %H:%M:%S'); logging.info(f"Async: Single scheduled upload for '{account_name}' at {schedule_str}"); success_summary, failure_summary = await self._perform_single_upload_iteration(platforms, account_name, video_path_obj, title, tags, publish_date_obj, worker_instance)
        else: logging.info(f"Async: Immediate upload task for account '{account_name}'"); publish_date_obj = 0; success_summary, failure_summary = await self._perform_single_upload_iteration(platforms, account_name, video_path_obj, title, tags, publish_date_obj, worker_instance)
        success_count = sum(success_summary.values()); fail_count = sum(failure_summary.values())
        summary_msg = f"多平台上传完成。成功: {success_count}/{len(platforms)}。"
        failed_plats = [p for p, c in failure_summary.items() if c > 0];
        if failed_plats: summary_msg += f" 失败平台: {', '.join(failed_plats)}"; logging.info(f"Async: {summary_msg}"); return summary_msg

    async def _perform_single_upload_iteration( self, platforms: list[str], account_name: str, video_path_obj: Path, title: str, tags: list, publish_date_obj: datetime | int, worker_instance: AsyncWorker | None) -> tuple[dict, dict]:
        success = {p: 0 for p in platforms}; failure = {p: 0 for p in platforms}
        for platform in platforms:
            if not worker_instance or not worker_instance._is_running: break
            msg_start = f"平台 '{platform}', 账号 '{account_name}': 开始上传..."
            logging.info(f"Async: {msg_start}"); worker_instance.progress.emit(msg_start) if worker_instance else None
            try:
                cookie_file = COOKIES_DIR / f"{platform}_{account_name}.json"
                if not cookie_file.exists(): raise FileNotFoundError(f"未找到平台 '{platform}' 账号 '{account_name}' 的 Cookie 文件。")
                app = self._get_uploader_instance(platform, cookie_file, title, str(video_path_obj), tags, publish_date_obj)
                await app.main()
                msg_success = f"平台 '{platform}', 账号 '{account_name}': 上传成功。"
                logging.info(f"Async: {msg_success}"); worker_instance.progress.emit(msg_success) if worker_instance else None
                success[platform] += 1
            except Exception as e_inner:
                msg_fail = f"平台 '{platform}', 账号 '{account_name}': 上传失败! 原因: {e_inner.__class__.__name__}: {e_inner}"
                logging.error(f"Async: {msg_fail}", exc_info=True); worker_instance.progress.emit(msg_fail) if worker_instance else None
                failure[platform] += 1
        return success, failure

    def _get_uploader_instance(self, platform, account_file_path: Path, title, video_file_str, tags, publish_date):
        logging.info(f"Creating uploader instance for {platform} using cookie {account_file_path} with publish_date: {publish_date}")
        account_file_str = str(account_file_path)
        try:
            if platform == SOCIAL_MEDIA_DOUYIN: account_name = account_file_path.stem.split('_', 1)[1] if '_' in account_file_path.stem else 'Unknown'; logging.debug(f"Instantiating DouYinVideo positionally: title='{title}', file='{video_file_str}', tags={tags}, publish_date={publish_date}, cookie='{account_file_str}' (Account: {account_name})"); return DouYinVideo(title, video_file_str, tags, publish_date, account_file_str)
            else: common_args = { "title": title, "file_path": video_file_str, "tags": tags, "publish_date": publish_date, "cookie_path": account_file_str };
            if platform == SOCIAL_MEDIA_TIKTOK: return TiktokVideo(**common_args)
            elif platform == SOCIAL_MEDIA_TENCENT: return TencentVideo(**common_args, category=TencentZoneTypes.LIFESTYLE.value)
            elif platform == SOCIAL_MEDIA_KUAISHOU: return KSVideo(**common_args)
            elif platform == SOCIAL_MEDIA_BILIBILI: return BiliBiliUploader(**common_args)
            else: raise ValueError(f"不支持的平台实例创建: {platform}")
        except Exception as e: logging.error(f"Error creating {platform} uploader instance: {e}", exc_info=True); raise type(e)(f"创建 {platform} 上传器实例时出错: {e}") from e

    # --- Button Handlers ---
    def handle_login(self):
        checked_platforms = self.get_checked_platforms(); account_name = self.account_combo.currentText().strip()
        if not checked_platforms: QMessageBox.warning(self, "登录错误", "请至少勾选一个要登录的平台。"); return
        if not account_name: QMessageBox.warning(self, "登录错误", "请输入要登录的账号名称。"); self.account_combo.setFocus(); return
        self.show_message(f"准备为账号 '{account_name}' 登录 {len(checked_platforms)} 个平台..."); self.run_async_task(self.async_login, platforms=checked_platforms, account_name=account_name)
    def handle_upload(self):
        valid, platforms, account_name = self.validate_inputs(check_video=True, check_login=True);
        if not valid: return
        video_file = self.video_path_input.text(); self.show_message(f"准备使用账号 '{account_name}' 立即上传到 {len(platforms)} 个平台..."); self.run_async_task(self.async_upload, platforms=platforms, account_name=account_name, video_file=video_file, scheduled=False)
    def handle_schedule(self):
        valid, platforms, account_name = self.validate_inputs(check_video=True, check_login=True);
        if not valid: return
        if not self.scheduled_radio.isChecked(): QMessageBox.information(self, "提示", "请先选择'定时发布'选项。"); return
        video_file = self.video_path_input.text(); schedule_dt_str = self.schedule_datetime.dateTime().toString("yyyy-MM-dd HH:mm:ss"); repeat_info = ""
        if self.repeat_check.isChecked(): repeat_info = f" (重复 {self.repeat_times.text().strip() or '?'} 次, 间隔 {self.repeat_interval.text().strip() or '?'} 分钟)"
        self.show_message(f"准备使用账号 '{account_name}' 定时上传到 {len(platforms)} 个平台 ({schedule_dt_str}{repeat_info})..."); self.run_async_task(self.async_upload, platforms=platforms, account_name=account_name, video_file=video_file, scheduled=True)

    # --- Async Task Management ---
    def run_async_task(self, coro_func, *args, **kwargs):
        if self.thread and self.thread.isRunning(): QMessageBox.warning(self, "操作繁忙", "上一个后台任务仍在运行..."); return
        thread_name = f"WorkerThread-{int(time.time())}"; worker_name = f"AsyncWorker-{int(time.time())}"
        self.thread = QThread(); self.thread.setObjectName(thread_name)
        kwargs_with_worker = kwargs.copy(); kwargs_with_worker['worker_instance'] = None
        self.worker = AsyncWorker(coro_func, *args, **kwargs_with_worker); self.worker.setObjectName(worker_name)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit, Qt.ConnectionType.QueuedConnection)
        self.thread.finished.connect(self.worker.deleteLater); self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.on_thread_finished)
        self.worker.error.connect(self.show_error); self.worker.message.connect(self.show_message)
        self.worker.progress.connect(self.show_progress)
        # Connect to the renamed slot
        self.worker.login_success.connect(self.save_account_to_typed_history)
        self.set_buttons_enabled(False); self.thread.start(); logging.info(f"新异步任务已启动 on thread {thread_name}.")

    def on_thread_finished(self):
        sender_obj = self.sender()
        sender_name = sender_obj.objectName() if sender_obj else 'Unknown'
        logging.info(f"QThread finished signal received for thread {sender_name}.")
        QTimer.singleShot(150, lambda: self.set_buttons_enabled(True))
        self.worker = None; self.thread = None; logging.info("异步任务线程已完成清理调度，按钮将很快重新启用。")

    def set_buttons_enabled(self, enabled):
        logging.debug(f"Setting buttons enabled: {enabled}")
        self.login_btn.setEnabled(enabled); self.upload_btn.setEnabled(enabled); self.schedule_btn.setEnabled(enabled); self.browse_btn.setEnabled(enabled)
        for checkbox in self.platform_checkboxes.values(): checkbox.setEnabled(enabled)
        self.account_combo.setEnabled(enabled); self.schedule_group.setEnabled(enabled)
        if enabled: self.toggle_schedule_options(self.immediate_radio.isChecked())

    # --- Status/Error Display (Formatted Correctly) ---
    def show_error(self, message):
        """Displays an error message in a dialog and the status bar."""
        logging.error(f"GUI Error Display: {message}")
        try:
            QMessageBox.critical(self, "错误", message)
            if hasattr(self, 'status_bar') and self.status_bar:
                 self.status_bar.showMessage(f"错误: {message}", 10000)
        except Exception as e:
            logging.error(f"无法显示错误弹窗/状态栏: {e}")

    def show_message(self, message): # Final messages
        """Displays a final status message in the status bar."""
        logging.info(f"GUI Status (Final): {message}")
        try:
            if hasattr(self, 'status_bar') and self.status_bar:
                self.status_bar.showMessage(message, 8000)
        except Exception as e:
            logging.error(f"无法显示状态栏消息: {e}")

    def show_progress(self, message): # Intermediate messages
        """Displays an intermediate progress message in the status bar."""
        logging.info(f"GUI Status (Progress): {message}")
        try:
            if hasattr(self, 'status_bar') and self.status_bar:
                self.status_bar.showMessage(message, 4000)
        except Exception as e:
            logging.error(f"无法显示进度状态栏消息: {e}")

    # --- Window Closing ---
    def closeEvent(self, event):
        if self.thread and self.thread.isRunning():
            reply = QMessageBox.question(self, '退出确认', "后台任务正在运行，确定要强制退出吗？\n（任务将被中断）", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes: logging.info("正在停止运行中的任务以退出..."); self.worker.stop() if self.worker else None; self.thread.quit(); self.thread.wait(2500); logging.info("任务已尝试停止，正在退出。"); event.accept()
            else: event.ignore()
        else: event.accept()

# --- Main Execution (Formatted Correctly) ---
if __name__ == "__main__":
    # Set Application Info
    QApplication.setOrganizationName(ORGANIZATION_NAME)
    QApplication.setApplicationName(APPLICATION_NAME)
    QApplication.setStyle("Fusion")
    app = QApplication(sys.argv)

    # Check Base Directory
    try:
        if 'BASE_DIR' not in globals() or not isinstance(BASE_DIR, (str, Path)) or not Path(BASE_DIR).is_dir():
            raise FileNotFoundError(f"BASE_DIR ('{BASE_DIR if 'BASE_DIR' in globals() else 'Not Defined'}') 未在 conf.py 中定义或不是有效目录")
        # Ensure cookies dir exists
        COOKIES_DIR.mkdir(parents=True, exist_ok=True)
        logging.info(f"Base directory checked and cookies directory ensured: {BASE_DIR}")
    except Exception as e:
        # Correctly formatted exception handling
        msg = f"配置检查失败: {e}。\n请检查 conf.py 中的 BASE_DIR 设置。"
        logging.critical(msg, exc_info=True)
        try:
            QMessageBox.critical(None, "启动错误", msg)
        except Exception as mb_error:
            print(f"无法显示错误弹窗: {mb_error}") # Fallback print
        sys.exit(1) # Exit after handling

    # Run the GUI
    try:
        window = SocialMediaUploaderGUI()
        window.show()
        exit_code = app.exec()
        logging.info(f"Application finished with exit code {exit_code}")
        sys.exit(exit_code)
    except Exception as e:
        # Correctly formatted exception handling
        logging.critical("启动 GUI 时发生未处理的异常:", exc_info=True)
        try:
            QMessageBox.critical(None, "严重错误", f"无法启动应用程序:\n{e}")
        except Exception as mb_error:
            print(f"无法显示错误弹窗: {mb_error}") # Fallback print
        sys.exit(1) # Exit after handling