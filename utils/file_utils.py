"""文件处理工具类"""

import os
import shutil
from pathlib import Path
from astrbot.api import logger
from astrbot.core.message.components import File, Image, Video, Record


class FileUtils:
    """文件处理工具类"""

    def __init__(self, save_dir: str | Path):
        self.save_dir = save_dir

    async def download_user_file(
        self, path: str, file_component: File | Image | Video | Record
    ) -> str | None:
        """下载文件/图片/视频/音频并保存到用户文件夹下。

        支持所有文件相关的消息组件类型，会根据组件类型自动调用合适的转换方法。

        Args:
            path: 路径
            file_component: 文件消息组件对象（File, Image, Video, Record）

        Returns:
            str | None: 下载成功返回文件路径，失败返回 None
        """
        try:
            # 构建用户文件夹路径
            user_dir = os.path.join(self.save_dir, path)
            os.makedirs(user_dir, exist_ok=True)

            # 根据组件类型获取源文件路径
            if isinstance(file_component, File):
                # File 类型使用 get_file() 方法
                source_path = await file_component.get_file()
                file_name = file_component.name or os.path.basename(source_path)
            elif isinstance(file_component, (Image, Video, Record)):
                # Image, Video, Record 类型使用 convert_to_file_path() 方法
                source_path = await file_component.convert_to_file_path()
                # 从源路径提取文件名，或使用默认命名
                file_name = os.path.basename(source_path)
            else:
                logger.error(f"不支持的文件组件类型: {type(file_component)}")
                return None

            if not source_path or not os.path.exists(source_path):
                logger.error(f"源文件不存在: {source_path}")
                return None

            # 构建目标文件路径
            dest_path = os.path.join(user_dir, file_name)

            # 如果源路径和目标路径不同，则复制文件
            if os.path.abspath(source_path) != os.path.abspath(dest_path):
                shutil.copy2(source_path, dest_path)

            logger.info(f"文件已保存: {file_name} -> {dest_path}")
            return dest_path
        except Exception as e:
            logger.error(f"文件下载失败: {e}")
            return None
