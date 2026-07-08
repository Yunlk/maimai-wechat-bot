"""
查分查询封装 — 去掉 HoshinoBot 依赖
直接调用 API 客户端 + 数据转换
"""
from .core.clients.divingfish.client import DivingFishAPI
from .core.clients.lxns.client import LxnsAPI
from .core.merge.models import Best50, Player, ServiceName
from .core.merge.player import df_to_best50, df_to_player, lxns_to_best50


async def diving_fish_query(username: str) -> tuple[Player, Best50]:
    """
    水鱼查分器查询

    Args:
        username: 水鱼查分器用户名

    Returns:
        (Player, Best50)
    """
    api = DivingFishAPI(username=username)
    userinfo = await api.query_user_b50()
    player = df_to_player(userinfo)
    best50 = df_to_best50(userinfo)
    return player, best50


async def lxns_query(username_or_friend_code: str) -> tuple[Player, Best50]:
    """
    落雪查分器查询

    Args:
        username_or_friend_code: 好友码

    Returns:
        (Player, Best50)
    """
    api = LxnsAPI()
    if username_or_friend_code.isdigit():
        friend_code = int(username_or_friend_code)
        player = await api.player(friend_code=friend_code)
        data = await api.best50(friend_code=friend_code)
    else:
        player = await api.player()
        data = await api.best50()
    best50 = lxns_to_best50(data)
    return player, best50
