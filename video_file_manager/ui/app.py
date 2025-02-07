"""
主应用界面
"""
import gradio as gr
from pathlib import Path
from typing import Dict, Optional

from core.file_manager import FileManager
from core.metadata_manager import MetadataManager
from ui.components.file_tree import create_file_tree
from ui.components.video_info import create_video_info

class VideoManagerApp:
    def __init__(self):
        """初始化应用"""
        self.file_manager = FileManager()
        self.metadata_manager = MetadataManager()
        self.selected_file: Optional[Path] = None
    
    def refresh_directory(self) -> Dict:
        """刷新目录"""
        return self.file_manager.build_directory_tree()
    
    def on_file_select(self, evt: gr.SelectData) -> tuple:
        """
        文件选择回调
        
        Args:
            evt: 选择事件数据
            
        Returns:
            tuple: (文件信息, 元数据信息)
        """
        path = Path(evt.value)
        if path.is_file():
            self.selected_file = path
            file_info = self.file_manager.get_file_info(path)
            metadata = self.metadata_manager.read_metadata(path.parent)
            return file_info, metadata
        return None, None
    
    def create_ui(self) -> gr.Blocks:
        """
        创建用户界面
        
        Returns:
            gr.Blocks: Gradio界面
        """
        with gr.Blocks(title="视频文件管理器") as app:
            gr.Markdown("# 视频文件管理器")
            
            with gr.Row():
                # 左侧面板
                with gr.Column(scale=2):
                    gr.Markdown("## 文件目录")
                    refresh_btn = gr.Button("刷新目录")
                    file_tree = create_file_tree(self.refresh_directory())
                
                # 右侧面板
                with gr.Column(scale=3):
                    info_group = create_video_info()
            
            # 事件处理
            refresh_btn.click(
                fn=self.refresh_directory,
                outputs=[file_tree]
            )
            
            file_tree.select(
                fn=self.on_file_select,
                outputs=[info_group]
            )
        
        return app

def create_app() -> gr.Blocks:
    """
    创建应用实例
    
    Returns:
        gr.Blocks: Gradio应用界面
    """
    app = VideoManagerApp()
    return app.create_ui()

if __name__ == "__main__":
    app = create_app()
    app.launch() 