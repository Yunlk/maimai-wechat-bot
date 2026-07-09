"""
查分查询封装
支持全局 token 和用户个人 token
"""
from .core.clients.divingfish.client import DivingFishAPI
from .core.clients.lxns.client import LxnsAPI
from .core.merge.models import Best50, Player
from .core.merge.player import df_to_best50, df_to_player, lxns_to_best50


async def diving_fish_query(
    username: str, *, token: str | None = None
) -> tuple[Player, Best50]:
    """
    水鱼查分器查询

    Args:
        username: 水鱼查分器用户名
        token:    个人开发者 token（可选，优先级高于全局配置）

    Returns:
        (Player, Best50)
    """
    api = DivingFishAPI(username=username, token=token)
    userinfo = await api.query_user_b50()
    player = df_to_player(userinfo)
    best50 = df_to_best50(userinfo)
    return player, best50


async def lxns_query(
    username_or_friend_code: str,
    *,
    user_id: str | None = None,
) -> tuple[Player, Best50]:
    """
    落雪查分器查询

    Args:
        username_or_friend_code: 好友码
        user_id:                 已绑定的 user id（用于 OAuth 查询自己）

    Returns:
        (Player, Best50)
    """
    api = LxnsAPI(user_id=user_id)
    if username_or_friend_code.isdigit():
        friend_code = int(username_or_friend_code)
        player = await api.player(friend_code=friend_code)
        data = await api.best50()
    else:
        player = await api.player()
        data = await api.best50()
    best50 = lxns_to_best50(data)
    return player, best50
