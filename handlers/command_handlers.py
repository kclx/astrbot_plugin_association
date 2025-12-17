"""命令处理器类"""

from astrbot.api.event import AstrMessageEvent

from ..engine.association_client import AssociationClient
from ..utils.message_utils import MessageUtils


class CommandHandlers:
    """命令处理器类，处理用户命令"""

    def __init__(self, ass_client: AssociationClient, message_utils: MessageUtils):
        self.ass_client = ass_client
        self.message_utils = message_utils

    async def create_adventurer(self, event: AstrMessageEvent):
        """注册为冒险者"""
        name, contact_way, contact_number = self.message_utils.get_user_identity(event)
        if self.ass_client.is_adventurer(
            contact_way, contact_number
        ) or self.ass_client.is_clienter(contact_way, contact_number):
            yield event.plain_result("您已经注册过了")
            return

        adventurer = self.ass_client.register_adventurer(
            name, contact_way, contact_number
        )
        if adventurer:
            yield event.plain_result(
                f"欢迎 {adventurer.name} 加入冒险家工会！🎉\n准备好迎接新的冒险吧！"
            )
        else:
            yield event.plain_result("注册失败，请稍后重试。")

    async def create_clienter(self, event: AstrMessageEvent):
        """注册为委托人"""
        name, contact_way, contact_number = self.message_utils.get_user_identity(event)
        # 检查是否已经注册为冒险者或委托人
        if self.ass_client.is_adventurer(
            contact_way, contact_number
        ) or self.ass_client.is_clienter(contact_way, contact_number):
            yield event.plain_result("您已经注册过了")
            return
        # 调用 Clienter 注册方法
        clienter = self.ass_client.register_clienter(name, contact_way, contact_number)
        if clienter:
            yield event.plain_result(
                f"欢迎 {name} 成为委托人！🎉\n您可以开始发布任务了。"
            )
        else:
            yield event.plain_result("注册失败，请稍后重试。")
