from dataclasses import dataclass, asdict, field
from typing import Optional, List
from datetime import datetime
import uuid
from ..domain.status import AdventurerStatus, QuestMaterialType, QuestAssignStatus

def _parse_datetime(value) -> Optional[datetime]:
    """统一处理 datetime 字符串/对象"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


@dataclass
class Clienter:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: Optional[datetime] = field(default_factory=datetime.now)
    name: Optional[str] = None
    contact_way: Optional[str] = None
    contact_number: Optional[str] = None

    @staticmethod
    def from_dict(data: dict) -> "Clienter":
        return Clienter(
            id=str(data["id"]),
            created_at=_parse_datetime(data.get("created_at")),
            name=data.get("name"),
            contact_way=data.get("contact_way"),
            contact_number=data.get("contact_number"),
        )

    @staticmethod
    def from_list(datas: List[dict]) -> List["Clienter"]:
        return [Clienter.from_dict(d) for d in datas]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["created_at"] = (
            self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None
        )
        return d


@dataclass
class Adventurer:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: Optional[datetime] = field(default_factory=datetime.now)
    name: Optional[str] = None
    status: AdventurerStatus = field(default_factory=lambda: AdventurerStatus.IDLE)
    contact_way: Optional[str] = None
    contact_number: Optional[str] = None

    @staticmethod
    def from_dict(data: dict) -> "Adventurer":
        return Adventurer(
            id=str(data["id"]),
            name=data.get("name"),
            status=AdventurerStatus(data.get("status", "IDLE")),
            contact_way=data.get("contact_way"),
            contact_number=data.get("contact_number"),
            created_at=_parse_datetime(data.get("created_at")),
        )

    @staticmethod
    def from_list(datas: List[dict]) -> List["Adventurer"]:
        return [Adventurer.from_dict(d) for d in datas]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        d["created_at"] = (
            self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None
        )
        return d


@dataclass
class Quest:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: Optional[datetime] = field(default_factory=datetime.now)
    clienter_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    reward: Optional[float] = None
    deadline: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @staticmethod
    def from_dict(data: dict) -> "Quest":
        return Quest(
            id=str(data["id"]),
            created_at=_parse_datetime(data.get("created_at")),
            clienter_id=data.get("clienter_id"),
            title=data.get("title"),
            description=data.get("description"),
            reward=data.get("reward"),
            deadline=_parse_datetime(data.get("deadline")),
            updated_at=_parse_datetime(data.get("updated_at")),
        )

    @staticmethod
    def from_list(datas: List[dict]) -> List["Quest"]:
        return [Quest.from_dict(d) for d in datas]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["created_at"] = (
            self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None
        )
        if self.deadline:
            d["deadline"] = self.deadline.strftime("%Y-%m-%d %H:%M:%S")
        if self.updated_at:
            d["updated_at"] = self.updated_at.strftime("%Y-%m-%d %H:%M:%S")
        return d

    @staticmethod
    def format_quests(quests: List["Quest"]) -> str:
        """将 Quest 列表格式化为可读文本"""
        if not quests:
            return "当前没有任务。"

        lines = []
        for q in quests:
            line = (
                f"任务ID: {q.id}\n"
                f"标题: {q.title}\n"
                f"描述: {q.description}\n"
                f"奖励: {q.reward}\n"
                f"截止时间: {q.deadline.strftime('%Y-%m-%d %H:%M:%S') if q.deadline else '无'}\n"
                f"创建时间: {q.created_at.strftime('%Y-%m-%d %H:%M:%S') if q.created_at else '未知'}\n"
                f"{'-'*40}"
            )
            lines.append(line)
        return "\n".join(lines)


@dataclass
class QuestAssign:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    quest_id: Optional[str] = None
    adventurer_id: Optional[str] = None
    assign_time: Optional[datetime] = field(default_factory=datetime.now)
    submit_time: Optional[datetime] = None
    confirm_time: Optional[datetime] = None
    status: QuestAssignStatus = (
        QuestAssignStatus.UNANSWERED
    )  # ONGOING, SUBMITTED, CONFIRMED, TIMEOUT, FORCED_END

    @staticmethod
    def from_dict(data: dict) -> "QuestAssign":
        return QuestAssign(
            id=str(data["id"]),
            quest_id=data.get("quest_id"),
            adventurer_id=data.get("adventurer_id"),
            assign_time=_parse_datetime(data.get("assign_time")),
            submit_time=_parse_datetime(data.get("submit_time")),
            confirm_time=_parse_datetime(data.get("confirm_time")),
            status=data.get("status", "UNANSWERED"),
        )

    @staticmethod
    def from_list(datas: List[dict]) -> List["QuestAssign"]:
        return [QuestAssign.from_dict(d) for d in datas]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["assign_time"] = (
            self.assign_time.strftime("%Y-%m-%d %H:%M:%S") if self.assign_time else None
        )
        d["submit_time"] = (
            self.submit_time.strftime("%Y-%m-%d %H:%M:%S") if self.submit_time else None
        )
        d["confirm_time"] = (
            self.confirm_time.strftime("%Y-%m-%d %H:%M:%S")
            if self.confirm_time
            else None
        )
        # 将枚举转换为字符串值
        d["status"] = self.status.value if isinstance(self.status, QuestAssignStatus) else self.status
        return d


@dataclass
class SystemLog:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event: Optional[str] = None
    detail: Optional[str] = None
    created_at: Optional[datetime] = field(default_factory=datetime.now)

    @staticmethod
    def from_dict(data: dict) -> "SystemLog":
        return SystemLog(
            id=str(data["id"]),
            event=data.get("event"),
            detail=data.get("detail"),
            created_at=_parse_datetime(data.get("created_at")),
        )

    @staticmethod
    def from_list(datas: List[dict]) -> List["SystemLog"]:
        return [SystemLog.from_dict(d) for d in datas]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["created_at"] = (
            self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None
        )
        return d


@dataclass
class QuestMaterial:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    quest_id: Optional[str] = None
    material_name: Optional[str] = None
    file_path: Optional[str] = None
    upload_time: Optional[datetime] = field(default_factory=datetime.now)
    type: str = QuestMaterialType.NONE

    @staticmethod
    def from_dict(data: dict) -> "QuestMaterial":
        return QuestMaterial(
            id=str(data["id"]),
            quest_id=data.get("quest_id"),
            material_name=data.get("material_name"),
            file_path=data.get("file_path"),
            upload_time=_parse_datetime(data.get("upload_time")),
            type=data.get("type", "NONE"),
        )

    @staticmethod
    def from_list(datas: List[dict]) -> List["QuestMaterial"]:
        return [QuestMaterial.from_dict(d) for d in datas]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["upload_time"] = (
            self.upload_time.strftime("%Y-%m-%d %H:%M:%S") if self.upload_time else None
        )
        return d
