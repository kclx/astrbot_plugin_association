"""文件处理工具类"""

import os
from astrbot.api import logger
from astrbot.core.message.components import File
from astrbot.core.utils.io import download_file


class FileUtils:
    """文件处理工具类"""

    def __init__(self, save_dir: str):
        self.save_dir = save_dir

    async def download_user_file(self, user_id: str, file_msg: File) -> str | None:
        """下载文件并保存到用户文件夹下。

        Args:
            user_id(string): 用户ID
            file_msg(File): 文件消息对象

        Returns:
            str | None: 下载成功返回文件路径，失败返回 None
        """
        try:
            # 构建用户文件夹路径
            user_dir = os.path.join(self.save_dir, user_id)
            os.makedirs(user_dir, exist_ok=True)

            # 构建完整文件路径
            file_path = os.path.join(user_dir, file_msg.name)

            # 下载文件
            await download_file(file_msg.url, file_path)
            logger.info(f"文件已保存: {file_msg.name} -> {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"文件下载失败: {file_msg.name}, 错误: {e}")
            return None
