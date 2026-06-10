"""淘宝光合页面选择器"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class TaobaoGuangheSelectors:
    """淘宝光合页面选择器集合"""

    # 版本标识
    version: str = "v1_real"

    # ==================== URL 常量 ====================

    # 淘宝光合首页
    GUANGHE_HOME_URL: str = "https://guanghe.taobao.com/"

    # 创作者中心
    CREATOR_CENTER_URL: str = "https://creator.guanghe.taobao.com/page?layout=%2Fvelocity%2Flayout%2Findex.vm"

    # ==================== 登录页面 ====================

    # 登录按钮/入口（待确认）
    login_button: str = 'text="登录"'

    # 扫码登录标签（如果有多个登录方式）
    scan_login_tab: str = 'text="扫码登录"'

    # 二维码容器（ID 选择器）
    qrcode_container: str = '#qrcode-img'

    # 二维码容器（Class 选择器，备用）
    qrcode_container_class: str = '.qrcode-img'

    # 二维码 Canvas 元素（主要）
    qrcode_canvas: str = '#qrcode-img canvas'

    # 二维码图片（隐藏的，备用）
    qrcode_img: str = '#qrcode-img img'

    # 登录成功后的用户元素（待确认）
    user_avatar: str = '.user-avatar'

    # ==================== 创作者中心（登录后） ====================

    # 新手引导弹窗关闭按钮
    guide_modal_close: str = '.guide-modal-close-icon'

    # 欢迎弹窗关闭按钮
    welcome_close: str = 'button[name="关闭"]'

    # 知道了按钮
    got_it_button: str = 'button:has-text("知道了")'

    # 创作者入口
    creator_entry: str = 'text="创作者"'

    # ==================== 上传页面（待录制） ====================

    # 上传视频入口
    upload_entry: str = 'text="上传视频"'

    # 视频上传输入框（待确认）
    video_upload_input: str = 'input[type="file"][accept*="video"]'

    # 视频上传按钮（待确认）
    video_upload_button: str = 'button:has-text("上传视频")'

    # 视频处理进度（待确认）
    video_progress: str = '.upload-progress'

    # 视频处理完成标识（待确认）
    video_complete: str = '.upload-complete'

    # ==================== 视频信息填写（待录制） ====================

    # 标题输入框（待确认）
    title_input: str = 'input[placeholder*="标题"]'

    # 描述输入框（待确认）
    description_textarea: str = 'textarea[placeholder*="描述"]'

    # 标签输入框（待确认）
    tag_input: str = 'input[placeholder*="标签"]'

    # 添加标签按钮（待确认）
    add_tag_button: str = 'button:has-text("添加")'

    # ==================== 封面上传（待录制） ====================

    # 封面上传输入框（待确认）
    cover_upload_input: str = 'input[type="file"][accept*="image"]'

    # 封面预览（待确认）
    cover_preview: str = '.cover-preview'

    # ==================== 商品关联（待录制） ====================

    # 商品链接输入框（待确认）
    product_link_input: str = 'input[placeholder*="商品链接"]'

    # 商品标题输入框（待确认）
    product_title_input: str = 'input[placeholder*="商品标题"]'

    # 关联商品按钮（待确认）
    link_product_button: str = 'button:has-text("关联商品")'

    # ==================== 发布设置（待录制） ====================

    # 立即发布单选框（待确认）
    publish_immediately: str = 'radio[value="immediate"]'

    # 定时发布单选框（待确认）
    publish_scheduled: str = 'radio[value="scheduled"]'

    # 定时发布日期选择器（待确认）
    schedule_date_input: str = 'input[placeholder*="选择日期"]'

    # 定时发布时间选择器（待确认）
    schedule_time_input: str = 'input[placeholder*="选择时间"]'

    # ==================== 发布按钮（待录制） ====================

    # 发布按钮（待确认）
    publish_button: str = 'button:has-text("发布")'

    # 确认发布按钮（待确认）
    confirm_publish_button: str = 'button:has-text("确认")'

    # 发布成功提示（待确认）
    publish_success: str = 'text="发布成功"'

    # 视频链接（待确认）
    video_link: str = 'a[href*="/video/"]'


# 默认选择器（真实录制版本）
DEFAULT_SELECTORS = TaobaoGuangheSelectors(version="v1_real")


def get_selectors(version: Literal["v1_real"] = "v1_real") -> TaobaoGuangheSelectors:
    """
    获取指定版本的选择器

    Args:
        version: 选择器版本

    Returns:
        TaobaoGuangheSelectors: 选择器集合
    """
    if version == "v1_real":
        return DEFAULT_SELECTORS
    else:
        raise ValueError(f"不支持的选择器版本: {version}")


# 导出常用选择器
QRCODE_CONTAINER = "#qrcode-img"
QRCODE_CANVAS = "#qrcode-img canvas"
GUANGHE_HOME_URL = "https://guanghe.taobao.com/"
CREATOR_CENTER_URL = "https://creator.guanghe.taobao.com/page?layout=%2Fvelocity%2Flayout%2Findex.vm"
