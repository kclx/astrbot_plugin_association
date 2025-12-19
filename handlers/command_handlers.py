"""命令处理器类"""

import os
from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger
from astrbot.api import message_components as Comp
from astrbot.core.utils.session_waiter import session_waiter, SessionController
from astrbot.core.platform.astrbot_message import AstrBotMessage
from astrbot.core.message.components import BaseMessageComponent, ComponentType

from ..domain.status import QuestMaterialType

from ..engine.association_client import AssociationClient
from ..utils.message_utils import MessageUtils
from ..utils.file_utils import FileUtils


class CommandHandlers:
    """命令处理器类，处理用户命令"""

    def __init__(
        self,
        ass_client: AssociationClient,
        message_utils: MessageUtils,
        file_utils: FileUtils,
    ):
        self.ass_client = ass_client
        self.message_utils = message_utils
        self.file_utils = file_utils

    async def create_adventurer(self, event: AstrMessageEvent):
        """注册为冒险者"""
        name, contact_way, contact_number = self.message_utils.get_user_identity(event)
        if self.ass_client.is_adventurer(
            contact_way, contact_number
        ) or self.ass_client.is_clienter(contact_way, contact_number):
            yield event.plain_result("您已经注册过了")
            return

        adventurer = self.ass_client.register_adventurer(
            name, contact_way, contact_number
        )
        if adventurer:
            yield event.plain_result(
                f"欢迎 {adventurer.name} 加入冒险家工会！🎉\n准备好迎接新的冒险吧！"
            )
        else:
            yield event.plain_result("注册失败，请稍后重试。")

    async def create_clienter(self, event: AstrMessageEvent):
        """注册为委托人"""
        name, contact_way, contact_number = self.message_utils.get_user_identity(event)
        # 检查是否已经注册为冒险者或委托人
        if self.ass_client.is_adventurer(
            contact_way, contact_number
        ) or self.ass_client.is_clienter(contact_way, contact_number):
            yield event.plain_result("您已经注册过了")
            return
        # 调用 Clienter 注册方法
        clienter = self.ass_client.register_clienter(name, contact_way, contact_number)
        if clienter:
            yield event.plain_result(
                f"欢迎 {name} 成为委托人！🎉\n您可以开始发布任务了。"
            )
        else:
            yield event.plain_result("注册失败，请稍后重试。")

    async def upload_attachments(self, event: AstrMessageEvent, quest_id: str):
        """文件上传具体实现"""
        try:
            yield event.plain_result('请在60s内上传附件，完成请说"退出"')

            @session_waiter(timeout=60, record_history_chains=False)
            async def file_upload_waiter(
                controller: SessionController, event: AstrMessageEvent
            ):
                _, contact_way, contact_number = self.message_utils.get_user_identity(
                    event
                )
                if self.ass_client.is_adventurer(contact_way, contact_number):
                    type = QuestMaterialType.PROOF
                elif self.ass_client.is_clienter(contact_way, contact_number):
                    type = QuestMaterialType.ILLUSTRATE
                else:
                    return
                message_text = event.message_str.strip()

                if message_text in ["退出", "完成"]:
                    await event.send(event.plain_result("已退出"))
                    controller.stop()
                    return

                msg: AstrBotMessage = event.message_obj
                messages: list[BaseMessageComponent] = msg.message

                for message in messages:
                    if message.type in [
                        ComponentType.File,
                        ComponentType.Image,
                        ComponentType.Video,
                        ComponentType.Record,
                    ]:

                        # 下载文件到quest文件夹
                        file_path = await self.file_utils.download_user_file(
                            f"quest_file/{quest_id}", message
                        )
                        if file_path:
                            # 保存到数据库
                            qm = self.ass_client.save_quest_attachment(
                                quest_id,
                                f"quest_file/{quest_id}",
                                type,
                            )
                    # 只有在有文件上传时才发送确认消息
                    message_result = event.make_result()
                    message_result.chain = [
                        Comp.Plain(f"已上传文件: {os.path.basename(file_path)}")
                    ]
                    await event.send(message_result)

                controller.keep(timeout=60, reset_timeout=True)

            try:
                await file_upload_waiter(event)
            except TimeoutError:
                yield event.plain_result("你超时了！")
            except Exception as e:
                logger.error(f"upload_file error: {e}")
                yield event.plain_result(f"发生错误，请联系管理员: {str(e)}")
            finally:
                event.stop_event()
        except Exception as e:
            logger.error(f"upload_file outer error: {e}")
