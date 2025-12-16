from enum import Enum


ADVENTURER_STATUS_CN_MAP = {
    "IDLE": "空闲",
    "WORKING": "执行任务",
    "REST": "休息",
    "QUIT": "已离开或不再参与",
}
QUEST_STATUS_CN_MAP = {
    "PUBLISHED": "已发布",
    "ASSIGNED": "已接取",
    "COMPLETED": "已完成",
    "TIMEOUT": "超时未完成",
    "CLOSED": "已关闭",
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


class QuestStatus(Enum):
    PUBLISHED = "PUBLISHED"
    ASSIGNED = "ASSIGNED"
    COMPLETED = "COMPLETED"
    TIMEOUT = "TIMEOUT"
    CLOSED = "CLOSED"

    @property
    def cn(self) -> str:
        return QUEST_STATUS_CN_MAP[self.value]

    @classmethod
    def from_cn(cls, text: str):
        for key, val in QUEST_STATUS_CN_MAP.items():
            if val == text:
                return cls(key)
        return None
