"""消息处理工具类"""

from astrbot.api.event import AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context
from astrbot.api import logger
from astrbot.core.config.astrbot_config import AstrBotConfig

from ..domain.vo import Adventurer, Clienter


class MessageUtils:
    """消息处理工具类"""

    def __init__(self, context: Context, config: AstrBotConfig):
        self.context = context
        self.config = config

    @staticmethod
    def get_user_identity(event: AstrMessageEvent) -> tuple[str, str, str]:
        """从事件中提取用户的基础身份信息。

        Args:
            event(AstrMessageEvent): 消息事件对象

        Returns:
            tuple[str, str, str]: (name, contact_way, contact_number)
        """
        name = event.get_sender_name()
        contact_way = event.get_platform_name()
        contact_number = event.get_sender_id()
        return name, contact_way, contact_number

    async def send_message_to_users(
        self, users: list[Adventurer | Clienter], message: str
    ) -> None:
        """将消息发送给用户列表，支持多平台（telegram, aiocqhttp）。

        Args:
            users(list): 用户对象列表，要求每个用户至少包含 contact_way, contact_number, name
            message(string): 需要发送的消息文本
        """
        for user in users:
            if not getattr(user, "contact_way", None) or not getattr(
                user, "contact_number", None
            ):
                continue

            umo: str | None = None
            if user.contact_way == "telegram":
                umo = f"{self.config.get('telegram_id')}:FriendMessage:{user.contact_number}"
            elif user.contact_way == "aiocqhttp":
                umo = f"{self.config.get('aiocqhttp_id')}:FriendMessage:{user.contact_number}"

            if umo:
                try:
                    await self.context.send_message(
                        umo, MessageEventResult().message(message)
                    )
                    logger.info(f"消息已发送给 {user.name} via {user.contact_way}")
                except Exception as e:
                    logger.error(f"发送消息给 {user.name} 失败: {e}")
