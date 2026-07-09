"""
企业微信智能机器人长连接客户端
WebSocket → wss://openws.work.weixin.qq.com
明文 JSON 消息，无需加解密，原生支持群聊。
"""
from __future__ import annotations

import asyncio
import base64
import json
import time
import uuid
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

import aiohttp
import websockets

from .config import log

WS_URL = "wss://openws.work.weixin.qq.com"
HEARTBEAT_INTERVAL = 30  # 心跳间隔 (秒)
RECONNECT_MAX = 10


# ── 消息回调类型 ──
MsgCallback = Callable[
    ["MsgContext", "Responder"], Awaitable[None]
]
EventCallback = Callable[
    ["MsgContext", "WelcomeResponder"], Awaitable[None]
]


class MsgContext:
    """消息上下文"""
    msgid: str = ""
    aibotid: str = ""
    chatid: str = ""
    chattype: str = ""  # "single" / "group"
    userid: str = ""    # 发送者 userid
    msgtype: str = ""   # "text" / "mixed" / "event" ...
    content: str = ""   # 文本内容 (msgtype=text 时)


class Responder:
    """消息回复器 (aibot_respond_msg)"""
    def __init__(self, client: "AibotClient", req_id: str):
        self._client = client
        self._req_id = req_id

    async def text(self, content: str) -> None:
        await self._client._send("aibot_respond_msg", self._req_id, {
            "msgtype": "text",
            "text": {"content": content},
        })

    async def markdown(self, content: str) -> None:
        await self._client._send("aibot_respond_msg", self._req_id, {
            "msgtype": "markdown",
            "markdown": {"content": content},
        })

    async def image(self, file_path: str | Path) -> None:
        """发送图片 - 先上传临时素材再回复"""
        media_id = await self._client.upload_image(Path(file_path))
        await self._client._send("aibot_respond_msg", self._req_id, {
            "msgtype": "image",
            "image": {"media_id": media_id},
        })


class WelcomeResponder:
    """进入会话欢迎语回复器"""
    def __init__(self, client: "AibotClient", req_id: str):
        self._client = client
        self._req_id = req_id

    async def text(self, content: str) -> None:
        await self._client._send("aibot_respond_welcome_msg", self._req_id, {
            "msgtype": "text",
            "text": {"content": content},
        })


