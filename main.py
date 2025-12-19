"""探险家协会插件主文件"""

from pathlib import Path

from astrbot.api.star import Context, Star, register
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api import logger
from astrbot.api import message_components as Comp
from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot.core.star.star_tools import StarTools


from .engine.supa_client import SupabaseClient
from .engine.association_client import AssociationClient
from .utils.message_utils import MessageUtils
from .utils.file_utils import FileUtils
from .utils.session_manager import SessionManager
from .handlers.command_handlers import CommandHandlers
from .handlers.llm_handlers import LLMHandlers
from .handlers.event_handlers import EventHandlers


# todo https://github.com/AstrBotDevs/AstrBot/issues/4108#issuecomment-3669179542
@register("astrbot_plugin_association", "Orlando", "成为冒险者或成为委托人", "1.0.0")
class AssociationPlugin(Star):
    """探险家协会插件主类"""

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.context = context
        self.config = config

    async def initialize(self):
        """初始化插件，创建所有处理器实例"""
        # 初始化存储位置
        self.save_dir: Path = StarTools.get_data_dir()

        # 初始化数据库客户端
        self.supa_client = SupabaseClient(
            self.config.get("supabase_url", None),
            self.config.get("supabase_key", None),
        )
        self.ass_client = AssociationClient(self.supa_client)

        # 初始化工具类
        self.session_manager = SessionManager(self.save_dir)
        self.message_utils = MessageUtils(
            self.context, self.config, self.session_manager
        )
        self.file_utils = FileUtils(self.save_dir)

        # 初始化处理器
        self.command_handlers = CommandHandlers(
            self.ass_client, self.message_utils, self.file_utils
        )
        self.llm_handlers = LLMHandlers(
            self.supa_client, self.ass_client, self.message_utils
        )
        self.event_handlers = EventHandlers(self.file_utils)

        logger.info("Adventurer plugin initialized.")
        logger.info(f"save path: {self.save_dir}")
        logger.info(f"supa id: {self.supa_client.url}.")

    async def terminate(self):
        """插件销毁方法"""
        pass

    # ==================== 对话管理辅助方法 ====================

    async def _ensure_guild_conversation(
        self, event: AstrMessageEvent
    ) -> tuple[bool, str]:
        """确保用户在冒险者工会专属对话中

        如果用户还没有专属对话，会自动创建一个。
        这个对话与用户的日常聊天对话隔离。

        Args:
            event: 消息事件对象

        Returns:
            tuple[bool, str]: (is_first_time, conversation_id)
                - is_first_time: 是否是首次创建专属对话
                - conversation_id: 对话 ID
        """
        try:
            umo = event.unified_msg_origin

            # 检查是否已有插件专属的 conversation
            existing_cid = self.session_manager.get_user_conversation(umo)
            if existing_cid:
                # 验证这个 conversation 是否还存在
                try:
                    conversation = (
                        await self.context.conversation_manager.get_conversation(
                            umo, existing_cid
                        )
                    )
                    if conversation:
                        return False, existing_cid
                except Exception:
                    logger.warning(
                        f"用户 {umo} 的专属对话 {existing_cid} 不存在，将创建新对话"
                    )

            # 创建新的插件专属 conversation
            new_cid = await self.context.conversation_manager.new_conversation(
                umo,
                event.get_platform_id(),
                title="冒险者工会",
            )

            # 保存到 SessionManager
            self.session_manager.set_user_conversation(umo, new_cid)

            # 切换到这个新对话
            await self.context.conversation_manager.switch_conversation(umo, new_cid)

            logger.info(f"为用户 {umo} 创建了冒险者工会专属对话: {new_cid[:8]}...")
            return True, new_cid
        except Exception as e:
            logger.error(f"创建/获取用户专属 conversation 失败: {e}")
            return False, ""

    def _create_first_time_notice(self, cid: str) -> str:
        """创建首次创建专属对话的提示消息

        Args:
            cid: 对话 ID

        Returns:
            str: 提示消息文本
        """
        return (
            f"✨ 已为您创建冒险者工会专属对话（{cid[:8]}...）\n"
            "所有工会相关的对话都会在这个专属空间中进行。\n"
            "如需切换回日常聊天，请使用 /ls 查看对话列表，然后用 /switch 序号 切换。\n"
            "---"
        )

    # ==================== 命令处理器 ====================

    @filter.command("我要当冒险者")
    async def create_adventurer(self, event: AstrMessageEvent):
        """注册为冒险者"""
        is_first_time, cid = await self._ensure_guild_conversation(event)
        if is_first_time:
            # 设置冒险者人格
            adventurer_personality_id = self.config.get(
                "adventurer_personality_id", None
            )
            if adventurer_personality_id:
                await self.context.conversation_manager.update_conversation(
                    event.unified_msg_origin, cid, persona_id=adventurer_personality_id
                )
            yield event.plain_result(self._create_first_time_notice(cid))
        async for result in self.command_handlers.create_adventurer(event):
            yield result

    @filter.command("我要成为委托人")
    async def create_clienter(self, event: AstrMessageEvent):
        """注册为委托人"""
        is_first_time, cid = await self._ensure_guild_conversation(event)
        if is_first_time:
            # 设置委托人人格
            clienter_personality_id = self.config.get("clienter_personality_id", None)
            if clienter_personality_id:
                await self.context.conversation_manager.update_conversation(
                    event.unified_msg_origin, cid, persona_id=clienter_personality_id
                )
            yield event.plain_result(self._create_first_time_notice(cid))
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
        await self._ensure_guild_conversation(event)
        return await self.llm_handlers.publish_request(
            event, title, description, reward, deadline
        )

    @filter.llm_tool(name="fetch_quests_published")
    async def fetch_quests_published(self, event: AstrMessageEvent) -> str:
        """获取所有已发布且可供冒险者接取的任务列表。

        Args:
        """
        await self._ensure_guild_conversation(event)
        return await self.llm_handlers.fetch_quests_published(event)

    @filter.llm_tool("accept_task")
    async def accept_task(self, event: AstrMessageEvent, quest_id: str) -> str:
        """接取一项冒险者协会已发布的任务。

        Args:
            quest_id(string): 要接取的委托任务的唯一标识符（UUID）
        """
        await self._ensure_guild_conversation(event)
        return await self.llm_handlers.accept_task(event, quest_id)

    @filter.llm_tool("submit_quest")
    async def submit_quest(self, event: AstrMessageEvent) -> str:
        """冒险者提交当前正在执行的任务。

        Args:
        """
        await self._ensure_guild_conversation(event)
        return await self.llm_handlers.submit_quest(event)

    @filter.llm_tool("confirm_quest")
    async def confirm_quest(self, event: AstrMessageEvent, quest_id: str) -> str:
        """委托人确认任务完成。

        Args:
            quest_id(string): 任务唯一标识符（UUID）
        """
        await self._ensure_guild_conversation(event)
        return await self.llm_handlers.confirm_quest(event, quest_id)

    @filter.llm_tool("adventurer_rest")
    async def adventurer_rest(self, event: AstrMessageEvent) -> str:
        """冒险者暂时不接取任务，享受假期。

        Args:
        """
        await self._ensure_guild_conversation(event)
        return await self.llm_handlers.adventurer_rest(event)

    @filter.llm_tool("adventurer_idle")
    async def adventurer_idle(self, event: AstrMessageEvent) -> str:
        """将冒险者状态设置为空闲，可接取任务。

        Args:
        """
        await self._ensure_guild_conversation(event)
        return await self.llm_handlers.adventurer_idle(event)

    @filter.llm_tool("adventurer_quit")
    async def adventurer_quit(self, event: AstrMessageEvent) -> str:
        """将冒险者状态设置为退出，不再接取任务。

        Args:
        """
        await self._ensure_guild_conversation(event)
        return await self.llm_handlers.adventurer_quit(event)

    # ==================== Test ====================

    @filter.llm_tool("test_tool")
    async def test(self, event: AstrMessageEvent) -> str:
        """测试 LLM 工具函数。

        Args:
        """
        return await self.llm_handlers.test(event)

    @filter.command("test")
    async def testChat(self, event: AstrMessageEvent):
        chain = [
            Comp.Plain("来看这个图："),
            Comp.Image.fromURL(
                "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRb-CIA1N7aGu8ouN7NGSvmXq46hKPOqTD45w&s"
            ),
            Comp.Image.fromFileSystem(f"{self.save_dir}/2481534548/图片-2.jpg"),
            Comp.File(
                file=f"{self.save_dir}/2481534548/雅音宫羽.txt", name="雅音宫羽.txt"
            ),
            Comp.Plain("这是一个图片。"),
        ]
        yield event.chain_result(chain)

    @filter.llm_tool("upload_attachments")
    async def upload_attachments(self, event: AstrMessageEvent, quest_id: str):
        """上传附件用于委托人发布或者冒险者提交委托

        Args:
            quest_id (str): 绑定任务ID
        """
        async for result in self.command_handlers.upload_attachments(event, quest_id):
            yield result
