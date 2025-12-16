from datetime import datetime

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.config.astrbot_config import AstrBotConfig

from .engine.supa_client import SupabaseClient
from .engine.association_client import AssociationClient

from .domain.status import AdventurerStatus, QuestStatus
from .domain.vo import Quest


@register("astrbot_plugin_association", "Orlando", "成为冒险者或成为委托人", "1.0.0")
class AssociationPlugin(Star):

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.context = context
        self.config = config

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        self.supa_client = SupabaseClient(
            self.config.get("supabase_url", None), self.config.get("supabase_key", None)
        )
        self.ass_client = AssociationClient(self.supa_client)
        logger.info("Adventurer plugin initialized.")
        logger.info(f"supa id: {self.supa_client.url}.")

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""

    # ========================== 开发 ==========================
    @filter.command("我要当冒险者")
    async def create_adventurer(self, event: AstrMessageEvent):
        """注册为冒险者"""
        name, contact_way, contact_number = self.get_user_identity(event)
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

    @filter.command("我要成为委托人")
    async def create_clienter(self, event: AstrMessageEvent):
        """注册为委托人"""
        name, contact_way, contact_number = self.get_user_identity(event)
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

    @filter.llm_tool(name="publish_request")
    async def llm_tool(
        self,
        event: AstrMessageEvent,
        title: str,
        description: str,
        reward: float = 0.0,
        deadline: str | None = None,
    ) -> MessageEventResult | None:
        """
        向冒险家工会发布一份委托任务的工具函数。

        该函数会根据用户提供的任务信息创建一个 Quest，并推送给当前空闲的冒险者。

        Args:
            title (str): 委托任务标题。
            description (str): 委托任务详细描述。
            reward (float): 奖励金额，默认为 0.0。
            deadline (str): 任务截止时间，ISO 格式字符串，例如 "2025-12-31T23:59:59"。
        """
        # 获取用户身份
        _, contact_way, contact_number = self.get_user_identity(event)

        # 检查委托人身份
        if not self.ass_client.is_clienter(contact_way, contact_number):
            return event.plain_result("您还不是委托人，无法发布任务，请先注册。")

        # 解析截止时间
        deadline_dt: datetime | None = None
        if deadline:
            try:
                deadline_dt = datetime.fromisoformat(deadline)
            except ValueError:
                return event.plain_result(
                    "截止时间格式错误，请使用 ISO 格式，如 2025-12-31T23:59:59"
                )

        # 获取委托人对象
        clienter = self.supa_client.get_clienter_by_way_number(
            contact_way, contact_number
        )
        if not clienter:
            return event.plain_result("未找到您的委托人信息，请重新注册。")

        # 发布任务
        quest = self.ass_client.register_quest(
            clienter.id, title, description, reward, deadline_dt
        )
        if not quest:
            return event.plain_result("任务发布失败，请稍后重试。")
        # 获取空闲冒险者
        adventurers = self.supa_client.get_adventurers_by_status(AdventurerStatus.IDLE)
        if not adventurers:
            return
        # 任务文本格式化
        quest_text = Quest.format_quests([quest])
        # 推送消息给冒险者（抽象为通用方法）
        await self.send_message_to_users(adventurers, quest_text)
        return event.plain_result(
            f"任务《{quest.title}》发布成功，并已推送给空闲的冒险者。"
        )

    @filter.llm_tool(name="fetch_quests_published")
    async def fetch_quests_published(
        self, event: AstrMessageEvent
    ) -> MessageEventResult:
        """
        获取所有已发布且可供冒险者接取的任务，并返回格式化文本。

        LLM Tool 描述:
            该方法用于让冒险者查看当前可接取的任务列表。
            它会从冒险家协会获取状态为 QuestStatus.PUBLISHED 的任务，并将任务信息格式化为可读文本。
            如果没有可接取的任务，会返回提示信息“当前没有已发布的任务。”

        Args:
        """
        _, way, number = self.get_user_identity(event)
        adventurer = self.supa_client.get_adventurer_by_way_number(way, number)
        if not adventurer or adventurer.status != AdventurerStatus.IDLE:
            return event.plain_result(
                "您现在貌似还有任务没有完成，或者您并未注册为冒险者。"
            )
        quests = self.supa_client.get_quests_by_status(QuestStatus.PUBLISHED)
        if not quests:
            return event.plain_result("当前没有已发布的任务。")
        return event.plain_result(Quest.format_quests(quests))

    @filter.llm_tool("accept_task")
    async def accept_task(
        self, event: AstrMessageEvent, quest_id: str
    ) -> MessageEventResult:
        """接取一项冒险者协会已发布的任务。

        当用户表示想要“接任务”“接受某个委托”时，你应该调用本工具。
        用户可能使用任务标题、描述、奖励金额、或直接给出任务ID来表达意图。
        如果用户未直接提供 quest_id，应从当前可见的任务列表中根据标题或内容匹配对应任务。

        Args:
            quest_id (str): 要接取的委托任务的唯一标识符（UUID）。
        """
        _, contact_way, contact_number = self.get_user_identity(event)
        # 检查是否是注册冒险者
        if not self.ass_client.is_adventurer(contact_way, contact_number):
            return event.plain_result("你还不是冒险者")
        # 检查冒险者是否空闲
        status = self.ass_client.get_adventurer_status_by_id(
            contact_way, contact_number
        )
        if status != AdventurerStatus.IDLE:
            return event.plain_result("你已经接取了其他任务")
        # 获取冒险者ID
        adv_id = self.supa_client.get_adventurer_id_by_way_number(
            contact_way, contact_number
        )
        if not adv_id:
            return event.plain_result("无法获取冒险者ID，请重试")
        # 接取任务
        quest = self.ass_client.accept_quest_by_id(quest_id, adv_id)
        if not quest:
            return event.plain_result("任务接取失败，可能已被其他人接取或任务不存在")
        # 返回格式化任务信息
        return MessageEventResult().message(Quest.format_quests([quest]))

    @filter.llm_tool("submit_quest")
    async def submit_quest(self, event: AstrMessageEvent) -> MessageEventResult:
        """
        让冒险者提交当前正在执行的任务。

        用途：
            当冒险者完成任务后调用，用于将任务状态从“进行中（ASSIGNED）”
            修改为“已提交（COMPLETED）”，并通知委托人前来确认。

        行为说明：
            1. 自动识别调用者身份，并判断其是否为冒险者。
            2. 获取冒险者当前正在执行的任务。
            3. 如果任务存在且状态正确，则提交任务。
            4. 自动向委托人发送跨平台通知，提醒确认任务完成。
            5. 最终返回提交成功或失败的消息。

        使用场景（示例指令）：
            - “我完成任务了”
            - “提交任务”
            - “我想上交任务”

        Args:
        """
        # ===== 1. 身份解析 =====
        _, way, number = self.get_user_identity(event)
        adventurer = self.supa_client.get_adventurer_by_way_number(way, number)
        if not adventurer:
            return MessageEventResult().message("❌ 你还不是冒险者，无法提交任务。")
        if adventurer.status != AdventurerStatus.WORKING:
            return MessageEventResult().message("❌ 你当前没有正在进行的任务。")
        # ===== 2. 获取任务 =====
        quest = self.ass_client.get_running_quest_by_adventurer_id(adventurer.id)
        if not quest:
            return MessageEventResult().message("❌ 未找到你正在执行的任务。")
        # ===== 3. 获取委托人 =====
        if not quest.clienter_id:
            return MessageEventResult().message("❌ 未找到委托人。")
        clienter = self.supa_client.get_clienter_by_id(quest.clienter_id)
        if not clienter:
            return MessageEventResult().message(f"⚠️ 任务已提交，但未找到委托人。")
        # ===== 4. 调用业务逻辑提交任务 =====
        updated_quest = self.ass_client.submit_quest(adventurer.id, quest.id)
        if not updated_quest:
            return MessageEventResult().message("❌ 任务提交失败，请检查状态或权限。")
        # ===== 5. 构造委托人通知地址 =====
        quest.status = QuestStatus.COMPLETED
        await self.send_message_to_users(
            [clienter],
            f"🔔 任务通知\n\n{Quest.format_quests([quest])} \n已由冒险者提交完成。\n请及时确认。",
        )
        # ===== 6. 返回冒险者提示 =====
        return MessageEventResult().message(
            f"✅ 任务《{quest.title}》已成功提交！\n📨 已通知委托人确认。"
        )

    @filter.llm_tool("confirm_quest")
    async def confirm_quest(
        self, event: AstrMessageEvent, quest_id: str
    ) -> MessageEventResult:
        """
        委托人确认任务（强制调用工具版本）。

        功能：
            用户只要表达“确认任务”、“认可任务”、“我确认了”、“任务以确认完成”等意图，
            无论是否明确给出 quest_id，
            LLM 必须调用 confirm_quest 工具，并将 quest_id 传递给后端执行。

        LLM 行为规则（关键点）：
            1. 只要用户表达“确认任务完成/认可/确认”等相关意图 → 必须调用 confirm_quest 工具。
            2. 不进行情绪回复、不输出自然语言、不解释、不重复任务内容。
            3. 不替用户做业务判断，不校验状态，不校验权限。
            4. 如果用户没有明确 quest_id：
                - 优先从用户最近的任务通知文本中自动抽取。
                - 若仍无法确定，则要求用户提供 quest_id。
            5. 工具调用后不做额外文本输出。

        触发示例：
            - “任务以确认完成”
            - “我确认这个任务了”
            - “确认任务 95eb51ab-b7d6-46ea-8b1e-6d499a2c64bf”
            - “这个任务我认可”

        禁止行为：
            - ❌ 不要回复“任务已确认完成”
            - ❌ 不要返回系统消息
            - ❌ 不要进行 JSON 外格式说明
            - ❌ 不要进行任何业务处理，只能调用工具

        Args:
            quest_id (str): 任务唯一标识符（UUID）。
        """
        # ===== 1. 身份解析 =====
        _, way, number = self.get_user_identity(event)
        clienter_id = self.supa_client.get_clienter_id_by_way_number(way, number)
        if not clienter_id:
            return MessageEventResult().message("❌ 你不是委托人，无法确认任务。")
        if not quest_id:
            return MessageEventResult().message("❌ 任务 ID 不能为空。")
        # ===== 2. 执行业务逻辑 =====
        quest = self.ass_client.confirm_quest(clienter_id, quest_id)
        if not quest or not quest.adventurer_id:
            return MessageEventResult().message(
                "❌ 任务确认失败，请检查任务状态或权限。"
            )
        # ===== 3. 获取冒险者信息，用于通知 =====
        adventurer = self.supa_client.get_adventurer_by_id(quest.adventurer_id)
        if not adventurer:
            logger.warning(
                f"任务 {quest_id} 已确认，但冒险者 {quest.adventurer_id} 不存在？"
            )
            return MessageEventResult().message(
                f"🎉 任务《{quest.title}》已确认完成，但冒险者信息缺失。"
            )
        # ===== 4. 拼接通知发送目标 =====
        await self.send_message_to_users(
            [adventurer],
            f"🎉 恭喜！\n"
            f"你提交的任务《{quest.title}》\n"
            f"✨ 已被委托人确认完成！\n"
            f"你的状态已恢复为【空闲】，可以继续接取新任务啦！",
        )
        # ===== 5. 返回给委托人 =====
        return MessageEventResult().message(
            f"🎉 任务《{quest.title}》已成功确认完成！\n✨ 感谢使用冒险者公会系统。"
        )

    @filter.llm_tool("adventurer_rest")
    async def adventurer_rest(self, event: AstrMessageEvent) -> MessageEventResult:
        """冒险者暂时不接取任务，享受假期

        Args:
        """
        _, way, number = self.get_user_identity(event)
        adv = self.supa_client.get_adventurer_by_way_number(way, number)
        assert adv
        if adv.status == AdventurerStatus.IDLE:
            adv.status = AdventurerStatus.REST
            if self.supa_client.update_adventurer(adv):
                return MessageEventResult().message("已完成修改，享受假期吧冒险者！")
        elif adv.status == AdventurerStatus.WORKING:
            return MessageEventResult().message("您还有任务在身！")
        elif adv.status == AdventurerStatus.QUIT:
            return MessageEventResult().message("您已经不是冒险者了，每天都是假期！")
        elif adv.status == AdventurerStatus.REST:
            return MessageEventResult().message("您已经在休息了。")

    @filter.llm_tool("adventurer_idle")
    async def adventurer_idle(self, event: AstrMessageEvent) -> MessageEventResult:
        """将冒险者状态设置为空闲，可接取任务"""
        _, way, number = self.get_user_identity(event)
        adv = self.supa_client.get_adventurer_by_way_number(way, number)
        if not adv:
            return MessageEventResult().message("未找到您的冒险者信息。")

        if adv.status == AdventurerStatus.IDLE:
            return MessageEventResult().message("您已经是空闲状态，可以接取任务。")
        elif adv.status in [AdventurerStatus.WORKING, AdventurerStatus.REST]:
            adv.status = AdventurerStatus.IDLE
            if self.supa_client.update_adventurer(adv):
                return MessageEventResult().message(
                    "状态已恢复为空闲，可以接取任务了！"
                )
            else:
                return MessageEventResult().message("状态恢复失败，请稍后重试。")
        elif adv.status == AdventurerStatus.QUIT:
            return MessageEventResult().message("您已退出冒险者公会，无法恢复为空闲。")

    @filter.llm_tool("adventurer_quit")
    async def adventurer_quit(self, event: AstrMessageEvent) -> MessageEventResult:
        """将冒险者状态设置为退出，不再接取任务"""
        _, way, number = self.get_user_identity(event)
        adv = self.supa_client.get_adventurer_by_way_number(way, number)
        if not adv:
            return MessageEventResult().message("未找到您的冒险者信息。")

        if adv.status == AdventurerStatus.QUIT:
            return MessageEventResult().message("您已经退出了冒险者公会。")
        else:
            adv.status = AdventurerStatus.QUIT
            if self.supa_client.update_adventurer(adv):
                return MessageEventResult().message(
                    "您已成功退出冒险者公会，每天都是假期！"
                )
            else:
                return MessageEventResult().message("退出操作失败，请稍后重试。")

    # ========================== tool ==========================
    def get_user_identity(self, event: AstrMessageEvent) -> tuple[str, str, str]:
        """
        从事件中提取用户的基础身份信息。

        Returns:
            tuple[str, str, str]: (name, contact_way, contact_number)
        """
        name = event.get_sender_name()
        contact_way = event.get_platform_name()
        contact_number = event.get_sender_id()
        return name, contact_way, contact_number

    async def send_message_to_users(self, users: list, message: str) -> None:
        """
        将消息发送给用户列表，支持多平台（telegram, aiocqhttp）。

        Args:
            users (list): 用户对象列表，要求每个用户至少包含 contact_way, contact_number, name。
            message (str): 需要发送的消息文本。
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
