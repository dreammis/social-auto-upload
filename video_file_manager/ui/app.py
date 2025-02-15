"""
主应用界面
"""
import gradio as gr
from pathlib import Path
from typing import Dict, Optional, Tuple
import logging
import tkinter as tk
from tkinter import filedialog

from video_file_manager.core.file_manager import FileManager
from video_file_manager.core.metadata_manager import MetadataManager
from video_file_manager.ui.components.file_tree import create_file_tree
from video_file_manager.ui.components.video_info import create_video_info
from video_file_manager.utils.helpers import extract_text_from_video

logger = logging.getLogger(__name__)

class VideoManagerApp:
    def __init__(self):
        """初始化应用"""
        self.default_dir = Path("F:/向阳也有米/24版本/12月")
        self.file_manager = FileManager(self.default_dir) if self.default_dir.exists() else FileManager()
        self.metadata_manager = MetadataManager()
        self.selected_file: Optional[Path] = None
        logger.info(f"初始化应用完成，默认目录：{self.default_dir}")
    
    def on_directory_select(self, directory: str) -> Tuple[str, list]:
        """
        目录选择回调
        
        Args:
            directory: 选中的目录路径
            
        Returns:
            Tuple[str, list]: (目录路径, 文件列表)
        """
        try:
            logger.info(f"选择目录: {directory}")
            if directory:
                self.file_manager = FileManager(Path(directory))
                return directory, self.refresh_files()
            return "", []
        except Exception as e:
            logger.exception(f"切换目录失败: {str(e)}")
            return "", []
    
    def on_file_select(self, evt: gr.SelectData) -> tuple:
        """
        文件选择回调
        
        Args:
            evt: 选择事件数据
            
        Returns:
            tuple: (视频预览, 文本内容, 提取按钮状态, 文件名, 完整路径, 标题, 标签, 描述, 平台信息)
        """
        try:
            logger.debug(f"选择事件数据: {evt}")
            logger.debug(f"选择事件索引: {evt.index}")
            logger.debug(f"选择事件值: {evt.value}")
            
            # 获取选中行的数据
            row_index = evt.index[0]  # 获取选中的行索引
            videos = self.file_manager.scan_videos()  # 获取当前的视频列表
            if not videos or row_index >= len(videos):
                logger.error(f"无效的行索引: {row_index}")
                return None, "", False, "", "", "", "", "", {}  # 注意这里返回9个值
                
            video = videos[row_index]  # 获取选中的视频信息
            logger.debug(f"选中的视频信息: {video}")
            
            # 使用文件管理器中的完整信息
            file_name = video["name"]
            relative_path = video["relative_path"]
            
            logger.debug(f"文件名: {file_name}")
            logger.debug(f"相对路径: {relative_path}")
            
            # 确保使用绝对路径
            base_dir = self.file_manager.base_dir.resolve()
            full_path = base_dir / relative_path
            
            logger.debug(f"基础目录: {base_dir}")
            logger.debug(f"相对路径: {relative_path}")
            logger.info(f"选中文件: {full_path}")
            
            if full_path.is_file():
                self.selected_file = full_path
                metadata = self.metadata_manager.read_metadata(full_path.parent)
                logger.debug(f"元数据信息: {metadata}")
                
                # 返回文件信息和元数据
                return (
                    str(full_path),  # 视频预览路径
                    "",  # 文本内容（初始为空）
                    True,  # 提取按钮状态（可用）
                    file_name,  # 文件名
                    str(full_path),  # 完整路径
                    metadata.get("video_info", {}).get("title", ""),  # 标题
                    ", ".join(metadata.get("video_info", {}).get("tags", [])),  # 标签
                    metadata.get("video_info", {}).get("description", ""),  # 描述
                    metadata.get("platforms", {})  # 平台信息
                )
        except Exception as e:
            logger.exception(f"处理文件选择失败: {str(e)}")
            
        # 如果出现错误，返回空值
        return None, "", False, "", "", "", "", "", {}  # 注意这里返回9个值
    
    def refresh_files(self) -> list:
        """
        刷新文件列表
        
        Returns:
            list: 更新后的文件列表数据
        """
        logger.info("开始刷新文件列表")
        videos = self.file_manager.scan_videos()
        logger.info(f"找到 {len(videos)} 个视频文件")
        logger.debug(f"视频列表: {videos}")
        
        rows = [
            [
                video["name"],
                video["relative_path"],
                video["size"],
                video["modified"].strftime("%Y-%m-%d %H:%M:%S")
            ]
            for video in videos
        ]
        return rows
    
    def select_directory(self) -> str:
        """
        打开目录选择对话框
        
        Returns:
            str: 选中的目录路径
        """
        try:
            root = tk.Tk()
            root.withdraw()  # 隐藏主窗口
            root.attributes('-topmost', True)  # 确保对话框在最前面
            
            directory = filedialog.askdirectory(
                title="选择视频目录",
                initialdir=str(self.file_manager.base_dir),
                parent=root
            )
            
            logger.debug(f"选择的目录: {directory}")
            
            if directory:
                return directory
            return str(self.file_manager.base_dir)
        except Exception as e:
            logger.exception(f"打开目录选择对话框失败: {str(e)}")
            return str(self.file_manager.base_dir)
        finally:
            try:
                root.destroy()  # 确保窗口被销毁
            except Exception:
                pass
    
    def extract_text(self, video_path: str) -> str:
        """
        提取视频文字
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            str: 提取的文字内容
        """
        try:
            if not video_path:
                logger.warning("未提供视频路径")
                return "请先选择视频文件"
            
            logger.info(f"开始提取视频文字，输入路径: {video_path}")
            logger.debug(f"路径类型: {type(video_path)}")
            
            # 确保路径是字符串类型
            if not isinstance(video_path, str):
                video_path = str(video_path)
            
            # 检查路径是否存在
            video_file = Path(video_path)
            logger.debug(f"转换后的路径: {video_file.resolve()}")
            logger.debug(f"文件是否存在: {video_file.exists()}")
            
            text = extract_text_from_video(video_path)
            logger.info("文字提取完成")
            return text
        except Exception as e:
            logger.exception(f"提取文字失败: {str(e)}")
            return f"提取失败: {str(e)}"
    
    def create_ui(self) -> gr.Blocks:
        """
        创建用户界面
        
        Returns:
            gr.Blocks: Gradio界面
        """
        logger.info("开始创建用户界面")
        with gr.Blocks(title="视频文件管理器") as app:
            gr.Markdown("# 视频文件管理器")
            
            with gr.Row():
                # 左侧面板
                with gr.Column(scale=2):
                    gr.Markdown("## 文件目录")
                    with gr.Row():
                        dir_input = gr.Textbox(
                            label="视频目录",
                            placeholder="请选择或输入视频目录路径",
                            value=str(self.default_dir),
                            show_label=True
                        )
                        dir_button = gr.Button("选择目录", variant="secondary")
                    refresh_btn = gr.Button("刷新目录", variant="primary")
                    file_list = create_file_tree({})
                    logger.debug("文件列表组件创建完成")
                
                # 右侧面板
                with gr.Column(scale=3):
                    info_components = create_video_info()
                    logger.debug("信息显示组件创建完成")
            
            # 事件处理
            dir_button.click(
                fn=self.select_directory,
                outputs=dir_input,
                api_name="select_directory"
            ).then(
                fn=self.on_directory_select,
                inputs=dir_input,
                outputs=[dir_input, file_list],
                api_name="update_directory"
            )
            
            refresh_btn.click(
                fn=self.refresh_files,
                outputs=[file_list]
            )
            
            file_list.select(
                fn=self.on_file_select,
                outputs=info_components
            )
            
            # 提取文字按钮事件
            info_components[2].click(  # extract_btn
                fn=self.extract_text,
                inputs=[info_components[4]],  # file_path
                outputs=[info_components[1]]  # transcript_text
            )
            
            logger.info("用户界面创建完成")
        return app

def create_app() -> gr.Blocks:
    """
    创建应用实例
    
    Returns:
        gr.Blocks: Gradio应用界面
    """
    app = VideoManagerApp()
    return app.create_ui()

# 创建全局demo实例
demo = create_app()

# 仅在直接运行时启动服务器
if __name__ == "__main__":
    # 使用标准配置启动
    demo.queue().launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_api=False,
        show_error=True,
        debug=True,
        prevent_thread_lock=True
    )
