from datetime import datetime
import os
from pathlib import Path
from typing import List
import uuid

from ..engine.supa_client import SupabaseClient

from ..domain.status import AdventurerStatus, QuestAssignStatus, QuestMaterialType
from ..domain.vo import Adventurer, Clienter, Quest, QuestAssign, QuestMaterial

from astrbot.api import logger


class AssociationClient:
    """ """

    def __init__(self, supa_client: SupabaseClient):
        self.supa_client = supa_client

    # 检查
    async def is_adventurer(self, contact_way: str, contact_number: str) -> bool:
        """
        检查用户是否已注册为冒险者。

        Args:
            contact_way (str): 平台名称，例如 "telegram" 或 "aiocqhttp"
            contact_number (str): 用户在该平台的唯一标识

        Returns:
            bool: True 表示已注册，False 表示未注册
        """
        try:
            adv_id = await self.supa_client.get_adventurer_id_by_way_number(
                contact_way, contact_number
            )
            return adv_id is not None
        except Exception as e:
            logger.error(f"检查冒险者注册状态失败: {e}")
            return False

    async def is_clienter(self, contact_way: str, contact_number: str) -> bool:
        """
        检查用户是否已注册为委托人。

        Args:
            contact_way (str): 平台名称，例如 "telegram" 或 "aiocqhttp"
            contact_number (str): 用户在该平台的唯一标识

        Returns:
            bool: True 表示已注册，False 表示未注册
        """
        try:
            adv_id = await self.supa_client.get_clienter_id_by_way_number(
                contact_way, contact_number
            )
            return adv_id is not None
        except Exception as e:
            logger.error(f"检查委托人注册状态失败: {e}")
            return False

    # 注册相关
    async def register_adventurer(
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
        success = await self.supa_client.insert_adventurer(adventurer)
        if success:
            return adventurer
        logger.error(f"注册冒险者失败: {adventurer}")
        return None

    async def register_clienter(
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
        success = await self.supa_client.insert_clienter(clienter)
        if success:
            return clienter
        logger.error(f"注册委托人失败: {clienter}")
        return None

    async def register_quest(
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
            created_at=datetime.now(),
        )

        try:
            success = await self.supa_client.insert_quest(quest)
            if success:
                quest_assign = QuestAssign(
                    quest_id=quest.id,
                )
                success = await self.supa_client.insert_quest_assign(quest_assign)
                if success:
                    return quest
            else:
                logger.error("任务注册失败：数据库插入失败")
                return None
        except Exception as e:
            logger.error(f"任务注册失败: {e}")
            return None

    async def save_quest_attachment(
        self, quest_id: str, file_path: str, type: QuestMaterialType
    ) -> QuestMaterial | None:
        """保存单个任务附件

        Args:
            quest_id: 任务ID
            path: 文件路径（字符串或Path对象）
            type: 附件类型（ILLUSTRATE或PROOF）

        Returns:
            QuestMaterial | None: 成功返回材料对象，失败返回None
        """
        # 确保path是Path对象以便获取suffix
        path_obj = Path(file_path) if isinstance(file_path, str) else file_path

        qm = QuestMaterial(
            quest_id=quest_id,
            material_name=os.path.basename(path_obj),
            file_path=str(path_obj),  # 转换为字符串存储
            type=type.value,  # 使用枚举的值
        )
        try:
            success = await self.supa_client.insert_quest_material(qm)
            if success:
                return qm
            else:
                logger.error("任务材料注册失败：数据库插入失败")
                return None
        except Exception as e:
            logger.error(f"任务材料注册失败: {e}")
            return None

    async def save_quest_attachments(
        self, quest_id: str, paths: List[tuple[str | Path, QuestMaterialType]]
    ) -> List[QuestMaterial]:
        """批量保存任务附件

        Args:
            quest_id: 任务ID
            paths: 文件路径和类型的元组列表

        Returns:
            List[QuestMaterial]: 成功保存的材料对象列表
        """
        results = []
        for path, material_type in paths:
            qm = self.save_quest_attachment(quest_id, path, material_type)
            if qm:
                results.append(qm)
        return results

    async def get_quest_attachments(
        self, quest_id: str, type: QuestMaterialType
    ) -> List[QuestMaterial] | None:
        materials = await self.supa_client.get_quest_materials_by_quest_id_type(
            quest_id, type
        )
        if not materials:
            logger.warning(f"未找到附件: {quest_id} - {type.cn}")
            return None
        return materials

    # 冒险者相关
    async def get_adventurer_status_by_id(
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
        adventurer = await self.supa_client.get_adventurer_by_way_number(
            contact_way, contact_number
        )
        if not adventurer:
            logger.warning(f"未找到冒险者: {contact_way} - {contact_number}")
            return None
        return adventurer.status

    # 任务相关
    async def get_quest_assign_status_by_quest_adventurer(
        self, quest_id: str, adventurer_id: str
    ) -> QuestAssignStatus | None:
        """
        根据任务ID和冒险者ID获取任务分配的当前状态。

        Args:
            quest_id (str): 任务ID
            adventurer_id (str): 冒险者ID

        Returns:
            QuestAssignStatus | None: 返回任务分配状态，如果未找到返回 None
        """
        quest_assigns = await self.supa_client.get_quest_assigns_by_quest_id(quest_id)
        if not quest_assigns:
            logger.warning(f"未找到任务 {quest_id} 的分配记录")
            return None

        for qa in quest_assigns:
            if qa.adventurer_id == adventurer_id:
                return QuestAssignStatus(qa.status)

        logger.warning(f"未找到冒险者 {adventurer_id} 对任务 {quest_id} 的分配记录")
        return None

    async def accept_quest_by_id(self, quest_id: str, adventurer_id: str) -> Quest | None:
        """
        冒险者接取任务，创建任务分配记录并更新冒险者状态为 WORKING。

        Args:
            quest_id (str): 任务ID
            adventurer_id (str): 冒险者ID

        Returns:
            Quest | None: 返回任务实例，如果任务不存在或已被接取返回 None
        """
        # 获取任务
        quest = await self.supa_client.get_quest_by_id(quest_id)
        if not quest:
            logger.warning(f"任务 {quest_id} 不存在")
            return None

        # 检查任务是否已被接取（通过 quest_assign 表查询 ONGOING 状态的记录）
        existing_assigns = await self.supa_client.get_quest_assigns_by_quest_id(quest_id)
        if existing_assigns:
            for assign in existing_assigns:
                if assign.status == QuestAssignStatus.ONGOING.value:
                    logger.warning(
                        f"任务 {quest_id} 已被冒险者 {assign.adventurer_id} 接取"
                    )
                    return None

        # 更新冒险者状态为 WORKING
        adventurer = await self.supa_client.get_adventurer_by_id(adventurer_id)
        if not adventurer:
            logger.warning(f"未找到冒险者 {adventurer_id}")
            return None

        adventurer.status = AdventurerStatus.WORKING
        if not await self.supa_client.update_adventurer(adventurer):
            logger.error(f"更新冒险者 {adventurer_id} 状态失败")
            return None

        # 创建 quest_assign 记录
        quest_assign = QuestAssign(
            quest_id=quest_id,
            adventurer_id=adventurer_id,
            status=QuestAssignStatus.ONGOING.value,
        )
        if not await self.supa_client.insert_quest_assign(quest_assign):
            logger.error(f"创建任务分配记录失败: {quest_id} -> {adventurer_id}")
            # 回滚冒险者状态
            adventurer.status = AdventurerStatus.IDLE
            await self.supa_client.update_adventurer(adventurer)
            return None

        # 记录系统日志
        await self.supa_client.log_event(
            event="接取任务", detail=f"冒险者 {adventurer_id} 接取任务 {quest_id}"
        )

        return quest

    async def submit_quest(self, adventurer_id: str, quest_id: str) -> Quest | None:
        """
        冒险者提交任务，更新 quest_assign 状态为 SUBMITTED，设置提交时间。
        冒险者状态保持 WORKING 不变。

        Args:
            adventurer_id (str): 冒险者 ID
            quest_id (str): 任务 ID

        Returns:
            Quest | None: 返回任务对象；失败返回 None
        """
        # 获取任务
        quest = await self.supa_client.get_quest_by_id(quest_id)
        if not quest:
            logger.warning(f"提交失败：任务 {quest_id} 不存在")
            return None

        # 获取当前 ONGOING 状态的任务分配记录
        quest_assign = await self.supa_client.get_quest_assign_by_adventurer_status(
            adventurer_id, QuestAssignStatus.ONGOING.value
        )
        if not quest_assign:
            logger.warning(f"提交失败：冒险者 {adventurer_id} 没有正在执行的任务")
            return None

        # 权限检查：任务分配记录的任务ID必须匹配
        if quest_assign.quest_id != quest_id:
            logger.warning(
                f"提交失败：冒险者 {adventurer_id} 当前执行的任务是 {quest_assign.quest_id}，不是 {quest_id}"
            )
            return None

        # 更新 quest_assign 记录为 SUBMITTED 状态
        quest_assign.status = QuestAssignStatus.SUBMITTED.value
        quest_assign.submit_time = datetime.now()
        if not await self.supa_client.update_quest_assign(quest_assign):
            logger.error(f"更新任务分配记录失败: {quest_assign.id}")
            return None

        # 记录系统日志
        await self.supa_client.log_event(
            event="提交任务", detail=f"冒险者 {adventurer_id} 提交任务 {quest_id}"
        )

        return quest

    async def confirm_quest(
        self, clienter_id: str, quest_id: str
    ) -> tuple[Quest, str] | None:
        """
        委托人确认任务完成，更新 quest_assign 状态为 CONFIRMED，设置确认时间。
        同时将冒险者状态设为 IDLE。

        Args:
            clienter_id (str): 委托人 ID
            quest_id (str): 任务 ID

        Returns:
            tuple[Quest, str] | None: 返回 (任务对象, 冒险者ID)；失败返回 None
        """
        # 获取任务
        quest = await self.supa_client.get_quest_by_id(quest_id)
        if not quest:
            logger.warning(f"确认失败：任务 {quest_id} 不存在")
            return None

        # 权限检查：必须是任务的委托人
        if quest.clienter_id != clienter_id:
            logger.warning(f"确认失败：委托人 {clienter_id} 无权确认任务 {quest_id}")
            return None

        # 查找该任务的 SUBMITTED 状态的分配记录
        quest_assigns = await self.supa_client.get_quest_assigns_by_quest_id(quest_id)
        if not quest_assigns:
            logger.warning(f"确认失败：任务 {quest_id} 没有分配记录")
            return None

        submitted_assign = None
        for qa in quest_assigns:
            if qa.status == QuestAssignStatus.SUBMITTED.value:
                submitted_assign = qa
                break

        if not submitted_assign:
            logger.warning(f"确认失败：任务 {quest_id} 没有已提交的分配记录")
            return None

        # 更新 quest_assign 为 CONFIRMED 状态
        submitted_assign.status = QuestAssignStatus.CONFIRMED.value
        submitted_assign.confirm_time = datetime.now()
        if not await self.supa_client.update_quest_assign(submitted_assign):
            logger.error(f"更新任务分配记录失败: {submitted_assign.id}")
            return None

        # 更新冒险者状态为 IDLE
        adventurer = await self.supa_client.get_adventurer_by_id(
            submitted_assign.adventurer_id
        )
        if adventurer:
            adventurer.status = AdventurerStatus.IDLE
            if not await self.supa_client.update_adventurer(adventurer):
                logger.error(f"更新冒险者 {submitted_assign.adventurer_id} 状态失败")
        else:
            logger.warning(
                f"未找到冒险者 {submitted_assign.adventurer_id}，无法更新其状态"
            )

        # 记录系统日志
        await self.supa_client.log_event(
            event="确认任务", detail=f"委托人 {clienter_id} 确认任务 {quest_id} 完成"
        )

        return quest, submitted_assign.adventurer_id

    async def get_running_quest_by_adventurer_id(
        self, adventurer_id: str
    ) -> tuple[Quest, QuestAssign] | None:
        """
        获取冒险者当前正在执行的任务及其分配记录。

        Args:
            adventurer_id (str): 冒险者ID

        Returns:
            tuple[Quest, QuestAssign] | None: 返回 (任务对象, 任务分配记录)；未找到返回 None
        """
        # 获取冒险者当前 ONGOING 状态的任务分配记录
        quest_assign = await self.supa_client.get_active_quest_assign_by_adventurer(
            adventurer_id
        )
        if not quest_assign:
            return None

        # 获取对应的任务
        quest = await self.supa_client.get_quest_by_id(quest_assign.quest_id)
        if not quest:
            logger.warning(
                f"任务分配记录 {quest_assign.id} 指向的任务 {quest_assign.quest_id} 不存在"
            )
            return None

        return quest, quest_assign
