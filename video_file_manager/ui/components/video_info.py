"""
视频信息组件
"""
import gradio as gr
from pathlib import Path
from typing import Dict, Optional, List

def create_video_info() -> List[gr.Component]:
    """
    创建视频信息组件
    
    Returns:
        List[gr.Component]: 视频信息组件列表
    """
    components = []
    
    # 基本信息
    with gr.Group():
        gr.Markdown("### 基本信息")
        
        # 视频预览
        with gr.Row():
            video_preview = gr.Video(
                label="视频预览",
                interactive=False,
                height=400,  # 增加视频预览高度
                width=600   # 增加视频预览宽度
            )
            components.append(video_preview)
        
        # 文件信息
        with gr.Row():
            file_name = gr.Textbox(
                label="文件名",
                value="",
                interactive=False,
                show_copy_button=True
            )
            file_path = gr.Textbox(
                label="完整路径",
                value="",
                interactive=False,
                show_copy_button=True
            )
        components.extend([file_name, file_path])
    
    # 元数据信息
    with gr.Group():
        gr.Markdown("### 元数据信息")
        title = gr.Textbox(
            label="标题",
            value="",
            interactive=True,
            placeholder="请输入视频标题..."
        )
        tags = gr.Textbox(
            label="标签",
            value="",
            interactive=True,
            placeholder="请输入标签，用逗号分隔..."
        )
        description = gr.Textbox(
            label="描述",
            value="",
            interactive=True,
            placeholder="请输入视频描述...",
            lines=3
        )
        components.extend([title, tags, description])
    
    # 平台发布状态
    with gr.Group():
        gr.Markdown("### 平台发布状态")
        platforms = gr.JSON(
            label="平台状态",
            value={},
            show_label=True
        )
        components.append(platforms)
    
    return components 