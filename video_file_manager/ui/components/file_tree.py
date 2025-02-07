"""
文件树组件
"""
import gradio as gr
from pathlib import Path
from typing import Dict, Callable, Optional

def create_file_tree(
    directory_data: Dict,
    on_select: Optional[Callable] = None
) -> gr.Dataframe:
    """
    创建文件树组件
    
    Args:
        directory_data: 目录数据
        on_select: 选择回调函数
        
    Returns:
        gr.Dataframe: 文件树组件
    """
    # 将目录数据转换为表格数据
    rows = []
    
    def process_node(node: Dict, level: int = 0, parent: str = ""):
        for name, content in node.items():
            if isinstance(content, dict):
                # 这是一个文件夹
                rows.append({
                    "type": "📁",
                    "name": "  " * level + name,
                    "path": f"{parent}/{name}" if parent else name,
                    "size": "",
                    "modified": ""
                })
                process_node(content, level + 1, f"{parent}/{name}" if parent else name)
            else:
                # 这是一个文件
                path = Path(content)
                stat = path.stat()
                rows.append({
                    "type": "📹",
                    "name": "  " * level + name,
                    "path": str(path),
                    "size": _format_size(stat.st_size),
                    "modified": _format_time(stat.st_mtime)
                })
    
    process_node(directory_data)
    
    # 创建数据表格
    return gr.Dataframe(
        headers=["类型", "名称", "路径", "大小", "修改时间"],
        datatype=["str", "str", "str", "str", "str"],
        row_count=len(rows),
        col_count=5,
        value=[[row["type"], row["name"], row["path"], row["size"], row["modified"]] for row in rows],
        interactive=True,
        elem_id="file_tree"
    )

def _format_size(size: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

def _format_time(timestamp: float) -> str:
    """格式化时间戳"""
    from datetime import datetime
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S") 