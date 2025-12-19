"""LLM 工具处理器类"""

from datetime import datetime

from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger

from ..engine.supa_client import SupabaseClient
from ..engine.association_client import AssociationClient
from ..domain.status import AdventurerStatus
from ..domain.vo import Quest
from ..utils.message_utils import MessageUtils


class LLMHandlers:
    """LLM 工具处理器类，处理所有 LLM 工具调用"""

    def __init__(
        self,
        supa_client: SupabaseClient,
        ass_client: AssociationClient,
        message_utils: MessageUtils,
    ):
        self.supa_client = supa_client
        self.ass_client = ass_client
        self.message_utils = message_utils

    async def publish_request(
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
        _, contact_way, contact_number = self.message_utils.get_user_identity(event)

        if not self.ass_client.is_clienter(contact_way, contact_number):
            return "您还不是委托人，无法发布任务，请先注册。"

        deadline_dt: datetime | None = None
        if deadline:
            try:
                deadline_dt = datetime.fromisoformat(deadline)
            except ValueError:
                return "截止时间格式错误，请使用 ISO 格式，如 2025-12-31T23:59:59"

        clienter = self.supa_client.get_clienter_by_way_number(
            contact_way, contact_number
        )
        if not clienter:
            return "未找到您的委托人信息，请重新注册。"

        quest = self.ass_client.register_quest(
            clienter.id, title, description, reward, deadline_dt
        )
        if not quest:
            return "任务发布失败，请稍后重试。"

        adventurers = self.supa_client.get_adventurers_by_status(AdventurerStatus.IDLE)
        if adventurers:
            quest_text = Quest.format_quests([quest])
            await self.message_utils.send_message_to_users(adventurers, quest_text)
        return f"任务《{quest.title}》发布成功，并已推送给空闲的冒险者。"

    async def fetch_quests_published(self, event: AstrMessageEvent) -> str:
        """获取所有已发布且可供冒险者接取的任务列表。

        Args:
        """
        _, way, number = self.message_utils.get_user_identity(event)
        adventurer = self.supa_client.get_adventurer_by_way_number(way, number)
        if not adventurer or adventurer.status != AdventurerStatus.IDLE:
            return "您现在貌似还有任务没有完成，或者您并未注册为冒险者。"
        quests = self.supa_client.get_available_quests()
        if not quests:
            return "当前没有可接取的任务。"
        return Quest.format_quests(quests)

    async def accept_task(self, event: AstrMessageEvent, quest_id: str) -> str:
        """接取一项冒险者协会已发布的任务。

        Args:
            quest_id(string): 要接取的委托任务的唯一标识符（UUID）
        """
        _, contact_way, contact_number = self.message_utils.get_user_identity(event)
        if not self.ass_client.is_adventurer(contact_way, contact_number):
            return "你还不是冒险者"

        status = self.ass_client.get_adventurer_status_by_id(
            contact_way, contact_number
        )
        if status != AdventurerStatus.IDLE:
            return "你已经接取了其他任务"

        adv_id = self.supa_client.get_adventurer_id_by_way_number(
            contact_way, contact_number
        )
        if not adv_id:
            return "无法获取冒险者ID，请重试"

        quest = self.ass_client.accept_quest_by_id(quest_id, adv_id)
        if not quest:
            return "任务接取失败，可能已被其他人接取或任务不存在"
        return Quest.format_quests([quest])

    async def submit_quest(self, event: AstrMessageEvent) -> str:
        """冒险者提交当前正在执行的任务。

        Args:
        """
        _, way, number = self.message_utils.get_user_identity(event)
        adventurer = self.supa_client.get_adventurer_by_way_number(way, number)
        if not adventurer:
            return "❌ 你还不是冒险者，无法提交任务。"
        if adventurer.status != AdventurerStatus.WORKING:
            return "❌ 你当前没有正在进行的任务。"

        result = self.ass_client.get_running_quest_by_adventurer_id(adventurer.id)
        if not result:
            return "❌ 未找到你正在执行的任务。"

        quest, quest_assign = result

        if not quest.clienter_id:
            return "❌ 未找到委托人。"
        clienter = self.supa_client.get_clienter_by_id(quest.clienter_id)
        if not clienter:
            return "⚠️ 任务已提交，但未找到委托人。"

        updated_quest = self.ass_client.submit_quest(adventurer.id, quest.id)
        if not updated_quest:
            return "❌ 任务提交失败，请检查状态或权限。"

        await self.message_utils.send_message_to_users(
            [clienter],
            f"🔔 任务通知\n\n{Quest.format_quests([quest])} \n已由冒险者提交完成。\n请及时确认。",
        )
        return f"✅ 任务《{quest.title}》已成功提交！\n📨 已通知委托人确认。"

    async def confirm_quest(self, event: AstrMessageEvent, quest_id: str) -> str:
        """委托人确认任务完成。

        Args:
            quest_id(string): 任务唯一标识符（UUID）
        """
        _, way, number = self.message_utils.get_user_identity(event)
        clienter_id = self.supa_client.get_clienter_id_by_way_number(way, number)
        if not clienter_id:
            return "❌ 你不是委托人，无法确认任务。"
        if not quest_id:
            return "❌ 任务 ID 不能为空。"

        result = self.ass_client.confirm_quest(clienter_id, quest_id)
        if not result:
            return "❌ 任务确认失败，请检查任务状态或权限。"

        quest, adventurer_id = result

        adventurer = self.supa_client.get_adventurer_by_id(adventurer_id)
        if not adventurer:
            logger.warning(f"任务 {quest_id} 已确认，但冒险者 {adventurer_id} 不存在？")
            return f"🎉 任务《{quest.title}》已确认完成，但冒险者信息缺失。"

        await self.message_utils.send_message_to_users(
            [adventurer],
            f"🎉 恭喜！\n"
            f"你提交的任务《{quest.title}》\n"
            f"✨ 已被委托人确认完成！\n"
            f"你的状态已恢复为【空闲】，可以继续接取新任务啦！",
        )
        return f"🎉 任务《{quest.title}》已成功确认完成！\n✨ 感谢使用冒险者公会系统。"

    async def adventurer_rest(self, event: AstrMessageEvent) -> str:
        """冒险者暂时不接取任务，享受假期。

        Args:
        """
        _, way, number = self.message_utils.get_user_identity(event)
        adv = self.supa_client.get_adventurer_by_way_number(way, number)
        assert adv
        if adv.status == AdventurerStatus.IDLE:
            adv.status = AdventurerStatus.REST
            if self.supa_client.update_adventurer(adv):
                return "已完成修改，享受假期吧冒险者！"
        elif adv.status == AdventurerStatus.WORKING:
            return "您还有任务在身！"
        elif adv.status == AdventurerStatus.QUIT:
            return "您已经不是冒险者了，每天都是假期！"
        elif adv.status == AdventurerStatus.REST:
            return "您已经在休息了。"

    async def adventurer_idle(self, event: AstrMessageEvent) -> str:
        """将冒险者状态设置为空闲，可接取任务。

        Args:
        """
        _, way, number = self.message_utils.get_user_identity(event)
        adv = self.supa_client.get_adventurer_by_way_number(way, number)
        if not adv:
            return "未找到您的冒险者信息。"

        if adv.status == AdventurerStatus.IDLE:
            return "您已经是空闲状态，可以接取任务。"
        elif adv.status in [AdventurerStatus.WORKING, AdventurerStatus.REST]:
            adv.status = AdventurerStatus.IDLE
            if self.supa_client.update_adventurer(adv):
                return "状态已恢复为空闲，可以接取任务了！"
            else:
                return "状态恢复失败，请稍后重试。"
        elif adv.status == AdventurerStatus.QUIT:
            return "您已退出冒险者公会，无法恢复为空闲。"

    async def adventurer_quit(self, event: AstrMessageEvent) -> str:
        """将冒险者状态设置为退出，不再接取任务。

        Args:
        """
        _, way, number = self.message_utils.get_user_identity(event)
        adv = self.supa_client.get_adventurer_by_way_number(way, number)
        if not adv:
            return "未找到您的冒险者信息。"

        if adv.status == AdventurerStatus.QUIT:
            return "您已经退出了冒险者公会。"
        else:
            adv.status = AdventurerStatus.QUIT
            if self.supa_client.update_adventurer(adv):
                return "您已成功退出冒险者公会，每天都是假期！"
            else:
                return "退出操作失败，请稍后重试。"

    async def test(self, event: AstrMessageEvent) -> str:
        """测试 LLM 工具函数。

        Args:
        """
        logger.info(event.unified_msg_origin)
        return "test测试成功"
