"""消息处理工具类"""

import json
from typing import List, Union
from astrbot.api.event import AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context
from astrbot.api import logger
from astrbot.core.config.astrbot_config import AstrBotConfig

from ..domain.vo import Adventurer, Clienter
from .session_manager import SessionManager


class MessageUtils:
    """消息处理工具类

    负责处理跨平台消息发送、对话历史记录等功能。
    """

    def __init__(
        self, context: Context, config: AstrBotConfig, session_manager: SessionManager
    ):
        """初始化消息工具类

        Args:
            context: AstrBot 上下文对象
            config: 配置对象
            session_manager: 会话管理器
        """
        self.context = context
        self.config = config
        self.session_manager = session_manager

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
        self, users: List[Union[Adventurer, Clienter]], message: str
    ) -> None:
        """将消息发送给用户列表，支持多平台（telegram, aiocqhttp）

        主动发送的消息会被记录到用户的默认对话历史中，并自动附加对话切换提示。

        Args:
            users: 用户对象列表，每个用户需包含 contact_way, contact_number, name 属性
            message: 需要发送的消息文本
        """
        for user in users:
            await self._send_message_to_single_user(user, message)

    async def _send_message_to_single_user(
        self, user: Union[Adventurer, Clienter], message: str
    ) -> None:
        """向单个用户发送消息

        Args:
            user: 用户对象
            message: 消息文本
        """
        # 验证用户信息完整性
        if not self._validate_user_contact_info(user):
            return

        # 构建统一消息来源标识符
        umo = self._build_unified_message_origin(user)
        if not umo:
            return

        try:
            # 获取用户的专属对话 ID
            cid = self.session_manager.get_user_conversation(umo)

            # 构建完整消息（包含切换提示）
            full_message = self._build_message_with_switch_notice(message, cid)

            # 发送消息
            await self.context.send_message(
                umo, MessageEventResult().message(full_message)
            )
            logger.info(f"消息已发送给 {user.name} via {user.contact_way}")

            # 记录到对话历史（仅记录原始消息）
            await self._record_message_to_conversation(umo, message)
        except Exception as e:
            logger.error(f"发送消息给 {user.name} 失败: {e}")

    def _validate_user_contact_info(self, user: Union[Adventurer, Clienter]) -> bool:
        """验证用户联系方式信息是否完整

        Args:
            user: 用户对象

        Returns:
            bool: 信息是否完整
        """
        return bool(
            getattr(user, "contact_way", None) and getattr(user, "contact_number", None)
        )

    def _build_unified_message_origin(
        self, user: Union[Adventurer, Clienter]
    ) -> str | None:
        """构建统一消息来源标识符（UMO）

        Args:
            user: 用户对象

        Returns:
            str | None: UMO 字符串，格式为 "platform_id:MessageType:user_id"
        """
        platform_mapping = {
            "telegram": f"{self.config.get('telegram_id')}:FriendMessage:{user.contact_number}",
            "aiocqhttp": f"{self.config.get('aiocqhttp_id')}:FriendMessage:{user.contact_number}",
        }
        return platform_mapping.get(user.contact_way)

    def _build_message_with_switch_notice(
        self, message: str, conversation_id: str | None
    ) -> str:
        """构建带有对话切换提示的消息

        Args:
            message: 原始消息内容
            conversation_id: 对话 ID

        Returns:
            str: 完整消息（如果有对话 ID，则包含切换提示）
        """
        if not conversation_id:
            return message

        return (
            f"{message}\n\n"
            f"💬 如需回复，请先切换到冒险者工会对话：\n"
            f"   1. 使用 /ls 查看对话列表\n"
            f"   2. 找到「冒险者工会({conversation_id[:4]})」对话\n"
            f"   3. 使用 /switch 序号 进行切换"
        )

    async def _record_message_to_conversation(self, umo: str, message: str) -> None:
        """将主动发送的消息记录到用户的默认对话历史中

        Args:
            umo: 统一消息来源标识符
            message: 消息内容
        """
        try:
            # 获取或创建默认对话 ID
            cid = await self._get_or_create_default_conversation(umo)
            if not cid:
                logger.debug(f"用户 {umo} 没有默认对话，跳过消息记录")
                return

            # 获取并更新对话历史
            await self._append_message_to_conversation_history(umo, cid, message)

        except Exception as e:
            logger.error(f"记录消息到对话历史失败: {e}")

    async def _get_or_create_default_conversation(self, umo: str) -> str | None:
        """获取或创建用户的默认对话 ID

        Args:
            umo: 统一消息来源标识符

        Returns:
            str | None: 对话 ID，如果无法获取则返回 None
        """
        # 尝试从 session manager 获取
        cid = self.session_manager.get_user_conversation(umo)
        if cid:
            return cid

        # 尝试获取当前对话
        cid = await self.context.conversation_manager.get_curr_conversation_id(umo)
        if not cid:
            return None

        # 保存为默认对话
        self.session_manager.set_user_conversation(umo, cid)
        return cid

    async def _append_message_to_conversation_history(
        self, umo: str, cid: str, message: str
    ) -> None:
        """将消息追加到对话历史

        Args:
            umo: 统一消息来源标识符
            cid: 对话 ID
            message: 消息内容
        """
        # 获取对话详情
        conversation = await self.context.conversation_manager.get_conversation(
            umo, cid
        )
        if not conversation:
            logger.warning(f"无法获取对话 {cid}，跳过消息记录")
            return

        # 解析现有历史
        history = self._parse_conversation_history(conversation.history, cid)

        # 添加新消息（作为 assistant 角色）
        history.append({"role": "assistant", "content": message})

        # 更新对话历史
        await self.context.conversation_manager.update_conversation(
            umo, cid, history=history
        )
        logger.debug(f"已将消息记录到对话 {cid[:8]}... 的历史中")

    def _parse_conversation_history(self, history_json: str | None, cid: str) -> list:
        """解析对话历史 JSON

        Args:
            history_json: 历史记录 JSON 字符串
            cid: 对话 ID（用于日志）

        Returns:
            list: 解析后的历史记录列表
        """
        if not history_json:
            return []

        try:
            return json.loads(history_json)
        except json.JSONDecodeError:
            logger.warning(f"对话 {cid} 的历史记录格式错误，使用空历史")
            return []
