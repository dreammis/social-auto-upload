"""纯 Python 实现 B站视频上传，直接使用 SESSDATA 走 Web API，不依赖 biliup CLI。

上传流程：
1. (可选) 上传封面图片
2. GET preupload 获取上传凭证
3. 分片上传视频文件到 B站 CDN
4. POST x/vu/web/add/v3 提交视频元数据

参考: https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/creativecenter/upload.md
"""
from __future__ import annotations

import base64
import json
import math
import time
from pathlib import Path

import requests

from utils.log import bilibili_logger

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

CHUNK_SIZE = 10 * 1024 * 1024  # 10MB per chunk


def _msg(emoji: str, text: str) -> str:
    """统一log消息格式"""
    return f"{emoji} {text}"


class BilibiliUploader:
    def __init__(self, cookie_path: str | Path):
        self.cookie_path = Path(cookie_path)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Referer": "https://member.bilibili.com/",
        })
        self._load_cookies()

    def _load_cookies(self):
        with open(self.cookie_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 支持 LoginInfo 格式和扁平格式
        if "cookie_info" in data:
            cookies = data["cookie_info"].get("cookies", {})
        else:
            cookies = data

        self.SESSDATA = cookies.get("SESSDATA", "")
        self.bili_jct = cookies.get("bili_jct", "")
        self.DedeUserID = cookies.get("DedeUserID", "")

        if not self.SESSDATA:
            raise RuntimeError("cookie 文件中没有 SESSDATA，请重新登录B站")

        cookie_str = f"SESSDATA={self.SESSDATA}; bili_jct={self.bili_jct}; DedeUserID={self.DedeUserID}"
        self.session.headers["Cookie"] = cookie_str

    def check_login(self) -> dict:
        """验证 SESSDATA 是否有效，返回用户信息"""
        resp = self.session.get(
            "https://api.bilibili.com/x/web-interface/nav", timeout=10
        )
        data = resp.json()
        if data.get("code") != 0 or not data.get("data", {}).get("isLogin"):
            raise RuntimeError(
                f"B站登录已过期，请重新扫码登录。"
                f"错误码: {data.get('code')}, 信息: {data.get('message')}"
            )
        return data["data"]

    def upload_cover(self, cover_path: str | Path) -> str:
        """上传封面图片，返回封面 URL

        接口: POST /x/vu/web/cover/up
        """
        cover_path = Path(cover_path)
        if not cover_path.exists():
            raise FileNotFoundError(f"封面文件不存在: {cover_path}")

        with open(cover_path, "rb") as f:
            img_data = base64.b64encode(f.read()).decode("utf-8")

        # 根据后缀确定 MIME 类型
        suffix = cover_path.suffix.lower()
        mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp"}
        mime = mime_map.get(suffix, "image/jpeg")

        resp = self.session.post(
            "https://member.bilibili.com/x/vu/web/cover/up",
            data={
                "csrf": self.bili_jct,
                "cover": f"data:{mime};base64,{img_data}",
            },
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") != 0:
            raise RuntimeError(f"封面上传失败: code={result.get('code')}, message={result.get('message')}")
        raw_url = result["data"]["url"]
        # 清理 URL：用正则提取干净的 URL
        import re
        url_match = re.search(r'https?://[^\s`\'"<>]+', raw_url)
        cover_url = url_match.group(0) if url_match else raw_url.strip()
        bilibili_logger.info(_msg("🖼️", f"封面上传成功: {cover_url}"))
        return cover_url

    def _preupload(self, filename: str, filesize: int) -> dict:
        """第1步：获取上传凭证 (GET 请求)"""
        resp = self.session.get(
            "https://member.bilibili.com/preupload",
            params={
                "name": filename,
                "r": "upos",
                "profile": "ugcupos/bup",
                "ssl": 0,
                "version": "2.14.0.0",
                "build": "2140000",
                "upcdn": "bda2",
                "probe_version": 20221109,
                "size": filesize,
            },
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        if "upos_uri" not in result:
            raise RuntimeError(f"preupload 失败: {json.dumps(result, ensure_ascii=False)}")
        return result

    def _upload_chunks(self, video_path: str | Path, pre_info: dict) -> str:
        """第2步：分片上传视频文件"""
        video_path = Path(video_path)
        filesize = video_path.stat().st_size
        chunk_size = pre_info.get("chunk_size", CHUNK_SIZE)
        total_chunks = math.ceil(filesize / chunk_size)

        upos_uri = pre_info["upos_uri"]
        endpoint = pre_info.get("endpoint", "")
        auth = pre_info.get("auth", "")

        upos_path = upos_uri.replace("upos://", "")
        upload_base = f"https:{endpoint}/{upos_path}"

        # 2.1 初始化上传
        init_resp = self.session.post(
            f"{upload_base}?uploads&output=json",
            headers={"X-Upos-Auth": auth},
            timeout=30,
        )
        init_data = init_resp.json()
        upload_id = init_data.get("upload_id", "")
        if not upload_id:
            raise RuntimeError(f"上传初始化失败: {json.dumps(init_data, ensure_ascii=False)}")

        # 2.2 分片上传
        parts = []
        with open(video_path, "rb") as f:
            for chunk_index in range(total_chunks):
                chunk_data = f.read(chunk_size)
                if not chunk_data:
                    break

                chunk_resp = self.session.put(
                    upload_base,
                    params={
                        "partNumber": chunk_index + 1,
                        "uploadId": upload_id,
                        "chunk": chunk_index,
                        "chunks": total_chunks,
                        "size": len(chunk_data),
                        "start": chunk_index * chunk_size,
                        "end": chunk_index * chunk_size + len(chunk_data),
                        "total": filesize,
                    },
                    headers={
                        "X-Upos-Auth": auth,
                        "Content-Type": "application/octet-stream",
                    },
                    data=chunk_data,
                    timeout=120,
                )
                chunk_resp.raise_for_status()
                parts.append({
                    "partNumber": chunk_index + 1,
                    "eTag": chunk_resp.headers.get("ETag", ""),
                })
                bilibili_logger.info(_msg("📤", f"分片 {chunk_index + 1}/{total_chunks} 上传完成"))

        # 2.3 合并分片
        merge_resp = self.session.post(
            f"{upload_base}?output=json",
            headers={
                "X-Upos-Auth": auth,
                "Content-Type": "application/json",
            },
            json={"parts": parts},
            params={"uploadId": upload_id},
            timeout=30,
        )
        merge_data = merge_resp.json()
        if merge_data.get("OK") != 1:
            raise RuntimeError(f"分片合并失败: {json.dumps(merge_data, ensure_ascii=False)}")

        # 返回 filename（用于提交，无后缀名）
        filename = upos_path.split("/")[-1].split(".")[0]
        return filename

    def _submit(
        self,
        title: str,
        filename: str,
        biz_id: int,
        tid: int = 218,
        tag: str = "",
        desc: str = "",
        copyright_type: int = 1,
        source: str = "",
        cover: str = "",
        no_reprint: int = 1,
        dtime: int | None = None,
        ai_declaration: bool = False,
    ) -> dict:
        """第3步：提交视频元数据

        接口: POST /x/vu/web/add/v3
        认证: Cookie(SESSDATA)
        csrf 作为 URL query 参数 + JSON body 字段

        Args:
            title: 视频标题
            filename: 上传后的文件名（无后缀）
            biz_id: preupload 返回的 biz_id
            tid: 分区ID，默认218（动物圈·综合）
            tag: 标签，逗号分隔
            desc: 视频简介（纯文本）
            copyright_type: 1=自制，2=转载
            source: 转载来源（转载时必填）
            cover: 封面URL
            no_reprint: 0=允许转载，1=禁止转载
            dtime: 定时发布时间戳
            ai_declaration: 是否添加"含AI生成内容"创作声明
        """
        # 创作声明通过 creation_statement 字段传递
        # id=1 对应 "含AI生成内容"
        # id=2 对应 "含虚构演绎内容"
        # id=3 对应 "内容含营销信息"
        # id=4 对应 "个人观点，仅供参考"
        # id=-1 对应 "内容无需标注"（默认）
        creation_statement = None
        if ai_declaration:
            creation_statement = {"id": 1, "content": "含AI生成内容"}

        submit_data = {
            "videos": [
                {
                    "filename": filename,
                    "title": title,
                    "desc": "",
                    "cid": biz_id,
                }
            ],
            "cover": cover,
            "cover43": "",
            "title": title,
            "copyright": copyright_type,
            "tid": tid,
            "tag": tag,
            "desc_format_id": 9999,
            "desc": desc,
            "recreate": -1,
            "dynamic": "",
            "interactive": 0,
            "act_reserve_create": 0,
            "no_disturbance": 0,
            "no_reprint": no_reprint,
            "subtitle": {"open": 0, "lan": ""},
            "dolby": 0,
            "lossless_music": 0,
            "up_selection_reply": False,
            "up_close_reply": False,
            "up_close_danmu": False,
            "web_os": 3,
            "csrf": self.bili_jct,
        }

        if source:
            submit_data["source"] = source

        if dtime:
            submit_data["dtime"] = dtime

        if creation_statement:
            submit_data["creation_statement"] = creation_statement

        # 调试：打印提交数据
        bilibili_logger.debug(_msg("📝", f"submit_data: {json.dumps(submit_data, ensure_ascii=False, indent=2)}"))

        ts = int(time.time() * 1000)
        resp = self.session.post(
            "https://member.bilibili.com/x/vu/web/add/v3",
            params={
                "ts": ts,
                "csrf": self.bili_jct,
            },
            headers={
                "Content-Type": "application/json; charset=utf-8",
            },
            json=submit_data,
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") != 0:
            raise RuntimeError(
                f"视频提交失败: code={result.get('code')}, "
                f"message={result.get('message')}"
            )
        return result.get("data", {})

    def upload(
        self,
        video_path: str | Path,
        title: str,
        tid: int = 218,
        tag: str = "",
        desc: str = "",
        copyright_type: int = 1,
        source: str = "",
        cover_path: str | Path | None = None,
        no_reprint: int = 1,
        dtime: int | None = None,
        ai_declaration: bool = False,
    ) -> dict:
        """完整的上传流程：验证登录 → (上传封面) → preupload → 分片上传 → 提交元数据

        Args:
            video_path: 视频文件路径
            title: 视频标题
            tid: 分区ID，默认218（动物圈·综合）
            tag: 标签，逗号分隔
            desc: 视频简介
            copyright_type: 1=自制（默认），2=转载
            source: 转载来源（转载时必填）
            cover_path: 封面图片本地路径（会自动上传获取URL）
            no_reprint: 0=允许转载，1=禁止转载（默认）
            dtime: 定时发布时间戳
            ai_declaration: 是否添加"含AI生成内容"创作声明
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        # 验证登录
        user_info = self.check_login()
        bilibili_logger.info(_msg("✅", f"B站登录验证通过，用户: {user_info.get('uname')}"))

        # 上传封面（如果提供了封面路径）
        cover_url = ""
        if cover_path:
            bilibili_logger.info(_msg("🖼️", "小人准备上传封面"))
            cover_url = self.upload_cover(cover_path)

        # preupload
        bilibili_logger.info(_msg("🏃", f"开始上传视频: {video_path.name} ({video_path.stat().st_size / 1024 / 1024:.1f}MB)"))
        pre_info = self._preupload(video_path.name, video_path.stat().st_size)
        bilibili_logger.info(_msg("✅", f"preupload 成功, biz_id: {pre_info.get('biz_id')}"))

        # 分片上传
        filename = self._upload_chunks(video_path, pre_info)
        bilibili_logger.success(_msg("🥳", f"视频上传完成, filename: {filename}"))

        # 提交元数据
        bilibili_logger.info(_msg("📝", "小人正在提交视频元数据"))
        result = self._submit(
            title=title,
            filename=filename,
            biz_id=pre_info["biz_id"],
            tid=tid,
            tag=tag,
            desc=desc,
            copyright_type=copyright_type,
            source=source,
            cover=cover_url,
            no_reprint=no_reprint,
            dtime=dtime,
            ai_declaration=ai_declaration,
        )
        bvid = result.get("bvid", "")
        aid = result.get("aid", "")
        bilibili_logger.success(_msg("🥳", f"视频提交成功! BV号: {bvid}, AV号: {aid}"))
        return result
