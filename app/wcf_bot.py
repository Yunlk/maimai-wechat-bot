"""
WeChatFerry 异步封装 — 消息轮询 + 收发
"""
import asyncio
import os
import queue
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Optional

from wcferry import Wcf
from wcferry.wxmsg import WxMsg

from .config import wcfconfig
from .log import logger

MsgCallback = Callable[[WxMsg], None]


class WcfBot:
    """WeChatFerry 异步 bot（在子线程中运行 Wcf）"""

    def __init__(
        self,
        host: str | None = None,
        port: int = 10086,
        debug: bool = False,
    ):
        self._wcf = Wcf(host=host, port=port, debug=debug, block=True)
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._running = False
        self._callback: Optional[MsgCallback] = None
        self.wxid: str = ""

    # ── 生命周期 ──

    def on_message(self, callback: MsgCallback) -> None:
        """注册消息回调"""
        self._callback = callback

    async def start(self) -> None:
        """登录并开始接收消息"""
        self.wxid = self._wcf.get_self_wxid()
        logger.success(f"微信已登录: {self.wxid}")
        self._wcf.enable_receiving_msg()
        self._running = True

    async def run_forever(self) -> None:
        """消息轮询主循环"""
        loop = asyncio.get_running_loop()
        while self._running:
            try:
                msg: WxMsg = await loop.run_in_executor(self._executor, self._wcf.get_msg)
                if msg and self._callback:
                    try:
                        await self._callback(msg)
                    except Exception:
                        logger.exception("消息回调异常")
                await asyncio.sleep(0.3)
            except queue.Empty:
                # 消息队列空超时 —— 正常情况，不报错
                pass
            except Exception:
                logger.exception("消息轮询错误")
                await asyncio.sleep(1)

    def stop(self) -> None:
        """停止并清理资源"""
        self._running = False
        self._wcf.cleanup()
        self._executor.shutdown(wait=False)

    # ── 消息发送 ──

    def _send_text(self, text: str, receiver: str, aters: str = "") -> int:
        """同步发送文本"""
        return self._wcf.send_text(text, receiver, aters)

    def _send_image(self, path: str, receiver: str) -> int:
        """同步发送图片"""
        return self._wcf.send_image(path, receiver)

    async def send_text(self, text: str, receiver: str, aters: str = "") -> int:
        """异步发送文本"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self._wcf.send_text, text, receiver, aters)

    async def send_image(self, path: str, receiver: str) -> int:
        """异步发送图片"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self._wcf.send_image, path, receiver)

    # ── 辅助 ──

    def get_aters(self, msg: WxMsg) -> str:
        """获取群聊消息中需要 @ 的人（非 bot 的发送者）"""
        if msg.from_group() and msg.sender != self.wxid:
            return msg.sender
        return ""

    @property
    def is_running(self) -> bool:
        return self._running
