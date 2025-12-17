"""探险家协会插件主文件"""

import os

from astrbot.api.star import Context, Star, register
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api import logger
from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

from .engine.supa_client import SupabaseClient
from .engine.association_client import AssociationClient
from .utils.message_utils import MessageUtils
from .utils.file_utils import FileUtils
from .handlers.command_handlers import CommandHandlers
from .handlers.llm_handlers import LLMHandlers
from .handlers.event_handlers import EventHandlers


@register("astrbot_plugin_association", "Orlando", "成为冒险者或成为委托人", "1.0.0")
class AssociationPlugin(Star):
    """探险家协会插件主类"""

    NAME: str = "astrbot_plugin_association"
    SAVE_DIR: str = os.path.join(get_astrbot_data_path(), "plugin_data", NAME)

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.context = context
        self.config = config

    async def initialize(self):
        """初始化插件，创建所有处理器实例"""
        # 初始化数据库客户端
        self.supa_client = SupabaseClient(
            self.config.get("supabase_url", None),
            self.config.get("supabase_key", None),
        )
        self.ass_client = AssociationClient(self.supa_client)

        # 初始化工具类
        self.message_utils = MessageUtils(self.context, self.config)
        self.file_utils = FileUtils(self.SAVE_DIR)

        # 初始化处理器
        self.command_handlers = CommandHandlers(self.ass_client, self.message_utils)
        self.llm_handlers = LLMHandlers(
            self.supa_client, self.ass_client, self.message_utils
        )
        self.event_handlers = EventHandlers(self.file_utils)

        logger.info("Adventurer plugin initialized.")
        logger.info(f"supa id: {self.supa_client.url}.")

    async def terminate(self):
        """插件销毁方法"""
        pass

    # ==================== 命令处理器 ====================
    @filter.command("我要当冒险者")
    async def create_adventurer(self, event: AstrMessageEvent):
        """注册为冒险者"""
        async for result in self.command_handlers.create_adventurer(event):
            yield result

    @filter.command("我要成为委托人")
    async def create_clienter(self, event: AstrMessageEvent):
        """注册为委托人"""
        async for result in self.command_handlers.create_clienter(event):
            yield result

    # ==================== LLM 工具处理器 ====================
    @filter.llm_tool(name="publish_request")
    async def llm_tool(
        self,
        event: AstrMessageEvent,
        title: str,
        description: str,
        reward: float = 0.0,
        deadline: str | None = None,
    ) -> str:
        """向冒险家工会发布一份委托任务。

        Args:
            title(string): 委托任务标题
            description(string): 委托任务详细描述
            reward(number): 奖励金额，默认为 0.0
            deadline(string): 任务截止时间，ISO 格式字符串，例如 "2025-12-31T23:59:59"
        """
        return await self.llm_handlers.publish_request(
            event, title, description, reward, deadline
        )

    @filter.llm_tool(name="fetch_quests_published")
    async def fetch_quests_published(self, event: AstrMessageEvent) -> str:
        """获取所有已发布且可供冒险者接取的任务列表。

        Args:
        """
        return await self.llm_handlers.fetch_quests_published(event)

    @filter.llm_tool("accept_task")
    async def accept_task(self, event: AstrMessageEvent, quest_id: str) -> str:
        """接取一项冒险者协会已发布的任务。

        Args:
            quest_id(string): 要接取的委托任务的唯一标识符（UUID）
        """
        return await self.llm_handlers.accept_task(event, quest_id)

    @filter.llm_tool("submit_quest")
    async def submit_quest(self, event: AstrMessageEvent) -> str:
        """冒险者提交当前正在执行的任务。

        Args:
        """
        return await self.llm_handlers.submit_quest(event)

    @filter.llm_tool("confirm_quest")
    async def confirm_quest(self, event: AstrMessageEvent, quest_id: str) -> str:
        """委托人确认任务完成。

        Args:
            quest_id(string): 任务唯一标识符（UUID）
        """
        return await self.llm_handlers.confirm_quest(event, quest_id)

    @filter.llm_tool("adventurer_rest")
    async def adventurer_rest(self, event: AstrMessageEvent) -> str:
        """冒险者暂时不接取任务，享受假期。

        Args:
        """
        return await self.llm_handlers.adventurer_rest(event)

    @filter.llm_tool("adventurer_idle")
    async def adventurer_idle(self, event: AstrMessageEvent) -> str:
        """将冒险者状态设置为空闲，可接取任务。

        Args:
        """
        return await self.llm_handlers.adventurer_idle(event)

    @filter.llm_tool("adventurer_quit")
    async def adventurer_quit(self, event: AstrMessageEvent) -> str:
        """将冒险者状态设置为退出，不再接取任务。

        Args:
        """
        return await self.llm_handlers.adventurer_quit(event)

    @filter.llm_tool("test_tool")
    async def test(self, event: AstrMessageEvent) -> str:
        """测试 LLM 工具函数。

        Args:
        """
        return await self.llm_handlers.test(event)

    # ==================== 事件处理器 ====================
    # @filter.event_message_type(filter.EventMessageType.PRIVATE_MESSAGE)
    # async def on_all_message(self, event: AstrMessageEvent):
    #     """处理所有私聊消息，自动下载文件"""
    #     async for result in self.event_handlers.on_all_message(event):
    #         yield result
