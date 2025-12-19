"""Session 管理器，用于跟踪用户的默认对话 conversation ID"""

import json
import os
from pathlib import Path
from typing import Dict
from astrbot.api import logger


class SessionManager:
    """管理每个用户 (unified_msg_origin) 的默认对话 conversation ID"""

    def __init__(self, save_dir: str | Path):
        """初始化 SessionManager

        Args:
            save_dir: 数据存储目录
        """
        self.save_dir = save_dir
        self.session_file = os.path.join(save_dir, "user_conversations.json")
        # {unified_msg_origin: conversation_id}
        self.user_conversations: Dict[str, str] = {}
        self._load_sessions()

    def _load_sessions(self):
        """从文件加载已保存的 conversation 映射"""
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, "r", encoding="utf-8") as f:
                    self.user_conversations = json.load(f)
                logger.info(
                    f"加载了 {len(self.user_conversations)} 个用户的默认 conversation 映射"
                )
            except Exception as e:
                logger.error(f"加载 conversation 映射文件失败: {e}")
                self.user_conversations = {}
        else:
            logger.info("未找到 conversation 映射文件，将创建新的映射")

    def _save_sessions(self):
        """保存 conversation 映射到文件"""
        try:
            os.makedirs(self.save_dir, exist_ok=True)
            with open(self.session_file, "w", encoding="utf-8") as f:
                json.dump(self.user_conversations, f, ensure_ascii=False, indent=2)
            logger.debug(
                f"已保存 {len(self.user_conversations)} 个用户的 conversation 映射"
            )
        except Exception as e:
            logger.error(f"保存 conversation 映射文件失败: {e}")

    def set_user_conversation(self, unified_msg_origin: str, conversation_id: str):
        """设置用户的默认 conversation ID

        Args:
            unified_msg_origin: 统一消息来源标识符（用户的唯一标识）
            conversation_id: 对话 ID (cid)
        """
        self.user_conversations[unified_msg_origin] = conversation_id
        self._save_sessions()
        logger.debug(
            f"设置用户 {unified_msg_origin} 的默认 conversation 为 {conversation_id[:8]}..."
        )

    def get_user_conversation(self, unified_msg_origin: str) -> str | None:
        """获取用户的默认 conversation ID

        Args:
            unified_msg_origin: 统一消息来源标识符（用户的唯一标识）

        Returns:
            对话 ID (cid)，如果不存在则返回 None
        """
        return self.user_conversations.get(unified_msg_origin)

    def remove_user_conversation(self, unified_msg_origin: str):
        """移除用户的默认 conversation ID

        Args:
            unified_msg_origin: 统一消息来源标识符（用户的唯一标识）
        """
        if unified_msg_origin in self.user_conversations:
            del self.user_conversations[unified_msg_origin]
            self._save_sessions()
            logger.debug(f"移除用户 {unified_msg_origin} 的默认 conversation")

    def get_all_conversations(self) -> Dict[str, str]:
        """获取所有用户的 conversation 映射"""
        return self.user_conversations.copy()
