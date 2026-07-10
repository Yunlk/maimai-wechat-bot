"""
WeChatAuto 桥接客户端
通过 HTTP 轮询从 .NET 桥接程序取消息，并通过 HTTP 发消息/图片
"""
import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class BridgeMsg:
    """与 WxMsg 兼容的消息模型"""
    sender: str
    content: str
    room_id: str = ""       # 非空=群聊（群 ID/群名）
    room_name: str = ""     # 群名
    timestamp: int = 0

    def from_group(self) -> bool:
        return bool(self.room_id)

    def from_self(self) -> bool:
        return False

    def is_text(self) -> bool:
        return True

    @property
    def roomid(self) -> Optional[str]:
        """handler 里用得着：群聊时返回群 ID"""
        return self.room_id if self.room_id else None


class BridgeClient:
    """与 .NET WeChatAuto 桥接程序的 HTTP 客户端"""

    def __init__(self, base_url: str = "http://localhost:60443"):
        self.base_url = base_url.rstrip("/")
        self._session: Optional[aiohttp.ClientSession] = None
        self._callbacks: list = []
        self._running = False

    async def _ensure_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()

    def on_message(self, callback):
        """注册消息回调 callback(BridgeMsg)"""
        self._callbacks.append(callback)

    async def start(self):
        """启动轮询"""
        self._running = True
        await self._ensure_session()
        logger.info(f"桥接客户端已连接 {self.base_url}")

    async def run_forever(self):
        """消息轮询循环"""
        while self._running:
            try:
                await self._ensure_session()
                async with self._session.get(
                    f"{self.base_url}/messages",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for item in data:
                            rid = item.get("roomId", "") or ""
                            msg = BridgeMsg(
                                sender=item.get("sender", ""),
                                content=item.get("content", ""),
                                room_id=rid,
                                room_name=item.get("roomName", ""),
                                timestamp=item.get("timestamp", 0),
                            )
                            for cb in self._callbacks:
                                try:
                                    await cb(msg)
                                except Exception:
                                    logger.exception("消息回调异常")
            except asyncio.TimeoutError:
                pass
            except aiohttp.ClientConnectorError:
                logger.warning("无法连接到桥接程序，等待重试...")
                await asyncio.sleep(5)
                continue
            except Exception:
                logger.exception("轮询异常")
                await asyncio.sleep(1)
                continue

            await asyncio.sleep(1)

    async def send_text(self, text: str, receiver: str, aters: str = "") -> int:
        """发送文本消息，返回 0=成功"""
        try:
            await self._ensure_session()
            async with self._session.post(
                f"{self.base_url}/send",
                json={"to": receiver, "text": text},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    logger.info(f"文本已发送 → {receiver}")
                    return 0
                else:
                    logger.error(f"发送失败 ({resp.status})")
                    return -1
        except Exception:
            logger.exception(f"发送异常 → {receiver}")
            return -1

    async def send_image(self, image_path: str, receiver: str) -> int:
        """发送图片，返回 0=成功"""
        try:
            await self._ensure_session()
            data = aiohttp.FormData()
            data.add_field("to", receiver)
            data.add_field("file", open(image_path, "rb"), filename="b50.png",
                           content_type="image/png")
            async with self._session.post(
                f"{self.base_url}/send_image",
                data=data,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status == 200:
                    logger.info(f"图片已发送 → {receiver}")
                    return 0
                else:
                    logger.error(f"发送图片失败 ({resp.status})")
                    return -1
        except Exception:
            logger.exception(f"发送图片异常 → {receiver}")
            return -1

    def get_aters(self, msg: BridgeMsg) -> str:
        """获取 @ 列表（群聊中回复用）"""
        return ""

    async def close(self):
        """关闭 session"""
        self._running = False
        if self._session and not self._session.closed:
            await self._session.close()

    @property
    def wxid(self) -> str:
        return "(bridge)"
