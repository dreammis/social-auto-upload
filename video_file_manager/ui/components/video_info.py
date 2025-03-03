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
        
        # 视频预览和文本显示
        with gr.Row():
            with gr.Column(scale=1):
                video_preview = gr.Video(
                    label="视频预览",
                    interactive=False,
                    height=400,
                    width=600
                )
                components.append(video_preview)
            
            with gr.Column(scale=1):
                transcript_text = gr.Textbox(
                    label="视频文字",
                    value="",
                    interactive=True,
                    show_copy_button=True,
                    lines=25,  # 增加行数以匹配视频预览高度
                    container=True,  # 使用容器样式
                    scale=1  # 填充整个列宽
                )
                extract_btn = gr.Button(
                    "提取文字",
                    variant="primary",
                    scale=1  # 填充整个列宽
                )
                components.extend([transcript_text, extract_btn])  # 添加到组件列表
        
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