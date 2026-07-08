"""
QQ 数据库兼容层 — 用简化版 User 替代 HoshinoBot 的数据库模型
"""
from ...models import User
from ..clients.exceptions import UserNotBindError


async def update_user(
    qqid,
    *,
    friend_code: int | None = None,
    service=None,
    token=None,
    theme=None,
):
    """Stub: 无数据库时的兼容实现"""
    from ...log import logger
    logger.debug(f"update_user stub called for {qqid}")
    return User(qqid=qqid)

__all__ = ["User", "update_user"]
