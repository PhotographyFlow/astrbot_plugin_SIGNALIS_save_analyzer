from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api.message_components import Image, Reply
from astrbot.api import logger

import os
from pathlib import Path
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

from .analyser import analyser
from .text_to_img import text_to_img
import shutil


class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 初始化数据目录，并保存路径
        self.plugin_data_path = init_plugin_data_dir(self.name)
        logger.info(f"插件数据目录已就绪: {self.plugin_data_path}")

    @filter.command_group("存档解密")
    def save_decoder(self):
        pass

    @save_decoder.command("txt")
    async def analyse_save_text(self, event: AstrMessageEvent):
        """解析用户上传的存档图片，返回纯文本结果"""
        result = analyse_save(self, event)
        yield event.plain_result(result)

    @save_decoder.command("img")
    async def analyse_save_img(self, event: AstrMessageEvent):
        """解析用户上传的存档图片，返回图片结果（使用t2i转换）"""
        result = analyse_save(self, event)
        # 测试发图功能（不对应实际数据）
        img = await text_to_img(self, result)
        yield event.image_result(img)

    @save_decoder.command("help")
    async def help_messaage(self, event: AstrMessageEvent):
        """发送帮助消息"""
        help = """
SIGNALIS 存档解密指令：
/存档解密 txt：解密存档，发送纯文本结果
/存档解密 img：解密存档，发送图片结果
可以和存档图一起发送指令，或者发送图片后引用并附上指令发送

/存档解密 help：发送本帮助消息
        """
        yield event.plain_result(help)

    async def terminate(self):
        """当插件被卸载/停用时删除data文件夹。"""
        shutil.rmtree(self.plugin_data_path)

# 初始化插件目录
def init_plugin_data_dir(plugin_name: str) -> Path:
    """创建并返回插件数据目录"""
    data_path = Path(get_astrbot_data_path()) / "plugin_data" / plugin_name
    os.makedirs(data_path, exist_ok=True)
    return data_path

# 解密存档
def analyse_save(self, event):
    message_chain = event.get_messages()
    img_url = None
    for obj in message_chain:
        if isinstance(obj, Image):
            img_url = obj.url
            break
        elif isinstance(obj, Reply):
            # 从被引用消息的 chain 中查找图片
            if obj.chain:
                for sub_obj in obj.chain:
                    if isinstance(sub_obj, Image):
                        img_url = sub_obj.url
                        break
            if img_url:
                break
    if img_url != None:
        img_local_path = self.plugin_data_path / "temp_save.png"
        result = analyser(img_url, img_local_path)
    else:
        result = "解析失败，没有收到存档图片。发送 /存档解密 help 获取指令帮助"

    return result
