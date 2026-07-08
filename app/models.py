"""
兼容层：替换原 HoshinoBot 的数据库模型
"""
from dataclasses import dataclass, field

from .core.merge.models.enum import ServiceName, Theme


@dataclass
class User:
    """简化版 User 模型，替代 HoshinoBot 的数据库 User"""
    qqid: int = 0
    wxid: str = ""
    service: ServiceName = ServiceName.DIVINGFISH
    theme: Theme = Theme.PRISM_PLUS
