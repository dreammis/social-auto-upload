# -*- coding: utf-8 -*-

def format_str_for_short_title(origin_title: str) -> str:
    """
    格式化标题字符串，用于生成短标题。

    该函数会移除标题中的非字母数字字符和特定的特殊字符，然后根据长度要求进行截断或填充，
    以生成符合规范的短标题。

    参数:
    origin_title: 原始标题字符串。

    返回值:
    格式化后的短标题字符串。
    """
    # 定义允许的特殊字符
    allowed_special_chars = "《》" "+?%°"

    # 移除不允许的特殊字符
    filtered_chars = [
        (
            char
            if char.isalnum() or char in allowed_special_chars
            else " " if char == "," else ""
        )
        for char in origin_title
    ]
    formatted_string = "".join(filtered_chars)

    # 调整字符串长度
    if len(formatted_string) > 16:
        # 截断字符串
        formatted_string = formatted_string[:16]
    elif len(formatted_string) < 6:
        # 使用空格来填充字符串
        formatted_string += " " * (6 - len(formatted_string))

    return formatted_string 