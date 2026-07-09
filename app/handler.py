"""
消息处理器 — 指令路由 + 查分逻辑
WeChatFerry 版本
"""
import asyncio
import base64
import os
import tempfile
import time

from wcferry.wxmsg import WxMsg

from .config import botconfig, maiconfig
from .core.image import PlayerBest50
from .core.merge.models import ServiceName, Theme
from .core.service import mai
from .database import delete_user, get_user, save_user
from .log import logger
from .models import User
from .query import diving_fish_query, lxns_query


class MessageHandler:
    """消息处理器 — 返回文本或图片路径"""

    def __init__(self):
        self._init_lock = asyncio.Lock()
        self._initialized = False

    async def init_data(self):
        """初始化曲目数据（只执行一次）"""
        async with self._init_lock:
            if self._initialized:
                return
            logger.info("正在初始化 maimaiDX 数据...")
            try:
                await mai.update()
                self._initialized = True
                logger.success("maimaiDX 数据初始化完成")
            except Exception as e:
                logger.error(f"数据初始化失败: {e}")

    def handle(self, msg: WxMsg) -> str | None:
        """
        同步分发入口（handler 内部用 asyncio.run 跑异步命令）
        返回: 文本字符串, 图片文件路径, 或 None
        """
        if not msg.is_text():
            return None
        if msg.from_self():
            return None

        content = msg.content.strip()
        if not content:
            return None

        parts = content.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1].strip() if len(parts) > 1 else ""

        # 用户标识：群聊用 sender（群成员 wxid），单聊也用 sender
        user_id = msg.sender

        # ── 帮助 ──
        if cmd in ("/help", "/帮助", "/maimai"):
            return self._cmd_help()

        # ── 绑定 ──
        if cmd in ("/bind", "/绑定"):
            return asyncio.run(self._cmd_bind(user_id, args))

        # ── 解绑 ──
        if cmd in ("/unbind", "/解绑"):
            return asyncio.run(self._cmd_unbind(user_id))

        # ── 查看绑定 ──
        if cmd in ("/config", "/配置", "/绑定信息"):
            return asyncio.run(self._cmd_config(user_id))

        # ── 查分 ──
        if cmd in ("/b50", "/b40", "/查分"):
            return asyncio.run(self._cmd_b50(user_id, args))

        # ── 歌曲搜索 ──
        if cmd in ("/search", "/搜歌", "/find"):
            return self._cmd_search(args)

        # ── 随机 ──
        if cmd in ("/random", "/来一首", "/随"):
            return self._cmd_random()

        # ── ping ──
        if cmd == "/ping":
            return "pong! 🎵 maimaiDX Bot is running."

        return None

    # ════════════════════════════════════
    #  命令实现
    # ════════════════════════════════════

    def _cmd_help(self) -> str:
        return (
            "🎮 maimaiDX 微信查分器\n\n"
            "📋 指令列表:\n"
            "/bind <用户名> [token]  绑定水鱼查分器\n"
            "/unbind                解除绑定\n"
            "/config                查看绑定信息\n"
            "/b50 [用户名]          查看 Best 50\n"
            "                        (不填用户名则用已绑定的)\n"
            "/搜歌 <关键词>          搜索歌曲\n"
            "/随                    随机来一首\n"
            "/ping                  检查状态\n"
            "/帮助                  显示此帮助\n\n"
            f"数据来源: Diving-Fish & LXNS\n"
            f"Powered by {maiconfig.bot_name}"
        )

    # ── 绑定 / 解绑 / 配置 ──

    async def _cmd_bind(self, user_id: str, args: str) -> str:
        if not args:
            return (
                "使用方法:\n"
                "/bind <用户名>            绑定水鱼查分器\n"
                "/bind <用户名> <token>    绑定并设置个人开发者 Token\n\n"
                "示例:\n"
                "/bind yun5k\n"
                "/bind yun5k my_divingfish_token"
            )
        parts = args.split(maxsplit=1)
        username = parts[0].strip()
        token = parts[1].strip() if len(parts) > 1 else None

        await save_user(user_id, df_username=username, df_token=token)

        msg = f"✅ 绑定成功!\n用户名: {username}"
        if token:
            msg += "\n个人 Token 已设置"
        msg += "\n现在可以直接用 /b50 查分，无需每次输入用户名"
        return msg

    async def _cmd_unbind(self, user_id: str) -> str:
        deleted = await delete_user(user_id)
        if deleted:
            return "✅ 已解除绑定"
        return "⚠️ 你还没有绑定过，无需解绑"

    async def _cmd_config(self, user_id: str) -> str:
        user = await get_user(user_id)
        if not user:
            return (
                "你还没有绑定查分器账号\n\n"
                "请使用 /bind <用户名> 绑定"
            )
        lines = [
            "📋 当前绑定信息",
            f"用户名:   {user['df_username'] or '未设置'}",
            f"Token:    {'****' + user['df_token'][-4:] if user['df_token'] else '未设置（使用服务器全局 Token）'}",
            f"服务:     {user['service']}",
            f"主题:     {user['theme']}",
        ]
        return "\n".join(lines)

    # ── 查分 ──

    async def _cmd_b50(self, user_id: str, args: str) -> str:
        username = args.strip()
        bound = await get_user(user_id)
        personal_token = bound["df_token"] if bound else None

        if not username:
            if not bound or not bound["df_username"]:
                return (
                    "你还未绑定查分器账号，请先:\n"
                    "/bind <用户名>\n\n"
                    "或者直接指定用户名:\n"
                    "/b50 <用户名>"
                )
            username = bound["df_username"]

        logger.info(f"查询 [{username}] (个人token: {'是' if personal_token else '否'})")

        try:
            player, best50 = await diving_fish_query(username, token=personal_token)
            service = ServiceName.DIVINGFISH
        except Exception as e:
            logger.warning(f"水鱼查分失败 [{username}]: {e}，尝试落雪...")
            try:
                player, best50 = await lxns_query(username)
                service = ServiceName.LXNS
            except Exception as e2:
                logger.error(f"落雪查分也失败 [{username}]: {e2}")
                return f"查询失败: {e2}"

        theme = Theme(bound["theme"]) if bound and bound.get("theme") else Theme.PRISM_PLUS
        user_obj = User(service=service, theme=theme)
        b50_img = PlayerBest50(user_obj, player=player, best50=best50, is_username=True)
        b64 = await b50_img.draw()

        # 解码 base64 → 临时文件
        if b64.startswith("base64://"):
            data = base64.b64decode(b64[len("base64://"):])
        elif "," in b64:
            data = base64.b64decode(b64.split(",", 1)[1])
        else:
            data = base64.b64decode(b64)

        tmp = tempfile.NamedTemporaryFile(suffix=f"_{username}.png", delete=False)
        tmp.write(data)
        tmp.close()

        # 保存到指定目录（如果配置了）
        if botconfig.save_b50_dir:
            out = os.path.join(botconfig.save_b50_dir, f"b50_{username}_{int(time.time())}.png")
            with open(out, "wb") as f:
                f.write(data)
            logger.info(f"B50 图片已保存: {out}")

        return tmp.name

    # ── 歌曲搜索 ──

    def _cmd_search(self, keyword: str) -> str:
        if not keyword:
            return "使用方法: /搜歌 <关键词>\n支持歌名/别名搜索"

        results = mai.total_list.search(keyword)
        if not results:
            alias_results = mai.total_alias_list.search(keyword)
            if alias_results:
                songs = []
                for a in alias_results[:5]:
                    song = mai.total_list.by_id(a.song_id)
                    if song:
                        songs.append(f"{a.song_id}. {song.song_name}")
                if songs:
                    return f"搜索「{keyword}」:\n" + "\n".join(songs)
            return f"未找到与「{keyword}」相关的歌曲"

        lines = []
        for song in results[:10]:
            diffs = "/".join(str(d.level) for d in song.difficulties)
            lines.append(f"{song.song_id}. {song.song_name} [{diffs}]")
        return f"搜索「{keyword}」:\n" + "\n".join(lines)

    # ── 随机 ──

    def _cmd_random(self) -> str:
        import random
        song = random.choice(mai.total_list.root)
        diffs = "/".join(str(d.level) for d in song.difficulties)
        return (
            f"🎲 随机来一首:\n"
            f"{song.song_id}. {song.song_name}\n"
            f"难度: {diffs}\n"
            f"分类: {song.genre}\n"
            f"BPM: {song.bpm}"
        )