class AibotClient:
    """企业微信智能机器人长连接客户端"""

    def __init__(self, bot_id: str, secret: str):
        self.bot_id = bot_id
        self.secret = secret
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._running = False
        self._msg_handler: Optional[MsgCallback] = None
        self._event_handler: Optional[EventCallback] = None
        self._pending: dict[str, asyncio.Future] = {}  # req_id → Future

    # ── 注册回调 ──

    def on_message(self, handler: MsgCallback) -> MsgCallback:
        """注册消息回调 (单聊 + 群聊 @机器人)"""
        self._msg_handler = handler
        return handler

    def on_event(self, handler: EventCallback) -> EventCallback:
        """注册事件回调 (进入会话、模板卡片等)"""
        self._event_handler = handler
        return handler

    # ── 连接管理 ──

    async def connect(self) -> None:
        """建立 WebSocket 并鉴权订阅"""
        self._session = aiohttp.ClientSession()
        self._ws = await websockets.connect(WS_URL, ping_interval=None)

        # 发送订阅请求
        resp = await self._request("aibot_subscribe", {
            "bot_id": self.bot_id,
            "secret": self.secret,
        })
        if resp.get("errcode") != 0:
            raise RuntimeError(f"智能机器人订阅失败: {resp.get('errmsg')} (code={resp.get('errcode')})")
        log.success(f"智能机器人长连接已建立 (Bot ID: {self.bot_id[:16]}...)")

    async def _request(self, cmd: str, body: dict) -> dict:
        """发送请求并等待响应（通过 req_id 匹配，避免 listen 循环竞态）"""
        req_id = str(uuid.uuid4())
        future: asyncio.Future = asyncio.Future()
        self._pending[req_id] = future
        try:
            payload = {"cmd": cmd, "headers": {"req_id": req_id}, "body": body}
            await self._ws.send(json.dumps(payload, ensure_ascii=False))
            return await asyncio.wait_for(future, timeout=10)
        finally:
            self._pending.pop(req_id, None)

    async def _send(self, cmd: str, req_id: str, body: dict) -> None:
        """发送单向消息（不等待响应）"""
        payload = {"cmd": cmd, "headers": {"req_id": req_id}, "body": body}
        await self._ws.send(json.dumps(payload, ensure_ascii=False))

    # ── 主循环 ──

    async def listen(self) -> None:
        """消息事件循环"""
        self._running = True
        last_ping = time.time()

        while self._running:
            try:
                raw = await asyncio.wait_for(self._ws.recv(), timeout=5)
                data = json.loads(raw)
                # 检查是否是某个 pending request 的响应
                req_id = data.get("headers", {}).get("req_id", "")
                if req_id and req_id in self._pending:
                    self._pending[req_id].set_result(data)
                else:
                    await self._dispatch(data)
                last_ping = time.time()
            except asyncio.TimeoutError:
                # 心跳
                elapsed = time.time() - last_ping
                if elapsed >= HEARTBEAT_INTERVAL * 0.8:
                    await self._ws.send(json.dumps({"cmd": "ping"}))
                    last_ping = time.time()
            except websockets.ConnectionClosed as e:
                log.warning(f"WebSocket 连接断开 (code={e.code}): {e.reason}")
                await self._reconnect()
            except Exception as e:
                log.error(f"消息循环异常: {e}")
                await asyncio.sleep(1)

    async def _dispatch(self, data: dict) -> None:
        """分发消息到对应回调"""
        cmd = data.get("cmd")
        headers = data.get("headers", {})
        body = data.get("body", {})
        req_id = headers.get("req_id", "")

        if cmd == "aibot_msg_callback":
            ctx = MsgContext()
            ctx.msgid = body.get("msgid", "")
            ctx.aibotid = body.get("aibotid", "")
            ctx.chatid = body.get("chatid", "")
            ctx.chattype = body.get("chattype", "")
            ctx.userid = body.get("from", {}).get("userid", "")
            ctx.msgtype = body.get("msgtype", "")

            if ctx.msgtype == "text":
                ctx.content = body.get("text", {}).get("content", "")
            elif ctx.msgtype == "mixed":
                # 取第一段文本
                items = body.get("mixed", {}).get("msg_item", [])
                parts = [i.get("text", {}).get("content", "") for i in items if i.get("msgtype") == "text"]
                ctx.content = "".join(parts)

            if self._msg_handler and ctx.msgtype in ("text", "mixed"):
                responder = Responder(self, req_id)
                await self._msg_handler(ctx, responder)

        elif cmd == "aibot_event_callback":
            event = body.get("event", {})
            event_type = event.get("eventtype", "")
            ctx = MsgContext()
            ctx.userid = body.get("from", {}).get("userid", "")
            ctx.chattype = body.get("chattype", "")

            if event_type == "enter_chat" and self._event_handler:
                responder = WelcomeResponder(self, req_id)
                await self._event_handler(ctx, responder)
            elif event_type == "disconnected_event":
                log.warning("收到连接断开事件（可能被新连接踢掉），准备重连...")
                self._running = False

        elif cmd == "pong":
            pass  # 心跳应答

    # ── 重连 ──

    async def _reconnect(self) -> None:
        for i in range(RECONNECT_MAX):
            delay = min(2 ** i, 60)
            log.info(f"重连尝试 {i+1}/{RECONNECT_MAX} ({delay}s 后)...")
            await asyncio.sleep(delay)
            try:
                await self.connect()
                log.success("重连成功")
                return
            except Exception as e:
                log.warning(f"重连失败: {e}")
        raise RuntimeError(f"重连 {RECONNECT_MAX} 次均失败，放弃")

    # ── 主动推送 ──

    async def send_msg(self, chat_id: str, chat_type: str, msgtype: str = "text",
                       content: str = "", media_id: str = "") -> None:
        """主动推送消息到指定会话"""
        req_id = str(uuid.uuid4())
        if msgtype == "text":
            body = {"chatid": chat_id, "chattype": chat_type, "msgtype": "text",
                    "text": {"content": content}}
        elif msgtype == "markdown":
            body = {"chatid": chat_id, "chattype": chat_type, "msgtype": "markdown",
                    "markdown": {"content": content}}
        elif msgtype == "image":
            body = {"chatid": chat_id, "chattype": chat_type, "msgtype": "image",
                    "image": {"media_id": media_id}}
        else:
            body = {"chatid": chat_id, "chattype": chat_type, "msgtype": "text",
                    "text": {"content": content}}
        await self._send("aibot_send_msg", req_id, body)

    # ── 上传图片 ──

    async def upload_image(self, file_path: Path) -> str:
        """
        上传图片为临时素材，返回 media_id。
        流程: 上传初始化 → 上传分片(≤5MB) → 上传结束
        """
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        file_size = file_path.stat().st_size
        file_name = file_path.name

        # step 1: 上传初始化
        init_resp = await self._request("aibot_upload_init", {
            "filename": file_name,
            "filesize": file_size,
        })
        if init_resp.get("errcode") != 0:
            raise RuntimeError(f"上传初始化失败: {init_resp.get('errmsg')}")
        task_id = init_resp["body"]["task_id"]

        # step 2: 上传分片
        with open(file_path, "rb") as f:
            data = f.read()

        url = init_resp["body"]["url"]
        headers = {"Content-Type": "application/octet-stream"}
        chunk_size = 5 * 1024 * 1024  # 5MB
        offset = 0

        for chunk_start in range(0, file_size, chunk_size):
            chunk = data[chunk_start:chunk_start + chunk_size]
            chunk_headers = {
                **headers,
                "Content-Range": f"bytes {chunk_start}-{chunk_start + len(chunk) - 1}/{file_size}",
            }
            async with self._session.put(url, data=chunk, headers=chunk_headers) as resp:
                if resp.status not in (200, 201, 204):
                    raise RuntimeError(f"上传分片失败: HTTP {resp.status}")

        # step 3: 上传结束
        finish_resp = await self._request("aibot_upload_finish", {
            "task_id": task_id,
        })
        if finish_resp.get("errcode") != 0:
            raise RuntimeError(f"上传结束失败: {finish_resp.get('errmsg')}")

        return finish_resp["body"]["media_id"]

    # ── 启动 & 停止 ──

    async def run(self) -> None:
        """启动客户端（阻塞运行）"""
        log.info("正在连接企业微信智能机器人长连接...")
        if not self.bot_id or not self.secret:
            raise ValueError("AIBOT_BOT_ID 和 AIBOT_SECRET 未配置，请在 .env 中设置")
        await self.connect()
        await self.listen()

    async def stop(self) -> None:
        """优雅关闭"""
        self._running = False
        if self._ws:
            await self._ws.close()
        if self._session:
            await self._session.close()
        log.info("智能机器人客户端已关闭")
