import asyncio
from datetime import datetime
from os.path import exists
from pathlib import Path
import sys

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QComboBox, QLineEdit, QPushButton, QFileDialog,
                               QGroupBox, QRadioButton, QDateTimeEdit, QMessageBox, QCheckBox)
from PySide6.QtCore import Qt, QDateTime, QThread, Signal, QObject

from conf import BASE_DIR
from uploader.douyin_uploader.main import douyin_setup, DouYinVideo
from uploader.ks_uploader.main import ks_setup, KSVideo
from uploader.tencent_uploader.main import weixin_setup, TencentVideo
from uploader.tk_uploader.main_chrome import tiktok_setup, TiktokVideo
from utils.base_social_media import get_supported_social_media, SOCIAL_MEDIA_DOUYIN, \
    SOCIAL_MEDIA_TENCENT, SOCIAL_MEDIA_TIKTOK, SOCIAL_MEDIA_KUAISHOU
from utils.constant import TencentZoneTypes
from utils.files_times import get_title_and_hashtags


class AsyncWorker(QObject):
    finished = Signal()
    error = Signal(str)
    message = Signal(str)
    progress = Signal(int)

    def __init__(self, coro):
        super().__init__()
        self.coro = coro

    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.coro)
            self.message.emit("操作成功完成")
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()
            if loop.is_running():
                loop.close()


class SocialMediaUploaderGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Social Media Uploader - 支持定时上传")
        self.setMinimumSize(700, 500)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        # Platform selection
        platform_group = QGroupBox("平台设置")
        platform_layout = QVBoxLayout()

        self.platform_label = QLabel("选择平台:")
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(get_supported_social_media())

        self.account_label = QLabel("账号名称:")
        self.account_input = QLineEdit()
        self.account_input.setPlaceholderText("例如: xiaoA")

        platform_layout.addWidget(self.platform_label)
        platform_layout.addWidget(self.platform_combo)
        platform_layout.addWidget(self.account_label)
        platform_layout.addWidget(self.account_input)
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

        # Immediate or scheduled
        self.publish_type_group = QGroupBox("发布方式")
        publish_type_layout = QHBoxLayout()

        self.immediate_radio = QRadioButton("立即发布")
        self.immediate_radio.setChecked(True)
        self.scheduled_radio = QRadioButton("定时发布")

        publish_type_layout.addWidget(self.immediate_radio)
        publish_type_layout.addWidget(self.scheduled_radio)
        self.publish_type_group.setLayout(publish_type_layout)

        # Schedule time
        self.schedule_time_group = QGroupBox("定时设置")
        schedule_time_layout = QVBoxLayout()

        self.schedule_label = QLabel("发布时间:")
        self.schedule_datetime = QDateTimeEdit()
        self.schedule_datetime.setDateTime(QDateTime.currentDateTime().addSecs(3600))  # 默认1小时后
        self.schedule_datetime.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.schedule_datetime.setEnabled(False)

        # Repeat options
        self.repeat_check = QCheckBox("重复上传")
        self.repeat_interval = QLineEdit()
        self.repeat_interval.setPlaceholderText("间隔时间(分钟)")
        self.repeat_interval.setEnabled(False)
        self.repeat_times = QLineEdit()
        self.repeat_times.setPlaceholderText("重复次数")
        self.repeat_times.setEnabled(False)

        repeat_layout = QHBoxLayout()
        repeat_layout.addWidget(self.repeat_check)
        repeat_layout.addWidget(self.repeat_interval)
        repeat_layout.addWidget(self.repeat_times)

        schedule_time_layout.addWidget(self.schedule_label)
        schedule_time_layout.addWidget(self.schedule_datetime)
        schedule_time_layout.addLayout(repeat_layout)
        self.schedule_time_group.setLayout(schedule_time_layout)

        schedule_layout.addWidget(self.publish_type_group)
        schedule_layout.addWidget(self.schedule_time_group)
        self.schedule_group.setLayout(schedule_layout)

        # Add all groups to main layout
        self.layout.addWidget(platform_group)
        self.layout.addWidget(action_group)
        self.layout.addWidget(video_group)
        self.layout.addWidget(self.schedule_group)
        self.layout.addStretch()

        # Status bar
        self.status_bar = self.statusBar()

    def setup_connections(self):
        self.login_btn.clicked.connect(self.handle_login)
        self.upload_btn.clicked.connect(self.handle_upload)
        self.schedule_btn.clicked.connect(self.handle_schedule)
        self.browse_btn.clicked.connect(self.browse_video_file)

        self.immediate_radio.toggled.connect(self.toggle_schedule_options)
        self.scheduled_radio.toggled.connect(self.toggle_schedule_options)
        self.repeat_check.toggled.connect(self.toggle_repeat_options)

    def toggle_schedule_options(self):
        enabled = self.scheduled_radio.isChecked()
        self.schedule_datetime.setEnabled(enabled)
        self.repeat_check.setEnabled(enabled)

    def toggle_repeat_options(self):
        enabled = self.repeat_check.isChecked()
        self.repeat_interval.setEnabled(enabled)
        self.repeat_times.setEnabled(enabled)

    def browse_video_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择视频文件", "", "视频文件 (*.mp4 *.mov *.avi)")
        if file_path:
            self.video_path_input.setText(file_path)

    def validate_inputs(self, check_video=True):
        if not self.account_input.text():
            QMessageBox.warning(self, "警告", "账号名称不能为空!")
            return False

        if check_video and not self.video_path_input.text():
            QMessageBox.warning(self, "警告", "请选择视频文件!")
            return False

        if check_video and not exists(self.video_path_input.text()):
            QMessageBox.warning(self, "警告", f"找不到视频文件: {self.video_path_input.text()}")
            return False

        if self.scheduled_radio.isChecked():
            if self.schedule_datetime.dateTime() <= QDateTime.currentDateTime():
                QMessageBox.warning(self, "警告", "发布时间必须是将来的时间!")
                return False

            if self.repeat_check.isChecked():
                try:
                    interval = int(self.repeat_interval.text())
                    if interval <= 0:
                        QMessageBox.warning(self, "警告", "间隔时间必须大于0分钟!")
                        return False

                    times = int(self.repeat_times.text())
                    if times <= 0:
                        QMessageBox.warning(self, "警告", "重复次数必须大于0!")
                        return False
                except ValueError:
                    QMessageBox.warning(self, "警告", "请输入有效的数字!")
                    return False

        return True

    async def async_login(self):
        platform = self.platform_combo.currentText()
        account_name = self.account_input.text()

        account_file = Path(BASE_DIR / "cookies" / f"{platform}_{account_name}.json")
        account_file.parent.mkdir(exist_ok=True)

        try:
            if platform == SOCIAL_MEDIA_DOUYIN:
                await douyin_setup(str(account_file), handle=True)
            elif platform == SOCIAL_MEDIA_TIKTOK:
                await tiktok_setup(str(account_file), handle=True)
            elif platform == SOCIAL_MEDIA_TENCENT:
                await weixin_setup(str(account_file), handle=True)
            elif platform == SOCIAL_MEDIA_KUAISHOU:
                await ks_setup(str(account_file), handle=True)

            self.status_bar.showMessage(f"成功登录 {account_name} 到 {platform}", 5000)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"登录失败: {str(e)}")

    async def async_upload(self, scheduled=False):
        platform = self.platform_combo.currentText()
        account_name = self.account_input.text()
        video_file = self.video_path_input.text()

        account_file = Path(BASE_DIR / "cookies" / f"{platform}_{account_name}.json")
        title, tags = get_title_and_hashtags(video_file)

        if scheduled and self.scheduled_radio.isChecked():
            qdatetime = self.schedule_datetime.dateTime()
            publish_date = datetime(
                qdatetime.date().year(), qdatetime.date().month(), qdatetime.date().day(),
                qdatetime.time().hour(), qdatetime.time().minute(), qdatetime.time().second()
            )

            if self.repeat_check.isChecked():
                interval = int(self.repeat_interval.text()) * 60  # 转换为秒
                times = int(self.repeat_times.text())

                for i in range(times):
                    try:
                        if platform == SOCIAL_MEDIA_DOUYIN:
                            await douyin_setup(account_file, handle=False)
                            app = DouYinVideo(title, video_file, tags, publish_date, account_file)
                        elif platform == SOCIAL_MEDIA_TIKTOK:
                            await tiktok_setup(account_file, handle=True)
                            app = TiktokVideo(title, video_file, tags, publish_date, account_file)
                        elif platform == SOCIAL_MEDIA_TENCENT:
                            await weixin_setup(account_file, handle=True)
                            category = TencentZoneTypes.LIFESTYLE.value
                            app = TencentVideo(title, video_file, tags, publish_date, account_file, category)
                        elif platform == SOCIAL_MEDIA_KUAISHOU:
                            await ks_setup(account_file, handle=True)
                            app = KSVideo(title, video_file, tags, publish_date, account_file)

                        await app.main()
                        self.status_bar.showMessage(f"第{i + 1}次定时上传成功: {account_name} @ {platform}", 5000)

                        # 等待间隔时间
                        if i < times - 1:
                            await asyncio.sleep(interval)
                            publish_date = datetime.fromtimestamp(datetime.now().timestamp() + interval)

                    except Exception as e:
                        QMessageBox.critical(self, "错误", f"第{i + 1}次上传失败: {str(e)}")
                        break

                return
        else:
            publish_date = 0  # 立即发布

        try:
            if platform == SOCIAL_MEDIA_DOUYIN:
                await douyin_setup(account_file, handle=False)
                app = DouYinVideo(title, video_file, tags, publish_date, account_file)
            elif platform == SOCIAL_MEDIA_TIKTOK:
                await tiktok_setup(account_file, handle=True)
                app = TiktokVideo(title, video_file, tags, publish_date, account_file)
            elif platform == SOCIAL_MEDIA_TENCENT:
                await weixin_setup(account_file, handle=True)
                category = TencentZoneTypes.LIFESTYLE.value
                app = TencentVideo(title, video_file, tags, publish_date, account_file, category)
            elif platform == SOCIAL_MEDIA_KUAISHOU:
                await ks_setup(account_file, handle=True)
                app = KSVideo(title, video_file, tags, publish_date, account_file)

            await app.main()
            self.status_bar.showMessage(f"上传成功: {account_name} @ {platform}", 5000)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"上传失败: {str(e)}")

    def handle_login(self):
        if not self.validate_inputs(check_video=False):
            return

        self.run_async_task(self.async_login())

    def handle_upload(self):
        if not self.validate_inputs():
            return

        self.run_async_task(self.async_upload(scheduled=False))

    def handle_schedule(self):
        if not self.validate_inputs():
            return

        if not self.scheduled_radio.isChecked():
            QMessageBox.information(self, "提示", "请先选择定时发布选项并设置时间")
            return

        self.run_async_task(self.async_upload(scheduled=True))

    def run_async_task(self, coro):
        self.thread = QThread()
        self.worker = AsyncWorker(coro)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.error.connect(self.show_error)
        self.worker.message.connect(self.show_message)

        # 禁用按钮防止重复操作
        self.set_buttons_enabled(False)
        self.thread.finished.connect(lambda: self.set_buttons_enabled(True))

        self.thread.start()

    def set_buttons_enabled(self, enabled):
        self.login_btn.setEnabled(enabled)
        self.upload_btn.setEnabled(enabled)
        self.schedule_btn.setEnabled(enabled)

    def show_error(self, message):
        QMessageBox.critical(self, "错误", message)

    def show_message(self, message):
        self.status_bar.showMessage(message, 5000)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SocialMediaUploaderGUI()
    window.show()
    sys.exit(app.exec())