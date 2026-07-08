"""
maimai-wechat-bot 配置
去掉 HoshinoBot 依赖，使用 pydantic-settings + .env
"""
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

Root = Path(__file__).parent.parent  # D:/git/maimai-wechat-bot
StaticRoot = Root / "static"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Root / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class BaseConfig(Settings):
    """基础配置"""
    maimaidx_static_path: str = str(StaticRoot)
    maimaidx_alias_proxy: bool = False
    maimaidx_alias_push: bool = True
    save_in_memory: bool = True
    assets_online: bool = True
    bot_name: str = "maimaiDX"


class DivingFishConfig(Settings):
    """水鱼查分器配置"""
    divingfish_prober_proxy: bool = False
    divingfish_token: Optional[str] = None


class LxnsConfig(Settings):
    """落雪查分器配置"""
    lxns_dev_token: Optional[str] = None
    lx_client_id: Optional[str] = None
    lx_client_secret: Optional[str] = None
    redirect_uri: Optional[str] = None


class GewechatConfig(Settings):
    """Gewechat 配置"""
    gewechat_base_url: str = "http://localhost:2531"
    gewechat_token: str = ""
    gewechat_callback_url: str = ""
    gewechat_app_id: str = ""


class BotConfig(Settings):
    """机器人配置"""
    webhook_host: str = "0.0.0.0"
    webhook_port: int = 8080


from .log import logger as log  # noqa: E402

maiconfig = BaseConfig()
dfconfig = DivingFishConfig()
lxnsconfig = LxnsConfig()
geweconfig = GewechatConfig()
botconfig = BotConfig()
