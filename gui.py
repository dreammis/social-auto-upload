import asyncio
from datetime import datetime
from os.path import exists
from pathlib import Path
import sys

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QComboBox, QLineEdit, QPushButton, QFileDialog,
                               QGroupBox, QRadioButton, QDateTimeEdit, QMessageBox)
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
        self.setWindowTitle("Social Media Uploader")
        self.setMinimumSize(600, 400)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        # Platform selection
        platform_group = QGroupBox("Platform Settings")
        platform_layout = QVBoxLayout()

        self.platform_label = QLabel("Select Platform:")
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(get_supported_social_media())

        self.account_label = QLabel("Account Name:")
        self.account_input = QLineEdit()
        self.account_input.setPlaceholderText("e.g., xiaoA")

        platform_layout.addWidget(self.platform_label)
        platform_layout.addWidget(self.platform_combo)
        platform_layout.addWidget(self.account_label)
        platform_layout.addWidget(self.account_input)
        platform_group.setLayout(platform_layout)

        # Action selection
        action_group = QGroupBox("Action")
        action_layout = QVBoxLayout()

        self.login_btn = QPushButton("Login")
        self.upload_btn = QPushButton("Upload Video")

        action_layout.addWidget(self.login_btn)
        action_layout.addWidget(self.upload_btn)
        action_group.setLayout(action_layout)

        # Upload settings (initially hidden)
        self.upload_group = QGroupBox("Upload Settings")
        upload_layout = QVBoxLayout()

        # Video file selection
        self.video_label = QLabel("Video File:")
        self.video_path_input = QLineEdit()
        self.video_path_input.setReadOnly(True)
        self.browse_btn = QPushButton("Browse...")

        file_layout = QHBoxLayout()
        file_layout.addWidget(self.video_path_input)
        file_layout.addWidget(self.browse_btn)

        # Publish options
        self.publish_now_radio = QRadioButton("Publish Now")
        self.publish_now_radio.setChecked(True)
        self.schedule_radio = QRadioButton("Schedule Publish")

        self.schedule_datetime = QDateTimeEdit()
        self.schedule_datetime.setDateTime(QDateTime.currentDateTime())
        self.schedule_datetime.setEnabled(False)

        publish_layout = QVBoxLayout()
        publish_layout.addWidget(self.publish_now_radio)
        publish_layout.addWidget(self.schedule_radio)
        publish_layout.addWidget(self.schedule_datetime)

        upload_layout.addWidget(self.video_label)
        upload_layout.addLayout(file_layout)
        upload_layout.addLayout(publish_layout)
        self.upload_group.setLayout(upload_layout)
        self.upload_group.setVisible(False)

        # Add all groups to main layout
        self.layout.addWidget(platform_group)
        self.layout.addWidget(action_group)
        self.layout.addWidget(self.upload_group)
        self.layout.addStretch()

        # Status bar
        self.status_bar = self.statusBar()

    def setup_connections(self):
        self.login_btn.clicked.connect(self.handle_login)
        self.upload_btn.clicked.connect(self.toggle_upload_settings)
        self.browse_btn.clicked.connect(self.browse_video_file)

        self.publish_now_radio.toggled.connect(
            lambda: self.schedule_datetime.setEnabled(not self.publish_now_radio.isChecked()))
        self.schedule_radio.toggled.connect(lambda: self.schedule_datetime.setEnabled(self.schedule_radio.isChecked()))

    def toggle_upload_settings(self):
        self.upload_group.setVisible(not self.upload_group.isVisible())
        if not self.upload_group.isVisible():
            self.upload_btn.setText("Upload Video")
        else:
            self.upload_btn.setText("Hide Upload Settings")

    def browse_video_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Video File", "", "Video Files (*.mp4 *.mov *.avi)")
        if file_path:
            self.video_path_input.setText(file_path)

    def validate_inputs(self):
        if not self.account_input.text():
            QMessageBox.warning(self, "Warning", "Account name cannot be empty!")
            return False

        if self.upload_group.isVisible() and not self.video_path_input.text():
            QMessageBox.warning(self, "Warning", "Please select a video file!")
            return False

        if self.upload_group.isVisible() and not exists(self.video_path_input.text()):
            QMessageBox.warning(self, "Warning", f"Could not find the video file at {self.video_path_input.text()}")
            return False

        if (self.upload_group.isVisible() and self.schedule_radio.isChecked() and
                self.schedule_datetime.dateTime() <= QDateTime.currentDateTime()):
            QMessageBox.warning(self, "Warning", "Schedule time must be in the future!")
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

            self.status_bar.showMessage(f"Successfully logged in to {account_name} on {platform}", 5000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Login failed: {str(e)}")

    async def async_upload(self):
        platform = self.platform_combo.currentText()
        account_name = self.account_input.text()
        video_file = self.video_path_input.text()

        account_file = Path(BASE_DIR / "cookies" / f"{platform}_{account_name}.json")
        title, tags = get_title_and_hashtags(video_file)

        if self.publish_now_radio.isChecked():
            publish_date = 0
        else:
            qdatetime = self.schedule_datetime.dateTime()
            publish_date = datetime(
                qdatetime.date().year(), qdatetime.date().month(), qdatetime.date().day(),
                qdatetime.time().hour(), qdatetime.time().minute()
            )

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
            else:
                QMessageBox.critical(self, "Error", "Unsupported platform")
                return

            await app.main()
            self.status_bar.showMessage(f"Successfully uploaded video to {account_name} on {platform}", 5000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Upload failed: {str(e)}")

    def handle_login(self):
        if not self.validate_inputs():
            return

        # 创建并启动工作线程
        self.run_async_task(self.async_login())

    def handle_upload(self):
        if not self.validate_inputs():
            return

        self.run_async_task(self.async_upload())

    def run_async_task(self, coro):
        # 创建工作线程
        self.thread = QThread()
        self.worker = AsyncWorker(coro)
        self.worker.moveToThread(self.thread)

        # 连接信号
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.error.connect(self.show_error)
        self.worker.message.connect(self.show_message)

        # 开始线程
        self.thread.start()

        # 禁用按钮防止重复点击
        self.login_btn.setEnabled(False)
        self.upload_btn.setEnabled(False)
        self.thread.finished.connect(
            lambda: [
                self.login_btn.setEnabled(True),
                self.upload_btn.setEnabled(True)
            ]
        )

    def show_error(self, message):
        QMessageBox.critical(self, "Error", message)

    def show_message(self, message):
        self.status_bar.showMessage(message, 5000)


def main():
    app = QApplication(sys.argv)
    window = SocialMediaUploaderGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()