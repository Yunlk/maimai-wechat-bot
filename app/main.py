"""
maimaiDX 微信查分机器人 — FastAPI 主服务
接收 Gewechat 消息回调，调用 handler 处理，返回结果
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .config import botconfig, geweconfig
from .database import init_db, set_db_path
from .gewechat_client import GewechatClient
from .handler import MessageHandler
from .log import logger
from .resources import data_dir


gewe: GewechatClient = None
handler: MessageHandler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global gewe, handler
    logger.info("maimaiDX WeChat Bot 启动中...")

    # 初始化数据库
    set_db_path(data_dir / "users.db")
    await init_db()

    gewe = GewechatClient()
    handler = MessageHandler(gewe)

    # 预初始化数据
    await handler.init_data()

    # 设置 Gewechat 回调
    callback_url = geweconfig.gewchat_callback_url
    if callback_url:
        try:
            await gewe.set_callback(callback_url)
            logger.success(f"Gewechat 回调已设置: {callback_url}")
        except Exception as e:
            logger.warning(f"设置回调失败: {e}")
    else:
        logger.info("未配置回调地址，跳过自动设置。请手动在 Gewechat 控制台设置回调。")

    yield

    logger.info("maimaiDX WeChat Bot 关闭")
    if gewe:
        await gewe.close()


app = FastAPI(title="maimaiDX WeChat Bot", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(request: Request):
    """接收 Gewechat 消息回调"""
    try:
        msg = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid json"}, status_code=400)

    # Gewechat 的 msgType: 1=文本, 3=图片, 34=语音, 49=引用/小程序等
    data = msg.get("data") or msg
    msg_type = data.get("msgType", 0)

    # 只处理文本消息
    if msg_type != 1:
        return JSONResponse({"status": "ignored"})

    try:
        result = await handler.handle(msg)
    except Exception as e:
        logger.error(f"处理消息异常: {e}")
        return JSONResponse({"status": "error", "message": str(e)})

    if result is None:
        return JSONResponse({"status": "no_reply"})

    from_wxid = data.get("fromWxid", "")

    # 判断是图片路径还是文本
    if result.endswith(".png") and os.path.isfile(result):
        await gewe.send_image(from_wxid, result)
        # 清理临时文件
        try:
            os.remove(result)
        except Exception:
            pass
    else:
        await gewe.send_text(from_wxid, result)

    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=botconfig.webhook_host,
        port=botconfig.webhook_port,
        reload=False,
    )
