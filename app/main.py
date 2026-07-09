"""
maimai-wechat-bot 入口
WeChatFerry 集成版 — 在 Windows 上本地运行
"""
import asyncio
import os
import signal
import sys

from wcferry.wxmsg import WxMsg

from .config import log, wcfconfig
from .handler import MessageHandler
from .wcf_bot import WcfBot


async def main():
    log.info("=" * 50)
    log.info("maimai-wechat-bot 启动中 (WeChatFerry 模式)")
    log.info("=" * 50)

    # 先加载曲目数据
    handler = MessageHandler()
    await handler.init_data()

    # 初始化 WeChatFerry
    bot = WcfBot(
        host=wcfconfig.wcf_host or None,
        port=wcfconfig.wcf_port,
        debug=wcfconfig.wcf_debug,
    )

    # 消息回调
    async def on_msg(msg: WxMsg):
        try:
            result = handler.handle(msg)
            if not result:
                return

            # 确定回复目标：群消息→群，单聊→发送者
            receiver = msg.roomid if msg.from_group() else msg.sender
            aters = bot.get_aters(msg)

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
                await bot.send_text(result, receiver, aters)
        except Exception:
            log.exception(f"处理消息异常: {msg.content[:50]}")

    bot.on_message(on_msg)

    await bot.start()
    log.success(f"Bot 已上线，监听消息中... (wxid: {bot.wxid})")

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
                pass  # Windows 不支持 SIGTERM
    except Exception:
        pass

    # 启动消息轮询
    poll_task = asyncio.create_task(bot.run_forever())

    await stop_event.wait()
    bot.stop()
    poll_task.cancel()
    log.info("Bot 已退出")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("强行退出")
        sys.exit(0)
