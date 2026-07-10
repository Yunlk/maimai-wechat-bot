"""
maimai-wechat-bot 配置 — WeChatFerry 版本
使用 pydantic-settings + .env
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


class WcfConfig(Settings):
    """WeChatFerry 配置（已弃用，保留兼容）"""
    wcf_host: str = ""      # 远程 wcf 地址（留空=本地启动）
    wcf_port: int = 10086   # wcf RPC 端口
    wcf_debug: bool = False


class BridgeConfig(Settings):
    """WeChatAuto .NET 桥接配置"""
    bridge_url: str = "http://localhost:60443"


class BotConfig(Settings):
    """服务配置"""
    save_b50_dir: str = ""  # B50 图片本地保存目录（留空不保存）


from .log import logger as log  # noqa: E402

maiconfig = BaseConfig()
dfconfig = DivingFishConfig()
lxnsconfig = LxnsConfig()
wcfconfig = WcfConfig()
bridge_config = BridgeConfig()
botconfig = BotConfig()
