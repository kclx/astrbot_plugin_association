from datetime import datetime

from ..engine.supa_client import SupabaseClient

from ..domain.status import AdventurerStatus, QuestStatus
from ..domain.vo import Adventurer, Clienter, Quest, QuestAssign

from astrbot.api import logger


class AssociationClient:
    """ """

    def __init__(self, supa_client: SupabaseClient):
        self.supa_client = supa_client

    # 检查
    def is_adventurer(self, contact_way: str, contact_number: str) -> bool:
        """
        检查用户是否已注册为冒险者。

        Args:
            contact_way (str): 平台名称，例如 "telegram" 或 "aiocqhttp"
            contact_number (str): 用户在该平台的唯一标识

        Returns:
            bool: True 表示已注册，False 表示未注册
        """
        try:
            adv_id = self.supa_client.get_adventurer_id_by_way_number(
                contact_way, contact_number
            )
            return adv_id is not None
        except Exception as e:
            logger.error(f"检查冒险者注册状态失败: {e}")
            return False

    def is_clienter(self, contact_way: str, contact_number: str) -> bool:
        """
        检查用户是否已注册为委托人。

        Args:
            contact_way (str): 平台名称，例如 "telegram" 或 "aiocqhttp"
            contact_number (str): 用户在该平台的唯一标识

        Returns:
            bool: True 表示已注册，False 表示未注册
        """
        try:
            adv_id = self.supa_client.get_clienter_id_by_way_number(
                contact_way, contact_number
            )
            return adv_id is not None
        except Exception as e:
            logger.error(f"检查委托人注册状态失败: {e}")
            return False

    # 注册相关
    def register_adventurer(
        self, name: str, contact_way: str, contact_number: str
    ) -> Adventurer | None:
        """
        注册一个新的冒险者到数据库。

        Args:
            name (str): 冒险者名称
            contact_way (str): 平台名称，例如 "telegram" 或 "aiocqhttp"
            contact_number (str): 用户在平台的唯一标识

        Returns:
            Adventurer | None: 注册成功返回 Adventurer 实例，失败返回 None
        """
        adventurer = Adventurer(
            name=name,
            contact_way=contact_way,
            contact_number=contact_number,
        )
        success = self.supa_client.insert_adventurer(adventurer)
        if success:
            return adventurer
        logger.error(f"注册冒险者失败: {adventurer}")
        return None

    def register_clienter(
        self, name: str, contact_way: str, contact_number: str
    ) -> Clienter | None:
        """
        注册一个新的委托人到数据库。

        Args:
            name (str): 委托人名称
            contact_way (str): 平台名称，例如 "telegram" 或 "aiocqhttp"
            contact_number (str): 用户在平台的唯一标识

        Returns:
            Clienter | None: 注册成功返回 Clienter 实例，失败返回 None
        """
        clienter = Clienter(
            name=name,
            contact_way=contact_way,
            contact_number=contact_number,
        )
        success = self.supa_client.insert_clienter(clienter)
        if success:
            return clienter
        logger.error(f"注册委托人失败: {clienter}")
        return None

    def register_quest(
        self,
        clienter_id: str,
        title: str,
        description: str | None = None,
        reward: float = 0.0,
        deadline: datetime | None = None,
    ) -> Quest | None:
        """
        创建并注册一条新的任务（Quest）。

        Args:
            clienter_id (str): 发布任务的委托人ID
            title (str): 任务标题
            description (str | None): 任务描述
            reward (float | None): 任务奖励
            deadline (datetime | None): 任务截止时间

        Returns:
            Quest | None: 注册成功返回 Quest 实例，失败返回 None
        """
        if not clienter_id or not title:
            logger.error("任务注册失败：缺少 clienter_id 或 title")
            return None

        quest = Quest(
            clienter_id=clienter_id,
            title=title,
            description=description,
            reward=reward,
            deadline=deadline,
            status=QuestStatus.PUBLISHED,
            created_at=datetime.now(),
        )

        try:
            success = self.supa_client.insert_quest(quest)
            if success:
                return quest
            else:
                logger.error("任务注册失败：数据库插入失败")
                return None
        except Exception as e:
            logger.error(f"任务注册失败: {e}")
            return None

    # 冒险者相关
    def get_adventurer_status_by_id(
        self, contact_way: str, contact_number: str
    ) -> AdventurerStatus | None:
        """
        根据平台和用户编号获取冒险者的当前状态。

        Args:
            contact_way (str): 平台名称，例如 "telegram" 或 "aiocqhttp"
            contact_number (str): 用户在该平台的唯一标识

        Returns:
            AdventurerStatus | None: 返回冒险者状态，如果未找到冒险者返回 None
        """
        adventurer = self.supa_client.get_adventurer_by_way_number(
            contact_way, contact_number
        )
        if not adventurer:
            logger.warning(f"未找到冒险者: {contact_way} - {contact_number}")
            return None
        return adventurer.status

    # 任务相关
    def get_quest_status_by_id(self, quest_id: str) -> QuestStatus | None:
        """
        根据任务ID获取任务的当前状态。

        Args:
            quest_id (str): 任务ID

        Returns:
            QuestStatus | None: 返回任务状态，如果未找到任务返回 None
        """
        quest = self.supa_client.get_quest_by_id(quest_id)
        if not quest:
            logger.warning(f"未找到任务: {quest_id}")
            return None
        return quest.status

    def accept_quest_by_id(self, quest_id: str, adventurer_id: str) -> Quest | None:
        """
        冒险者接取任务，将任务状态设置为 ASSIGNED，并绑定冒险者ID，同时更新冒险者状态为 WORKING。
        同时创建 quest_assign 记录。

        Args:
            quest_id (str): 任务ID
            adventurer_id (str): 冒险者ID

        Returns:
            Quest | None: 返回更新后的任务实例，如果任务不存在或不可接取返回 None
        """
        # 获取任务
        quest = self.supa_client.get_quest_by_id(quest_id)
        if not quest:
            logger.warning(f"任务 {quest_id} 不存在")
            return None

        # 检查任务是否可接
        if quest.status != QuestStatus.PUBLISHED:
            logger.warning(f"任务 {quest_id} 状态为 {quest.status.cn}，无法接取")
            return None

        # 更新任务状态
        quest.adventurer_id = adventurer_id
        quest.status = QuestStatus.ASSIGNED
        quest.updated_at = datetime.now()
        updated = self.supa_client.update_quest(quest)
        if not updated:
            logger.error(f"更新任务 {quest_id} 失败")
            return None

        # 更新冒险者状态为 WORKING
        adventurer = self.supa_client.get_adventurer_by_id(adventurer_id)
        if adventurer:
            adventurer.status = AdventurerStatus.WORKING
            adv_updated = self.supa_client.update_adventurer(adventurer)
            if not adv_updated:
                logger.error(f"更新冒险者 {adventurer_id} 状态失败")
        else:
            logger.warning(f"未找到冒险者 {adventurer_id}，无法更新状态")

        # 创建 quest_assign 记录
        quest_assign = QuestAssign(
            quest_id=quest_id,
            adventurer_id=adventurer_id,
            status="ONGOING"
        )
        if not self.supa_client.insert_quest_assign(quest_assign):
            logger.error(f"创建任务分配记录失败: {quest_id} -> {adventurer_id}")

        # 记录系统日志
        self.supa_client.log_event(
            event="接取任务",
            detail=f"冒险者 {adventurer_id} 接取任务 {quest_id}"
        )

        return quest

    def submit_quest(self, adventurer_id: str, quest_id: str) -> Quest | None:
        """
        冒险者提交任务，将任务状态从 ASSIGNED 设置为 COMPLETED。
        同时更新 quest_assign 记录状态为 FINISHED。

        Args:
            adventurer_id (str): 冒险者 ID
            quest_id (str): 任务 ID

        Returns:
            Quest | None: 更新后的任务对象；失败返回 None
        """
        # 获取任务
        quest = self.supa_client.get_quest_by_id(quest_id)
        if not quest:
            logger.warning(f"提交失败：任务 {quest_id} 不存在")
            return None
        # 权限检查：必须是接取该任务的冒险者
        if quest.adventurer_id != adventurer_id:
            logger.warning(f"提交失败：冒险者 {adventurer_id} 无权提交任务 {quest_id}")
            return None
        # 状态检查
        if quest.status != QuestStatus.ASSIGNED:
            logger.warning(
                f"提交失败：任务 {quest_id} 状态为 {quest.status.cn}，无法提交完成"
            )
            return None
        # 更新任务
        quest.status = QuestStatus.COMPLETED
        quest.updated_at = datetime.now()
        if not self.supa_client.update_quest(quest):
            logger.error(f"提交失败：任务 {quest_id} 更新失败")
            return None

        # 更新 quest_assign 记录
        quest_assign = self.supa_client.get_quest_assign_by_adventurer_status(
            adventurer_id, "ONGOING"
        )
        if quest_assign and quest_assign.quest_id == quest_id:
            quest_assign.status = "FINISHED"
            quest_assign.finish_time = datetime.now()
            if not self.supa_client.update_quest_assign(quest_assign):
                logger.error(f"更新任务分配记录失败: {quest_assign.id}")

        # 记录系统日志
        self.supa_client.log_event(
            event="提交任务",
            detail=f"冒险者 {adventurer_id} 提交任务 {quest_id}"
        )

        return quest

    def confirm_quest(self, clienter_id: str, quest_id: str) -> Quest | None:
        """
        委托人确认任务完成，将任务状态从 COMPLETED 设置为 CLOSED。
        同时将冒险者状态设为 IDLE，并更新 quest_assign 为 CHECK_FINISHED。

        Args:
            clienter_id (str): 委托人 ID
            quest_id (str): 任务 ID

        Returns:
            Quest | None: 更新后的任务对象；失败返回 None
        """
        # 获取任务
        quest = self.supa_client.get_quest_by_id(quest_id)
        if not quest:
            logger.warning(f"确认失败：任务 {quest_id} 不存在")
            return None
        # 权限检查：必须是任务的委托人
        if quest.clienter_id != clienter_id:
            logger.warning(f"确认失败：委托人 {clienter_id} 无权确认任务 {quest_id}")
            return None
        # 状态检查
        if quest.status != QuestStatus.COMPLETED:
            logger.warning(
                f"确认失败：任务 {quest_id} 状态为 {quest.status.cn}，无法确认完成"
            )
            return None
        # 设置任务为 CLOSED
        quest.status = QuestStatus.CLOSED
        quest.updated_at = datetime.now()
        if not self.supa_client.update_quest(quest):
            logger.error(f"确认失败：任务 {quest_id} 设置 CLOSED 失败")
            return None
        if not quest.adventurer_id:
            logger.warning(f"确认失败：任务 {quest_id} 的冒险者不存在")
            return None
        # 更新冒险者状态
        adventurer = self.supa_client.get_adventurer_by_id(quest.adventurer_id)
        if adventurer:
            adventurer.status = AdventurerStatus.IDLE
            self.supa_client.update_adventurer(adventurer)
        else:
            logger.warning(f"未找到冒险者 {quest.adventurer_id}，无法更新其状态")

        # 更新 quest_assign 到 CHECK_FINISHED
        quest_assign = self.supa_client.get_quest_assign_by_adventurer_status(
            quest.adventurer_id, "FINISHED"
        )
        if quest_assign and quest_assign.quest_id == quest_id:
            quest_assign.status = "CHECK_FINISHED"
            if not self.supa_client.update_quest_assign(quest_assign):
                logger.error(f"更新任务分配记录失败: {quest_assign.id}")

        # 记录系统日志
        self.supa_client.log_event(
            event="确认任务",
            detail=f"委托人 {clienter_id} 确认任务 {quest_id} 完成"
        )

        return quest

    def get_running_quest_by_adventurer_id(self, adventurer_id: str) -> Quest | None:
        return self.supa_client.get_quest_by_adventurer_id_status(
            adventurer_id, QuestStatus.ASSIGNED
        )
