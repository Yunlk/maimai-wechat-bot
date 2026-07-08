"""
消息处理器 — 指令路由 + 查分逻辑
"""
import asyncio
from io import BytesIO

from PIL import Image

from .config import maiconfig
from .core.image import PlayerBest50, image_to_base64
from .core.merge.models import Best50, Player, ServiceName, Theme
from .core.service import mai
from .query import diving_fish_query, lxns_query
from .log import logger
from .models import User
from .resources import cover_dir, pic_dir


def _ensure_cover(song_id: int) -> str:
    """确保曲绘已下载，返回本地路径"""
    cover_path = cover_dir / f"{song_id}.png"
    if not cover_path.exists():
        # 占位图
        placeholder = Image.new("RGBA", (75, 75), (60, 60, 60))
        placeholder.save(cover_path)
    return str(cover_path)


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

        Gewechat 回调格式 (简化):
        {
            "appId": "...",
            "data": {
                "fromWxid": "wxid_xxx",         # 发送者或群ID
                "msgType": 1,                     # 1=文本 3=图片
                "content": "/b50 yun5k",          # 文本内容
                "msgSource": "..."                # 消息来源
            }
        }
        """
        await self.init_data()

        data = msg.get("data") or msg
        content = data.get("content", "").strip()
        from_wxid = data.get("fromWxid", "")

        if not content:
            return None

        # 解析指令
        parts = content.split(maxsplit=1)
        cmd = parts[0].lower()

        # --- 帮助 ---
        if cmd in ("/help", "/帮助", "/maimai"):
            return self._cmd_help()

        # --- 查分 ---
        if cmd in ("/b50", "/b40", "/查分"):
            username = parts[1].strip() if len(parts) > 1 else ""
            if not username:
                return "使用方法: /b50 <用户名>\n\n示例: /b50 yun5k"
            try:
                image_path = await self._cmd_b50(username)
                return image_path  # handler 中判断是路径就发图片
            except Exception as e:
                logger.error(f"查分失败 [{username}]: {e}")
                return f"查询失败: {e}"

        # --- 歌曲搜索 ---
        if cmd in ("/search", "/搜歌", "/find"):
            keyword = parts[1].strip() if len(parts) > 1 else ""
            if not keyword:
                return "使用方法: /搜歌 <关键词>\n\n支持歌名/别名搜索"
            return self._cmd_search(keyword)

        # --- 随机 ---
        if cmd in ("/random", "/random", "/来一首", "/随"):
            return self._cmd_random()

        # --- ping ---
        if cmd == "/ping":
            return "pong! 🎵 maimaiDX Bot is running."

        # 默认忽略非指令消息
        return None

    def _cmd_help(self) -> str:
        return (
            "🎮 maimaiDX 微信查分器\n\n"
            "指令列表:\n"
            "/b50 <用户名>    查看 Best 50（水鱼查分器）\n"
            "/搜歌 <关键词>    搜索歌曲（支持别名）\n"
            "/随             随机来一首\n"
            "/ping           检查机器人状态\n"
            "/帮助           显示此帮助\n\n"
            f"数据来源: Diving-Fish & LXNS\n"
            f"Powered by {maiconfig.bot_name}"
        )

    async def _cmd_b50(self, username: str) -> str:
        """查分并生成 B50 图片，返回图片文件路径"""
        # 先试水鱼查分器
        logger.info(f"查询玩家 [{username}] 的 B50 数据...")

        try:
            player, best50 = await diving_fish_query(username)
            service = ServiceName.DIVINGFISH
        except Exception:
            logger.warning(f"水鱼查分器查询失败，尝试落雪...")
            player, best50 = await lxns_query(username)
            service = ServiceName.LXNS

        user = User(service=service, theme=Theme.PRISM_PLUS)
        b50_img = PlayerBest50(user, player=player, best50=best50, is_username=True)
        b64 = await b50_img.draw()

        # base64 转文件
        # b64 格式可能是 "base64://xxxxx" 或 "data:image/png;base64,xxxxx"
        import base64
        import tempfile

        if b64.startswith("base64://"):
            img_data = base64.b64decode(b64[len("base64://"):])
        elif "," in b64:
            img_data = base64.b64decode(b64.split(",", 1)[1])
        else:
            img_data = base64.b64decode(b64)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(img_data)
            tmp_path = f.name

        return tmp_path

    def _cmd_search(self, keyword: str) -> str:
        """歌曲搜索"""
        results = mai.total_list.search(keyword)
        if not results:
            # 尝试别名搜索
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
            diffs = "/".join(
                str(d.level) for d in song.difficulties
            )
            lines.append(f"{song.song_id}. {song.song_name} [{diffs}]")
        return f"搜索「{keyword}」:\n" + "\n".join(lines)

    def _cmd_random(self) -> str:
        """随机一首歌"""
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
