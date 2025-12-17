"""事件处理器类"""

from astrbot.api.event import AstrMessageEvent
from astrbot.core.platform.astrbot_message import AstrBotMessage
from astrbot.core.message.components import BaseMessageComponent, ComponentType, File

from ..utils.file_utils import FileUtils


class EventHandlers:
    """事件处理器类，处理各种消息事件"""

    def __init__(self, file_utils: FileUtils):
        self.file_utils = file_utils

    async def on_all_message(self, event: AstrMessageEvent):
        """处理所有私聊消息，自动下载文件"""
        msg: AstrBotMessage = event.message_obj
        messages: list[BaseMessageComponent] = msg.message
        for message in messages:
            if message.type == ComponentType.File:
                # 直接将 message 当作 File 类型处理
                file_msg: File = message
                # 下载文件到用户文件夹
                await self.file_utils.download_user_file(
                    event.get_sender_id(), file_msg
                )

        yield event.plain_result("收到了一条消息。")
