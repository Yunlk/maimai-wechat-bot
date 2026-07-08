"""
Gewechat API 客户端
负责与 Gewechat 服务通信：登录、收发消息、发送图片
"""
import httpx
from pathlib import Path
from typing import Optional

from .config import geweconfig
from .log import logger


class GewechatClient:
    """Gewechat REST API 封装"""

    def __init__(self):
        self.base_url = geweconfig.gewchat_base_url.rstrip("/")
        self.token = geweconfig.gewchat_token
        self.app_id = geweconfig.gewchat_app_id
        self._client = httpx.AsyncClient(timeout=30)

    # ---- 登录 ----

    async def get_login_qrcode(self) -> dict:
        """获取登录二维码"""
        resp = await self._client.post(f"{self.base_url}/login/getLoginQrCode", json={
            "appId": self.app_id,
        })
        return resp.json()

    async def check_login(self) -> dict:
        """检查登录状态"""
        resp = await self._client.post(f"{self.base_url}/login/checkLogin", json={
            "appId": self.app_id,
        })
        return resp.json()

    # ---- 消息发送 ----

    async def send_text(self, to_wxid: str, content: str) -> dict:
        """发送文本消息"""
        resp = await self._client.post(f"{self.base_url}/message/postText", json={
            "appId": self.app_id,
            "toWxid": to_wxid,
            "content": content,
        })
        return resp.json()

    async def send_image(self, to_wxid: str, image_path: str) -> dict:
        """发送图片消息（本地文件路径）"""
        resp = await self._client.post(f"{self.base_url}/message/postImage", json={
            "appId": self.app_id,
            "toWxid": to_wxid,
            "imgUrl": image_path,
        })
        return resp.json()

    async def send_image_bytes(self, to_wxid: str, image_bytes: bytes) -> dict:
        """发送图片消息（bytes，需要先上传到CDN或保存为文件）"""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(image_bytes)
            tmp_path = f.name
        try:
            return await self.send_image(to_wxid, tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    # ---- 回调管理 ----

    async def set_callback(self, callback_url: str) -> dict:
        """设置消息回调地址"""
        resp = await self._client.post(f"{self.base_url}/tools/setCallback", json={
            "token": self.token,
            "callbackUrl": callback_url,
        })
        return resp.json()

    # ---- 群管理 ----

    async def get_contact_list(self) -> dict:
        """获取通讯录"""
        resp = await self._client.post(f"{self.base_url}/contacts/getContactList", json={
            "appId": self.app_id,
        })
        return resp.json()

    async def get_group_list(self) -> dict:
        """获取群列表"""
        resp = await self._client.post(f"{self.base_url}/group/getGroupList", json={
            "appId": self.app_id,
        })
        return resp.json()

    async def invite_group_member(self, group_id: str, wxids: list[str]) -> dict:
        """拉人进群"""
        resp = await self._client.post(f"{self.base_url}/group/inviteMember", json={
            "appId": self.app_id,
            "chatroomId": group_id,
            "wxids": ",".join(wxids),
        })
        return resp.json()

    async def close(self):
        await self._client.aclose()
