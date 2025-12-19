from enum import Enum


ADVENTURER_STATUS_CN_MAP = {
    "IDLE": "空闲",
    "WORKING": "执行任务",
    "REST": "休息",
    "QUIT": "已离开或不再参与",
}

QUEST_ASSIGN_STATUS_CN_MAP = {
    "UNANSWERED": "未接取",
    "ONGOING": "执行中",
    "SUBMITTED": "已提交",
    "CONFIRMED": "已确认",
    "TIMEOUT": "超时",
    "FORCED_END": "强制终止",
}

QUEST_MATERIAL_TYPE_CN_MAP = {
    "ILLUSTRATE": "需求",
    "PROOF": "证明",
    "NONE": "未知",
}


class AdventurerStatus(Enum):
    IDLE = "IDLE"  # 可以接任务
    WORKING = "WORKING"  # 正在执行任务
    REST = "REST"  # 暂停中
    QUIT = "QUIT"  # 已离开系统/不再参与

    @property
    def cn(self) -> str:
        """获取状态的中文描述"""
        return ADVENTURER_STATUS_CN_MAP[self.value]

    @classmethod
    def from_cn(cls, text: str):
        """根据中文描述返回对应的枚举实例，如果找不到返回 None"""
        for key, val in ADVENTURER_STATUS_CN_MAP.items():
            if val == text:
                return cls(key)
        return None


class QuestAssignStatus(Enum):
    UNANSWERED = "UNANSWERED"
    ONGOING = "ONGOING"
    SUBMITTED = "SUBMITTED"
    CONFIRMED = "CONFIRMED"
    TIMEOUT = "TIMEOUT"
    FORCED_END = "FORCED_END"

    @property
    def cn(self) -> str:
        return QUEST_ASSIGN_STATUS_CN_MAP[self.value]

    @classmethod
    def from_cn(cls, text: str):
        for key, val in QUEST_ASSIGN_STATUS_CN_MAP.items():
            if val == text:
                return cls(key)
        return None


class QuestMaterialType(Enum):
    ILLUSTRATE = "ILLUSTRATE"
    PROOF = "PROOF"
    NONE = "NONE"

    @property
    def cn(self) -> str:
        return QUEST_MATERIAL_TYPE_CN_MAP[self.value]

    @classmethod
    def from_cn(cls, text: str):
        for key, val in QUEST_MATERIAL_TYPE_CN_MAP.items():
            if val == text:
                return cls(key)
        return None
