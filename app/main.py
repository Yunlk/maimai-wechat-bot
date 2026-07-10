"""
maimai-wechat-bot 入口
WeChatAuto 桥接版 — .NET 桥接 + Python Bot
"""
import asyncio
import os
import signal
import sys

from .bridge_client import BridgeClient, BridgeMsg
from .config import log, bridge_config
from .handler import MessageHandler


async def main():
    log.info("=" * 50)
    log.info("maimai-wechat-bot 启动中 (WeChatAuto 桥接模式)")
    log.info("=" * 50)

    # 先加载曲目数据
    handler = MessageHandler()
    await handler.init_data()

    # 连接 .NET 桥接程序
    bot = BridgeClient(base_url=bridge_config.bridge_url)

    # 消息回调
    async def on_msg(msg: BridgeMsg):
        try:
            result = handler.handle(msg)
            if not result:
                return

            # 确定回复目标：群消息→群，单聊→发送者
            receiver = msg.roomid if msg.from_group() else msg.sender

            if result.lower().endswith(".png"):
                # 图片回复
                status = await bot.send_image(result, receiver)
                if status == 0:
                    log.success(f"已发送 B50 图片 → {receiver}")
                else:
                    log.error(f"图片发送失败(status={status})")
                # 清理临时文件
                try:
                    os.unlink(result)
                except OSError:
                    pass
            else:
                # 文本回复
                await bot.send_text(result, receiver)
        except Exception:
            log.exception(f"处理消息异常: {msg.content[:50]}")

    bot.on_message(on_msg)

    await bot.start()
    log.success(f"Bot 已上线，监听消息中... (桥接: {bridge_config.bridge_url})")

    # 等待退出信号
    stop_event = asyncio.Event()

    def _on_signal():
        log.info("收到退出信号")
        stop_event.set()

    try:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _on_signal)
            except NotImplementedError:
                pass
    except Exception:
        pass

    # 启动消息轮询
    poll_task = asyncio.create_task(bot.run_forever())

    await stop_event.wait()
    await bot.close()
    poll_task.cancel()
    log.info("Bot 已退出")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("强行退出")
        sys.exit(0)
