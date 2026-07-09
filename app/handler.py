"""
消息处理器 — 指令路由 + 查分逻辑
"""
import asyncio
import base64
import os
import tempfile

from io import BytesIO

from PIL import Image

from .config import maiconfig
from .core.image import PlayerBest50
from .core.merge.models import Best50, Player, ServiceName, Theme
from .core.service import mai
from .database import delete_user, get_user, save_user
from .query import diving_fish_query, lxns_query
from .log import logger
from .models import User
from .resources import cover_dir


class MessageHandler:
    """消息处理器"""

    def __init__(self, gewechat_client):
        self.gewe = gewechat_client
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

    async def handle(self, msg: dict) -> str | None:
        """
        处理一条消息，返回要回复的文本或图片路径
        """
        await self.init_data()

        data = msg.get("data") or msg
        content = data.get("content", "").strip()
        from_wxid = data.get("fromWxid", "")

        if not content:
            return None

        parts = content.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1].strip() if len(parts) > 1 else ""

        # ==================== 帮助 ====================
        if cmd in ("/help", "/帮助", "/maimai"):
            return self._cmd_help()

        # ==================== 绑定 ====================
        if cmd in ("/bind", "/绑定"):
            return await self._cmd_bind(from_wxid, args)

        # ==================== 解绑 ====================
        if cmd in ("/unbind", "/解绑"):
            return await self._cmd_unbind(from_wxid)

        # ==================== 查看绑定 ====================
        if cmd in ("/config", "/配置", "/绑定信息"):
            return await self._cmd_config(from_wxid)

        # ==================== 查分 ====================
        if cmd in ("/b50", "/b40", "/查分"):
            return await self._cmd_b50_bind(from_wxid, args)

        # ==================== 歌曲搜索 ====================
        if cmd in ("/search", "/搜歌", "/find"):
            return self._cmd_search(args)

        # ==================== 随机 ====================
        if cmd in ("/random", "/来一首", "/随"):
            return self._cmd_random()

        # ==================== ping ====================
        if cmd == "/ping":
            return "pong! 🎵 maimaiDX Bot is running."

        return None

    # ---- 命令实现 ----

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

    # ---- 绑定 / 解绑 / 配置 ----

    async def _cmd_bind(self, wxid: str, args: str) -> str:
        """绑定水鱼查分器用户名"""
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

        await save_user(wxid, df_username=username, df_token=token)

        msg = f"✅ 绑定成功!\n用户名: {username}"
        if token:
            msg += f"\n个人 Token 已设置"
        msg += "\n现在可以直接用 /b50 查分，无需每次输入用户名"
        return msg

    async def _cmd_unbind(self, wxid: str) -> str:
        """解除绑定"""
        deleted = await delete_user(wxid)
        if deleted:
            return "✅ 已解除绑定"
        return "⚠️ 你还没有绑定过，无需解绑"

    async def _cmd_config(self, wxid: str) -> str:
        """查看当前绑定信息"""
        user = await get_user(wxid)
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

    # ---- 查分 ----

    async def _cmd_b50_bind(self, wxid: str, args: str) -> str:
        """查 B50，优先使用绑定信息"""
        # 1. 解析参数：看是否指定了用户名
        username = args.strip()

        # 2. 加载绑定信息
        bound = await get_user(wxid)
        personal_token = bound["df_token"] if bound else None

        if not username:
            # 没给用户名 → 必须已绑定
            if not bound or not bound["df_username"]:
                return (
                    "你还未绑定查分器账号，请先:\n"
                    "/bind <用户名>\n\n"
                    "或者直接指定用户名:\n"
                    "/b50 <用户名>"
                )
            username = bound["df_username"]

        # 3. 查询 & 渲染
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

        # 4. 渲染图片
        theme = Theme(bound["theme"]) if bound and bound.get("theme") else Theme.PRISM_PLUS
        user_obj = User(service=service, theme=theme)
        b50_img = PlayerBest50(user_obj, player=player, best50=best50, is_username=True)
        b64 = await b50_img.draw()

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            if b64.startswith("base64://"):
                f.write(base64.b64decode(b64[len("base64://"):]))
            elif "," in b64:
                f.write(base64.b64decode(b64.split(",", 1)[1]))
            else:
                f.write(base64.b64decode(b64))
            return f.name

    # ---- 歌曲搜索 ----

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

    # ---- 随机 ----

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
