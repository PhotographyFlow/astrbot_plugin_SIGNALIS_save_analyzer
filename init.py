import os
from pathlib import Path
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

def init_plugin_data_dir(plugin_name: str) -> Path:
    """创建并返回插件数据目录"""
    data_path = Path(get_astrbot_data_path()) / "plugin_data" / plugin_name
    os.makedirs(data_path, exist_ok=True)
    return data_path