"""
用户数据库 — SQLite 存储
每个微信用户可绑定自己的水鱼查分器用户名和 Token
"""
import aiosqlite
from pathlib import Path
from typing import Optional

from .log import logger

_DB_PATH: Path | None = None


def set_db_path(path: Path) -> None:
    global _DB_PATH
    _DB_PATH = path


async def init_db() -> None:
    """初始化数据库表"""
    db = await aiosqlite.connect(str(_DB_PATH))
    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            wxid       TEXT PRIMARY KEY,
            df_username TEXT,
            df_token   TEXT,
            friend_code INTEGER,
            service    TEXT DEFAULT 'DIVINGFISH',
            theme      TEXT DEFAULT 'prism_plus'
        )
    """)
    await db.commit()
    await db.close()
    logger.info("数据库初始化完成")


async def get_user(wxid: str) -> Optional[dict]:
    """获取用户绑定信息，未绑定时返回 None"""
    db = await aiosqlite.connect(str(_DB_PATH))
    db.row_factory = aiosqlite.Row
    cursor = await db.execute("SELECT * FROM users WHERE wxid = ?", (wxid,))
    row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None


async def save_user(
    wxid: str,
    *,
    df_username: Optional[str] = None,
    df_token: Optional[str] = None,
    friend_code: Optional[int] = None,
    service: Optional[str] = None,
    theme: Optional[str] = None,
) -> None:
    """创建或更新用户绑定（upsert）"""
    db = await aiosqlite.connect(str(_DB_PATH))

    # 先查是否存在
    cursor = await db.execute("SELECT wxid FROM users WHERE wxid = ?", (wxid,))
    exists = await cursor.fetchone()

    if exists:
        updates = []
        params = []
        if df_username is not None:
            updates.append("df_username = ?"); params.append(df_username)
        if df_token is not None:
            updates.append("df_token = ?"); params.append(df_token)
        if friend_code is not None:
            updates.append("friend_code = ?"); params.append(friend_code)
        if service is not None:
            updates.append("service = ?"); params.append(service)
        if theme is not None:
            updates.append("theme = ?"); params.append(theme)
        if updates:
            params.append(wxid)
            await db.execute(f"UPDATE users SET {', '.join(updates)} WHERE wxid = ?", params)
    else:
        await db.execute(
            "INSERT INTO users (wxid, df_username, df_token, friend_code, service, theme) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (wxid, df_username, df_token, friend_code, service or "DIVINGFISH", theme or "PRISM_PLUS"),
        )

    await db.commit()
    await db.close()


async def delete_user(wxid: str) -> bool:
    """删除用户绑定"""
    db = await aiosqlite.connect(str(_DB_PATH))
    cursor = await db.execute("DELETE FROM users WHERE wxid = ?", (wxid,))
    deleted = cursor.rowcount > 0
    await db.commit()
    await db.close()
    return deleted
