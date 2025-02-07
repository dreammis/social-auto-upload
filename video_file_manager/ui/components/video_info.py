"""
视频信息组件
"""
import gradio as gr
from pathlib import Path
from typing import Dict, Optional

def create_video_info(
    file_info: Optional[Dict] = None,
    metadata: Optional[Dict] = None
) -> gr.Group:
    """
    创建视频信息组件
    
    Args:
        file_info: 文件信息
        metadata: 元数据信息
        
    Returns:
        gr.Group: 视频信息组件组
    """
    with gr.Group() as info_group:
        # 基本信息
        with gr.Group(visible=True) as basic_info:
            gr.Markdown("### 基本信息")
            if file_info:
                gr.Text(label="文件名", value=file_info.get("name", ""), interactive=False)
                gr.Text(label="大小", value=file_info.get("size", ""), interactive=False)
                gr.Text(label="修改时间", value=file_info.get("modified", ""), interactive=False)
                gr.Text(label="路径", value=file_info.get("path", ""), interactive=False)
            else:
                gr.Markdown("*请选择视频文件*")
        
        # 元数据信息
        with gr.Group(visible=True) as meta_info:
            gr.Markdown("### 元数据信息")
            if metadata:
                with gr.Row():
                    gr.TextArea(
                        label="标题",
                        value=metadata.get("video_info", {}).get("title", ""),
                        interactive=True
                    )
                with gr.Row():
                    gr.TextArea(
                        label="标签",
                        value=", ".join(metadata.get("video_info", {}).get("tags", [])),
                        interactive=True
                    )
                with gr.Row():
                    gr.TextArea(
                        label="描述",
                        value=metadata.get("video_info", {}).get("description", ""),
                        interactive=True
                    )
            else:
                gr.Markdown("*暂无元数据信息*")
        
        # 平台发布状态
        with gr.Group(visible=True) as platform_info:
            gr.Markdown("### 平台发布状态")
            if metadata and metadata.get("platforms"):
                for platform, info in metadata["platforms"].items():
                    with gr.Row():
                        gr.Text(label=platform, value=info.get("status", "未发布"), interactive=False)
            else:
                gr.Markdown("*暂无平台发布信息*")
    
    return info_group 