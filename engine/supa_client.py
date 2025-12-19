import os

from supabase import create_client, Client

from ..domain.status import AdventurerStatus, QuestAssignStatus
from ..domain.vo import (
    Adventurer,
    Clienter,
    Quest,
    QuestAssign,
    SystemLog,
    QuestMaterial,
)

from astrbot.api import logger


class SupabaseClient:
    """
    一个用于操作 Supabase 的通用 CRUD 封装类。
    支持：查询 / 条件查询 / 插入 / 批量插入 / 更新 / 删除 / upsert / 批量 upsert。
    """

    def __init__(self, url: str | None = None, key: str | None = None):
        self.url = url
        self.key = key
        if not self.url or not self.key:
            raise ValueError("缺少 SUPABASE_URL 或 SUPABASE_KEY")
        self.client: Client = create_client(self.url, self.key)

    # ========================== 查询 ==========================
    def _get_records(self, table: str, filters: dict) -> list[dict] | None:
        """
        通用方法：根据条件从指定表获取多条记录

        Args:
            table (str): 数据表名称
            filters (dict, optional): 查询条件，例如 {"status": "PUBLISHED"}。
                                    如果为 None，则返回表中所有记录。

        Returns:
            list[dict]: 返回符合条件的记录列表，如果没有找到返回None
        """
        try:
            query = self.client.table(table).select("*")
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            res = query.execute()
            return getattr(res, "data")
        except Exception as e:
            logger.error(f"查询 {table} 失败: {e}")
            return None

    def _get_single_record(self, table: str, filters: dict) -> dict | None:
        """
        通用方法：根据条件从指定表获取单条记录

        Args:
            table (str): 数据表名称
            filters (dict, optional): 查询条件，例如 {"contact_way": "telegram", "contact_number": "123"}

        Returns:
            dict | None: 返回第一条记录，如果未找到返回 None
        """
        records = self._get_records(table, filters)
        return records[0] if records else None

    # 冒险者相关
    def get_adventurer_id_by_way_number(self, way: str, number: str) -> str | None:
        rec = self._get_single_record(
            "adventurer", {"contact_way": way, "contact_number": number}
        )
        return rec["id"] if rec else None

    def get_adventurer_by_way_number(self, way: str, number: str) -> Adventurer | None:
        rec = self._get_single_record(
            "adventurer", {"contact_way": way, "contact_number": number}
        )
        return Adventurer.from_dict(rec) if rec else None

    def get_adventurer_by_id(self, id: str) -> Adventurer | None:
        rec = self._get_single_record("adventurer", {"id": id})
        return Adventurer.from_dict(rec) if rec else None

    # 委托人相关
    def get_clienter_id_by_way_number(self, way: str, number: str) -> str | None:
        rec = self._get_single_record(
            "clienter", {"contact_way": way, "contact_number": number}
        )
        return rec["id"] if rec else None

    def get_clienter_by_way_number(self, way: str, number: str) -> Clienter | None:
        rec = self._get_single_record(
            "clienter", {"contact_way": way, "contact_number": number}
        )
        return Clienter.from_dict(rec) if rec else None

    def get_clienter_by_id(self, id: str) -> Clienter | None:
        rec = self._get_single_record("clienter", {"id": id})
        return Clienter.from_dict(rec) if rec else None

    # 任务相关
    def get_quest_by_id(self, quest_id: str) -> Quest | None:
        """
        根据任务ID获取任务信息

        Args:
            quest_id (str): 任务ID

        Returns:
            Quest | None: 找到返回 Quest 实例，未找到返回 None
        """
        rec = self._get_single_record("quest", {"id": quest_id})
        return Quest.from_dict(rec) if rec else None

    def get_quests_by_clienter_id(self, clienter_id: str) -> list[Quest] | None:
        """
        根据委托人ID获取该委托人发布的所有任务

        Args:
            clienter_id (str): 委托人ID

        Returns:
            list[Quest] | None: 返回任务列表，如果没有找到任务返回 None
        """
        rec = self._get_records("quest", {"clienter_id": clienter_id})
        return Quest.from_list(rec) if rec else None

    # 状态相关
    def get_adventurers_by_status(
        self, status: AdventurerStatus
    ) -> list[Adventurer] | None:
        """
        根据冒险者状态获取冒险者列表。

        Args:
            status (AdventurerStatus): 冒险者状态，例如 AdventurerStatus.IDLE

        Returns:
            list[Adventurer] | None: 返回冒险者列表，如果没有找到返回 None
        """
        # 获取所有状态符合的冒险者记录
        records = self._get_records("adventurer", {"status": status.value})
        return Adventurer.from_list(records) if records else None

    def get_available_quests(self) -> list[Quest] | None:
        """
        获取所有可接取的任务（没有 ONGOING 状态的任务分配记录）

        Returns:
            list[Quest] | None: 返回任务列表，如果没有找到返回 None
        """
        # 获取所有任务
        all_quests_records = self._get_records("quest", {})
        if not all_quests_records:
            return None

        # 获取所有 ONGOING 状态的任务分配记录
        ongoing_assigns = self.get_quest_assigns_by_status(QuestAssignStatus.ONGOING)
        ongoing_quest_ids = set()
        if ongoing_assigns:
            ongoing_quest_ids = {qa.quest_id for qa in ongoing_assigns}

        # 过滤出没有 ONGOING 分配的任务
        available_quests = [
            Quest.from_dict(q)
            for q in all_quests_records
            if q["id"] not in ongoing_quest_ids
        ]

        return available_quests if available_quests else None

    def get_active_quest_assign_by_adventurer(
        self, adventurer_id: str
    ) -> QuestAssign | None:
        """
        获取冒险者当前的活跃任务分配（ONGOING 状态）

        Args:
            adventurer_id (str): 冒险者ID

        Returns:
            QuestAssign | None: 返回任务分配实例，如果未找到返回 None
        """
        rec = self._get_single_record(
            "quest_assign", {"adventurer_id": adventurer_id, "status": "ONGOING"}
        )
        return QuestAssign.from_dict(rec) if rec else None

    def get_quest_assigns_by_status(
        self, status: QuestAssignStatus
    ) -> list[QuestAssign] | None:
        """
        获取特定状态的所有任务分配

        Args:
            status (QuestAssignStatus): 任务分配状态

        Returns:
            list[QuestAssign] | None: 返回任务分配列表，如果没有找到返回 None
        """
        records = self._get_records("quest_assign", {"status": status.value})
        return QuestAssign.from_list(records) if records else None

    # ========================== 插入 ==========================
    # 冒险者相关
    def insert_adventurer(self, adventurer: Adventurer) -> bool:
        """
        将 Adventurer 实例插入到数据库

        Args:
            adventurer (Adventurer): 待插入的冒险者对象

        Returns:
            bool: 插入成功返回 True，否则返回 False
        """
        try:
            res = self.client.table("adventurer").insert(adventurer.to_dict()).execute()
            if hasattr(res, "data") and res.data:
                return True
            else:
                logger.error(f"插入冒险者失败，返回结果: {res}")
                return False
        except Exception as e:
            logger.error(f"插入冒险者异常: {e}")
            return False

    # 委托人相关
    def insert_clienter(self, clienter: Clienter) -> bool:
        """
        将 Clienter 实例插入到数据库

        Args:
            clienter (Clienter): 待插入的委托人对象

        Returns:
            bool: 插入成功返回 True，否则返回 False
        """
        try:
            res = self.client.table("clienter").insert(clienter.to_dict()).execute()
            if hasattr(res, "data") and res.data:
                return True
            else:
                logger.error(f"插入委托人失败，返回结果: {res}")
                return False
        except Exception as e:
            logger.error(f"插入委托人异常: {e}")
            return False

    # 委托相关
    def insert_quest(self, quest: Quest) -> bool:
        """
        将 Quest 对象插入数据库。

        Args:
            quest (Quest): 要插入的任务对象

        Returns:
            bool: 插入成功返回 True，失败返回 False
        """
        try:
            d = quest.to_dict()
            res = self.client.table("quest").insert(d).execute()
            # Supabase 返回的数据可能在 data 属性中，也可以检查长度
            if hasattr(res, "data") and res.data:
                return True
            logger.error(f"插入任务失败，返回结果: {res}")
            return False
        except Exception as e:
            logger.error(f"插入任务异常: {e}")
            return False

    # ========================== 更新 ==========================
    # 委托相关
    def update_quest(self, quest: Quest) -> bool:
        """
        更新任务信息到数据库

        Args:
            quest (Quest): 需要更新的任务对象

        Returns:
            bool: 更新成功返回 True，失败返回 False
        """
        if not quest or not quest.id:
            logger.error("无效任务对象，无法更新")
            return False
        try:
            res = (
                self.client.table("quest")
                .update(quest.to_dict())
                .eq("id", quest.id)
                .execute()
            )
            return bool(getattr(res, "data", None))
        except Exception as e:
            logger.error(f"更新任务 {quest.id} 失败: {e}")
            return False

    # 冒险者相关
    def update_adventurer(self, adventurer: Adventurer) -> bool:
        """
        更新冒险者信息到数据库

        Args:
            adventurer (Adventurer): 需要更新的冒险者对象

        Returns:
            bool: 更新成功返回 True，失败返回 False
        """
        if not adventurer or not adventurer.id:
            logger.error("无效冒险者对象，无法更新")
            return False
        try:
            res = (
                self.client.table("adventurer")
                .update(adventurer.to_dict())
                .eq("id", adventurer.id)
                .execute()
            )
            return bool(getattr(res, "data", None))
        except Exception as e:
            logger.error(f"更新冒险者 {adventurer.id} 失败: {e}")
            return False

    # 委托人相关
    def update_clienter(self, clienter: Clienter) -> bool:
        """
        更新委托人信息到数据库

        Args:
            clienter (Clienter): 需要更新的委托人对象

        Returns:
            bool: 更新成功返回 True，失败返回 False
        """
        if not clienter or not clienter.id:
            logger.error("无效委托人对象，无法更新")
            return False
        try:
            res = (
                self.client.table("clienter")
                .update(clienter.to_dict())
                .eq("id", clienter.id)
                .execute()
            )
            return bool(getattr(res, "data", None))
        except Exception as e:
            logger.error(f"更新委托人 {clienter.id} 失败: {e}")
            return False

    # ========================== quest_assign operations ==========================
    def insert_quest_assign(self, quest_assign: QuestAssign) -> bool:
        """插入任务分配记录"""
        try:
            res = (
                self.client.table("quest_assign")
                .insert(quest_assign.to_dict())
                .execute()
            )
            return bool(getattr(res, "data", None))
        except Exception as e:
            logger.error(f"插入任务分配记录失败: {e}")
            return False

    def update_quest_assign(self, quest_assign: QuestAssign) -> bool:
        """更新任务分配记录"""
        if not quest_assign or not quest_assign.id:
            logger.error("无效任务分配对象")
            return False
        try:
            res = (
                self.client.table("quest_assign")
                .update(quest_assign.to_dict())
                .eq("id", quest_assign.id)
                .execute()
            )
            return bool(getattr(res, "data", None))
        except Exception as e:
            logger.error(f"更新任务分配记录失败: {e}")
            return False

    def get_quest_assign_by_adventurer_status(
        self, adventurer_id: str, status: str = "ONGOING"
    ) -> QuestAssign | None:
        """获取冒险者的特定状态任务分配记录"""
        rec = self._get_single_record(
            "quest_assign", {"adventurer_id": adventurer_id, "status": status}
        )
        return QuestAssign.from_dict(rec) if rec else None

    def get_quest_assigns_by_quest_id(self, quest_id: str) -> list[QuestAssign] | None:
        """获取某任务的所有分配历史"""
        records = self._get_records("quest_assign", {"quest_id": quest_id})
        return QuestAssign.from_list(records) if records else None

    # ========================== quest_material operations ==========================
    def insert_quest_material(self, quest_material: QuestMaterial) -> bool:
        """
        插入任务材料记录

        Args:
            quest_material (QuestMaterial): 待插入的任务材料对象

        Returns:
            bool: 插入成功返回 True，失败返回 False
        """
        try:
            res = (
                self.client.table("quest_material")
                .insert(quest_material.to_dict())
                .execute()
            )
            return bool(getattr(res, "data", None))
        except Exception as e:
            logger.error(f"插入任务材料失败: {e}")
            return False

    def get_quest_materials_by_assign_id(
        self, assign_id: str
    ) -> list[QuestMaterial] | None:
        """
        获取任务分配的所有材料

        Args:
            assign_id (str): 任务分配ID

        Returns:
            list[QuestMaterial] | None: 返回材料列表，如果没有找到返回 None
        """
        records = self._get_records("quest_material", {"assign_id": assign_id})
        return QuestMaterial.from_list(records) if records else None

    # ========================== system_log operations ==========================
    def insert_system_log(self, log: SystemLog) -> bool:
        """插入系统日志"""
        try:
            res = self.client.table("system_log").insert(log.to_dict()).execute()
            return bool(getattr(res, "data", None))
        except Exception as e:
            logger.error(f"插入系统日志失败: {e}")
            return False

    def log_event(self, event: str, detail: str | None = None) -> bool:
        """便捷方法：记录系统事件"""
        log = SystemLog(event=event, detail=detail)
        return self.insert_system_log(log)
